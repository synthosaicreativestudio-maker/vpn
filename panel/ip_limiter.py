"""Контроль лимита одновременных IP-адресов.

Фоновая задача парсит access.log Xray и отключает
пользователей, превысивших лимит IP.
"""

import asyncio
import logging
import re
import time
from collections import defaultdict
from pathlib import Path

from panel.config import (
    IP_CHECK_INTERVAL,
    XRAY_ACCESS_LOG,
    ENABLE_IP_LIMITS,
    INBOUND_TAG_VISION,
    INBOUND_TAG_XHTTP,
    INBOUND_TAG_GRPC,
    INBOUND_TAG_WS,
)
from panel.db import PanelDB

logger = logging.getLogger("panel.ip_limiter")

# Паттерн строки access.log Xray:
# 2026/03/21 11:00:00 1.2.3.4:12345 accepted tcp:example.com:443 [VLESS-Reality-Vision >> DIRECT] email: user@example.com
_LOG_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+"
    r"(?P<ip>[\d.]+):\d+\s+"
    r"accepted\s+.*"
    r"email:\s*(?P<email>\S+)"
)


class IPLimiter:
    """Фоновый монитор IP-адресов пользователей."""

    def __init__(self, db: PanelDB, xray_client=None):
        self.db = db
        self.xray_client = xray_client
        self._running = False
        self._last_position: int = 0
        self.blocked_users: dict[str, float] = {}

    async def start(self):
        """Запуск фонового мониторинга."""
        self._running = True
        logger.info(
            "IP limiter started (interval=%ds, log=%s)",
            IP_CHECK_INTERVAL,
            XRAY_ACCESS_LOG,
        )
        while self._running:
            try:
                self._check_log()
            except Exception:
                logger.exception("Error in IP limiter cycle")
            await asyncio.sleep(IP_CHECK_INTERVAL)

    def stop(self):
        """Остановка мониторинга."""
        self._running = False
        logger.info("IP limiter stopped")

    def _check_log(self):
        """Однократная проверка access.log."""
        log_path = Path(XRAY_ACCESS_LOG)
        if not log_path.exists():
            return

        file_size = log_path.stat().st_size
        if file_size < self._last_position:
            # Лог был ротирован
            self._last_position = 0

        with open(log_path, encoding="utf-8", errors="ignore") as f:
            f.seek(self._last_position)
            new_lines = f.readlines()
            self._last_position = f.tell()

        if not new_lines:
            return

        # Собираем IP → email
        ip_map: dict[str, set[str]] = defaultdict(set)
        for line in new_lines:
            match = _LOG_PATTERN.search(line)
            if match:
                email = match.group("email")
                ip = match.group("ip")
                ip_map[email].add(ip)
                self.db.log_ip(email, ip)

        # Проверяем лимиты
        all_tags = [INBOUND_TAG_VISION, INBOUND_TAG_XHTTP, INBOUND_TAG_GRPC, INBOUND_TAG_WS]
        for email, ips in ip_map.items():
            user = self.db.get_user(email)
            if not user:
                continue

            active_ips = self.db.get_active_ips(email)
            limit = user.get("ip_limit", 2)

            if len(active_ips) > limit:
                logger.warning(
                    "User %s exceeded IP limit: %d/%d (IPs: %s)",
                    email,
                    len(active_ips),
                    limit,
                    active_ips,
                )
                if ENABLE_IP_LIMITS and self.xray_client and email not in self.blocked_users:
                    logger.info("Temporarily blocking %s for 10 minutes", email)
                    self.blocked_users[email] = time.time() + 600
                    self.xray_client.remove_user_all_inbounds(email, all_tags)

        # Разблокировка пользователей
        if ENABLE_IP_LIMITS and self.xray_client:
            current_time = time.time()
            to_unblock = [e for e, t in self.blocked_users.items() if current_time > t]
            for e in to_unblock:
                del self.blocked_users[e]
                user = self.db.get_user(e)
                if user and user.get("is_active"):
                    # Проверяем, не исчерпан ли трафик
                    if user.get("total_gb") and user.get("used_gb") >= user.get("total_gb"):
                        continue
                    logger.info("IP block expired for %s, restoring to Xray", e)
                    self.xray_client.add_user_all_inbounds(e, user["uuid"], all_tags)

    def get_user_ips(self, email: str) -> list[str]:
        """Получить активные IP-адреса пользователя."""
        return self.db.get_active_ips(email)
