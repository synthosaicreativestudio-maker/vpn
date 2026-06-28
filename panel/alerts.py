"""Мониторинг и TG-алерты для VPN-инфраструктуры.

Фоновая задача проверяет:
- Количество TCP-соединений Xray (US + Relay)
- RAM Xray на Relay
- TIME-WAIT соединений

Отправляет уведомления в Telegram при превышении порогов.
Модуль подключается/отключается без влияния на ядро.
"""

import asyncio
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger("panel.alerts")

# ── Конфигурация (из переменных окружения) ────────────────────
ALERT_BOT_TOKEN = os.getenv("ALERT_BOT_TOKEN", "")
ALERT_CHAT_ID = os.getenv("ALERT_CHAT_ID", "")
ALERT_INTERVAL = int(os.getenv("ALERT_INTERVAL", "300"))  # 5 минут

# Пороги алертов
ALERT_CONN_THRESHOLD = int(os.getenv("ALERT_CONN_THRESHOLD", "500"))
ALERT_RAM_MB_THRESHOLD = int(os.getenv("ALERT_RAM_MB_THRESHOLD", "500"))
ALERT_TIMEWAIT_THRESHOLD = int(os.getenv("ALERT_TIMEWAIT_THRESHOLD", "800"))

# Кулдаун между однотипными алертами (не спамить)
_COOLDOWN = 1800  # 30 минут
_last_alerts: dict[str, float] = {}

# Relay IP (берём из panel.config)
_RELAY_IP: Optional[str] = None


def _get_relay_ip() -> str:
    """Ленивая загрузка RELAY_IP из config."""
    global _RELAY_IP
    if _RELAY_IP is None:
        try:
            from panel.config import RELAY_IP
            _RELAY_IP = RELAY_IP
        except ImportError:
            _RELAY_IP = ""
    return _RELAY_IP


async def _send_tg(text: str) -> None:
    """Отправка сообщения в Telegram."""
    if not ALERT_BOT_TOKEN or not ALERT_CHAT_ID:
        logger.debug("TG alerts not configured (no token/chat_id)")
        return

    url = f"https://api.telegram.org/bot{ALERT_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ALERT_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning("TG alert failed: %s", resp.text[:200])
    except Exception as exc:
        logger.warning("TG alert send error: %s", exc)


def _should_alert(key: str) -> bool:
    """Проверка кулдауна алерта."""
    now = time.time()
    if key in _last_alerts and (now - _last_alerts[key]) < _COOLDOWN:
        return False
    _last_alerts[key] = now
    return True


async def _get_conn_count() -> dict:
    """Получить количество TCP-соединений Xray (US local)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ss", "-tnp",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
        if not stdout:
            return {"us": 0, "time_wait": 0}

        output = stdout.decode("utf-8", errors="ignore")
        xray_count = sum(1 for line in output.split("\n") if "xray" in line and "ESTAB" in line)
        tw_count = output.count("TIME-WAIT")
        return {"us": xray_count, "time_wait": tw_count}
    except Exception:
        return {"us": 0, "time_wait": 0}


async def _get_relay_stats() -> dict:
    """Получить соединения и RAM Xray с Relay через SSH."""
    relay_ip = _get_relay_ip()
    if not relay_ip:
        return {"relay_conn": 0, "relay_ram_mb": 0}

    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            f"ubuntu@{relay_ip}",
            "sudo ss -tnp | grep -c xray 2>/dev/null; "
            "sudo ps -o rss= -p $(pgrep xray) 2>/dev/null",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            return {"relay_conn": 0, "relay_ram_mb": 0}

        if not stdout:
            return {"relay_conn": 0, "relay_ram_mb": 0}

        lines = stdout.decode("utf-8", errors="ignore").strip().split("\n")
        relay_conn = int(lines[0]) if lines and lines[0].strip().isdigit() else 0
        relay_ram_kb = int(lines[1].strip()) if len(lines) > 1 and lines[1].strip().isdigit() else 0

        return {
            "relay_conn": relay_conn,
            "relay_ram_mb": relay_ram_kb // 1024,
        }
    except Exception as exc:
        logger.debug("Relay stats error: %s", exc)
        return {"relay_conn": 0, "relay_ram_mb": 0}


async def _check_and_alert() -> None:
    """Одна итерация проверки и отправки алертов."""
    us = await _get_conn_count()
    relay = await _get_relay_stats()

    total_conn = us["us"] + relay["relay_conn"]
    relay_ram = relay["relay_ram_mb"]
    time_wait = us["time_wait"]

    logger.debug(
        "Alert check: conn=%d (US=%d, Relay=%d), RAM=%dMB, TW=%d",
        total_conn, us["us"], relay["relay_conn"], relay_ram, time_wait,
    )

    # Алерт: слишком много соединений
    if total_conn > ALERT_CONN_THRESHOLD and _should_alert("conn"):
        await _send_tg(
            f"⚠️ <b>VPN Alert: высокая нагрузка</b>\n\n"
            f"TCP-соединений Xray: <b>{total_conn}</b>\n"
            f"├ US: {us['us']}\n"
            f"├ Relay: {relay['relay_conn']}\n"
            f"└ TIME-WAIT: {time_wait}\n\n"
            f"Порог: {ALERT_CONN_THRESHOLD}"
        )

    # Алерт: RAM Xray на Relay
    if relay_ram > ALERT_RAM_MB_THRESHOLD and _should_alert("ram"):
        await _send_tg(
            f"🔴 <b>VPN Alert: утечка памяти Relay</b>\n\n"
            f"Xray RAM: <b>{relay_ram} МБ</b>\n"
            f"Порог: {ALERT_RAM_MB_THRESHOLD} МБ\n\n"
            f"Рекомендация: перезапустить Xray на Relay"
        )

    # Алерт: TIME-WAIT
    if time_wait > ALERT_TIMEWAIT_THRESHOLD and _should_alert("timewait"):
        await _send_tg(
            f"⏳ <b>VPN Alert: TIME-WAIT</b>\n\n"
            f"TIME-WAIT соединений: <b>{time_wait}</b>\n"
            f"Порог: {ALERT_TIMEWAIT_THRESHOLD}\n\n"
            f"Возможна утечка сокетов"
        )


async def alert_monitor_task() -> None:
    """Основной цикл мониторинга. Запускается из lifespan."""
    if not ALERT_BOT_TOKEN or not ALERT_CHAT_ID:
        logger.info("TG alerts disabled (ALERT_BOT_TOKEN/ALERT_CHAT_ID not set)")
        return

    logger.info(
        "🔔 Alert monitor started (interval=%ds, conn>%d, ram>%dMB)",
        ALERT_INTERVAL, ALERT_CONN_THRESHOLD, ALERT_RAM_MB_THRESHOLD,
    )

    # Стартовое уведомление
    await _send_tg("✅ <b>VPN Monitor запущен</b>\nАлерты активны.")

    await asyncio.sleep(30)  # Даём время на старт всех сервисов

    while True:
        try:
            await _check_and_alert()
        except Exception:
            logger.exception("Error in alert monitor")
        await asyncio.sleep(ALERT_INTERVAL)
