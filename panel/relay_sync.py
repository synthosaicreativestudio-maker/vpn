"""Синхронизация пользователей с Relay RU-сервером.

При создании / удалении пользователя в панели — добавляем/удаляем
его UUID в VLESS-Reality-Relay inbound на RU relay (46.21.244.161).
Это позволяет relay различать пользователей в access.log и трекать IP.

Модуль отключается если RELAY_ENABLED=False.
"""

import json
import logging
import subprocess

from panel.config import RELAY_ENABLED, RELAY_GRPC_ENABLED, RELAY_GRPC_HOST, RELAY_IP

logger = logging.getLogger("panel.relay_sync")

RELAY_INBOUND_TAGS = ["relay-vision", "relay-grpc", "relay-xhttp", "relay-test-8081"]

_relay_client = None


def get_relay_client():
    """Ленивое создание relay gRPC клиента."""
    global _relay_client
    if _relay_client is None and RELAY_ENABLED and RELAY_GRPC_ENABLED:
        try:
            from panel.xray_client import XrayClient
            _relay_client = XrayClient(RELAY_GRPC_HOST)
            logger.info("Relay gRPC client connected to %s", RELAY_GRPC_HOST)
        except Exception as exc:
            logger.error("Failed to connect relay gRPC: %s", exc)
    return _relay_client


def add_user_to_relay(email: str, uuid: str) -> bool:
    """Добавить пользователя во все relay inbounds."""
    if not RELAY_ENABLED:
        return True
    client = get_relay_client()
    if not client:
        return False
    
    success = False
    for tag in RELAY_INBOUND_TAGS:
        flow = "xtls-rprx-vision" if ("vision" in tag.lower() or "8081" in tag) else ""
        ok = client.add_user(tag, email, uuid, flow=flow)
        if ok:
            success = True
    
    if success:
        logger.info("User %s added to relay inbounds", email)
    return success


def remove_user_from_relay(email: str) -> bool:
    """Удалить пользователя из всех relay inbounds."""
    if not RELAY_ENABLED:
        return True
    client = get_relay_client()
    if not client:
        return False
    
    success = False
    for tag in RELAY_INBOUND_TAGS:
        ok = client.remove_user(tag, email)
        if ok:
            success = True
            
    if success:
        logger.info("User %s removed from relay inbounds", email)
    return success


def sync_all_users_to_relay(users: list[dict]) -> int:
    """Синхронизировать всех активных пользователей во все relay inbounds."""
    if not RELAY_ENABLED:
        return 0
    client = get_relay_client()
    if not client:
        logger.warning("Relay sync skipped: client not available")
        return 0
    
    # Собираем существующих пользователей на релее, чтобы не слать дублирующие запросы
    existing_by_tag: dict[str, set[str]] = {}
    for tag in RELAY_INBOUND_TAGS:
        try:
            inbound_users = client.get_inbound_users(tag)
            existing_by_tag[tag] = {u["email"] for u in inbound_users} if inbound_users else set()
        except Exception as e:
            logger.warning("Failed to get users for relay tag %s: %s", tag, e)
            existing_by_tag[tag] = set()

    count = 0
    for user in users:
        if not user.get("is_active"):
            continue
        email = user["email"]
        uuid = user["uuid"]
        
        user_synced = False
        for tag in RELAY_INBOUND_TAGS:
            if email not in existing_by_tag.get(tag, set()):
                flow = "xtls-rprx-vision" if ("vision" in tag.lower() or "8081" in tag) else ""
                ok = client.add_user(tag, email, uuid, flow=flow)
                if ok:
                    user_synced = True
                
        if user_synced:
            count += 1
            
    if count > 0:
        logger.info("Relay sync complete: %d users added", count)
    return count


def get_relay_traffic_stats() -> dict[str, float]:
    """Получить статистику трафика по пользователям с Relay сервера через SSH."""
    if not RELAY_ENABLED:
        return {}
    try:
        cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-i", "/root/.ssh/id_ed25519",
            f"ubuntu@{RELAY_IP}",
            "xray api statsquery --server=127.0.0.1:10085 -reset"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            logger.error("Failed to query relay stats: %s", res.stderr)
            return {}
            
        output = res.stdout.strip()
        if not output or output == "{}":
            return {}
            
        data = json.loads(output)
        stats = data.get("stat", [])
        
        traffic_by_email = {}
        for stat in stats:
            name = stat.get("name", "")
            value = stat.get("value", 0)
            parts = name.split(">>>")
            # user>>>email>>>traffic>>>downlink/uplink
            if len(parts) == 4 and parts[0] == "user" and parts[2] == "traffic":
                email = parts[1]
                value_gb = value / (1024**3)
                traffic_by_email[email] = traffic_by_email.get(email, 0.0) + value_gb
                
        return traffic_by_email
    except Exception as e:
        logger.error("Error collecting relay traffic: %s", e)
        return {}

