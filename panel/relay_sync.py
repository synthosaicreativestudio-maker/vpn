"""Синхронизация пользователей с Relay RU-сервером.

При создании / удалении пользователя в панели — добавляем/удаляем
его UUID в VLESS-Reality-Relay inbound на RU relay (46.21.244.161).
Это позволяет relay различать пользователей в access.log и трекать IP.

Модуль отключается если RELAY_ENABLED=False.
"""

import logging

from panel.config import RELAY_ENABLED

logger = logging.getLogger("panel.relay_sync")

RELAY_GRPC_HOST = "51.250.94.182:10085"
RELAY_INBOUND_TAG = "VLESS-Reality-Relay"
RELAY_INBOUND_TAG_443 = "VLESS-Reality-Relay-443"

_relay_client = None


def get_relay_client():
    """Ленивое создание relay gRPC клиента."""
    global _relay_client
    if _relay_client is None and RELAY_ENABLED:
        try:
            from panel.xray_client import XrayClient
            _relay_client = XrayClient(RELAY_GRPC_HOST)
            logger.info("Relay gRPC client connected to %s", RELAY_GRPC_HOST)
        except Exception as exc:
            logger.error("Failed to connect relay gRPC: %s", exc)
    return _relay_client


def add_user_to_relay(email: str, uuid: str) -> bool:
    """Добавить пользователя в оба relay inbound (8081 + 443)."""
    if not RELAY_ENABLED:
        return True
    client = get_relay_client()
    if not client:
        return False
    # Добавляем в оба inbound
    ok1 = client.add_user(RELAY_INBOUND_TAG, email, uuid, flow="xtls-rprx-vision")
    ok2 = client.add_user(RELAY_INBOUND_TAG_443, email, uuid, flow="xtls-rprx-vision")
    if ok1 or ok2:
        logger.info("User %s added to relay (8081=%s, 443=%s)", email, ok1, ok2)
    return ok1 or ok2


def remove_user_from_relay(email: str) -> bool:
    """Удалить пользователя из обоих relay inbound."""
    if not RELAY_ENABLED:
        return True
    client = get_relay_client()
    if not client:
        return False
    ok1 = client.remove_user(RELAY_INBOUND_TAG, email)
    ok2 = client.remove_user(RELAY_INBOUND_TAG_443, email)
    if ok1 or ok2:
        logger.info("User %s removed from relay", email)
    return ok1 or ok2


def sync_all_users_to_relay(users: list[dict]) -> int:
    """Синхронизировать всех активных пользователей на оба relay inbound."""
    if not RELAY_ENABLED:
        return 0
    client = get_relay_client()
    if not client:
        logger.warning("Relay sync skipped: client not available")
        return 0
    count = 0
    for user in users:
        if not user.get("is_active"):
            continue
        email = user["email"]
        uuid = user["uuid"]
        ok1 = client.add_user(RELAY_INBOUND_TAG, email, uuid, flow="xtls-rprx-vision")
        ok2 = client.add_user(RELAY_INBOUND_TAG_443, email, uuid, flow="xtls-rprx-vision")
        if ok1 or ok2:
            count += 1
    logger.info("Relay sync complete: %d users added", count)
    return count
