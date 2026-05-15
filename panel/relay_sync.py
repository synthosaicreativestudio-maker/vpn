"""Синхронизация пользователей с Relay RU-сервером.

При создании / удалении пользователя в панели — добавляем/удаляем
его UUID в VLESS-Reality-Relay inbound на RU relay (46.21.244.161).
Это позволяет relay различать пользователей в access.log и трекать IP.

Модуль отключается если RELAY_ENABLED=False.
"""

import logging

from panel.config import RELAY_ENABLED

logger = logging.getLogger("panel.relay_sync")

RELAY_GRPC_HOST = "46.21.244.161:10085"
RELAY_INBOUND_TAG = "VLESS-Reality-Relay"

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
    """Добавить пользователя в relay inbound."""
    if not RELAY_ENABLED:
        return True
    client = get_relay_client()
    if not client:
        return False
    # Vision flow для relay
    ok = client.add_user(RELAY_INBOUND_TAG, email, uuid, flow="xtls-rprx-vision")
    if ok:
        logger.info("User %s added to relay", email)
    return ok


def remove_user_from_relay(email: str) -> bool:
    """Удалить пользователя из relay inbound."""
    if not RELAY_ENABLED:
        return True
    client = get_relay_client()
    if not client:
        return False
    ok = client.remove_user(RELAY_INBOUND_TAG, email)
    if ok:
        logger.info("User %s removed from relay", email)
    return ok


def sync_all_users_to_relay(users: list[dict]) -> int:
    """Синхронизировать всех активных пользователей на relay при старте."""
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
        ok = client.add_user(RELAY_INBOUND_TAG, email, uuid, flow="xtls-rprx-vision")
        if ok:
            count += 1
    logger.info("Relay sync complete: %d users added", count)
    return count
