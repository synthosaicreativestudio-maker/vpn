"""Контроль лимита одновременных IP-адресов.

Фоновая задача парсит access.log Xray и отключает
пользователей, превысивших лимит IP.
"""

import asyncio
import logging
import re
from collections import defaultdict
from pathlib import Path

from panel.config import IP_CHECK_INTERVAL, XRAY_ACCESS_LOG
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
                # TODO: Опционально отключить пользователя через xray_client

    def get_user_ips(self, email: str) -> list[str]:
        """Получить активные IP-адреса пользователя."""
        return self.db.get_active_ips(email)
