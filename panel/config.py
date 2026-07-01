"""Конфигурация панели управления подписками.

Все значения берутся из переменных окружения (файл panel/.env).
ВАЖНО: Никогда не указывать реальные секреты как дефолты в коде.
       Создайте panel/.env по образцу panel/.env.example.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("panel.config")

# ── API Security ──────────────────────────────────────────────
API_KEY = os.getenv("PANEL_API_KEY", "")
if not API_KEY:
    logger.warning(
        "⚠️  PANEL_API_KEY не задан! Используется небезопасный дефолт. "
        "Установите переменную окружения PANEL_API_KEY в panel/.env"
    )
    # Используем дефолт только для обратной совместимости
    API_KEY = "b534ef20bdea908d3b9b4f5388467d525ba88f7abaddcc5ca8b4c159b75335c3"
API_KEY_HEADER = "X-API-KEY"

# ── Xray gRPC ─────────────────────────────────────────────────
XRAY_GRPC_HOST = os.getenv("XRAY_GRPC_HOST", "127.0.0.1:10085")

# ── Server ────────────────────────────────────────────────────
SERVER_IP = os.getenv("SERVER_IP", "38.180.81.181")

# ── Protocol Ports ────────────────────────────────────────────
# Xray VLESS+Reality (4 транспорта на разных портах)
PORT_VLESS_REALITY = int(os.getenv("PORT_VLESS_REALITY", "443"))
PORT_VLESS_XHTTP = int(os.getenv("PORT_VLESS_XHTTP", "8443"))
PORT_VLESS_GRPC = int(os.getenv("PORT_VLESS_GRPC", "2053"))
PORT_VLESS_WS = int(os.getenv("PORT_VLESS_WS", "2083"))
# Standalone Hysteria2 (UDP/QUIC)
PORT_HYSTERIA2 = int(os.getenv("PORT_HYSTERIA2", "10443"))



# ── Reality Keys ──────────────────────────────────────────────
REALITY_PUBLIC_KEY = os.getenv(
    "REALITY_PUBLIC_KEY",
    "n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4",
)
REALITY_SHORT_ID = os.getenv("REALITY_SHORT_ID", "0123456789abcdef")
REALITY_SNI = os.getenv("REALITY_SNI", "www.microsoft.com")

# ── Hysteria2 ─────────────────────────────────────────────────
HYSTERIA2_PASSWORD = os.getenv("HYSTERIA2_PASSWORD", "HysteriaPassword2026")
HYSTERIA2_SNI = os.getenv("HYSTERIA2_SNI", "www.microsoft.com")
HYSTERIA2_OBFS_PASSWORD = os.getenv("HYSTERIA2_OBFS_PASSWORD", "SalamanderObfs2026SecretKey")

# ── Shadowsocks 2022 ─────────────────────────────────────────
PORT_SHADOWSOCKS = int(os.getenv("PORT_SHADOWSOCKS", "2085"))
SHADOWSOCKS_METHOD = os.getenv("SHADOWSOCKS_METHOD", "2022-blake3-aes-256-gcm")
SHADOWSOCKS_PASSWORD = os.getenv("SHADOWSOCKS_PASSWORD", "vUHfGuAyhJlEGStg1P3YllhMbXvGA9Ib1XDyFu2khi0=")

# ── Xray Inbound Tags ────────────────────────────────────────
INBOUND_TAG_VISION = os.getenv("INBOUND_TAG_VISION", "VLESS-Reality-Vision")
INBOUND_TAG_XHTTP = os.getenv("INBOUND_TAG_XHTTP", "VLESS-Reality-XHTTP")
INBOUND_TAG_GRPC = os.getenv("INBOUND_TAG_GRPC", "VLESS-Reality-gRPC")
INBOUND_TAG_WS = os.getenv("INBOUND_TAG_WS", "VLESS-WS")


# ── Paths ─────────────────────────────────────────────────────
XRAY_ACCESS_LOG = os.getenv("XRAY_ACCESS_LOG", "/var/log/xray/access.log")
DB_PATH = os.getenv("PANEL_DB_PATH", "panel/data/panel.db")
BOT_DB_PATH = os.getenv("BOT_DB_PATH", "bot/data/bot.db")

# ── IP Limit ──────────────────────────────────────────────────
DEFAULT_IP_LIMIT = int(os.getenv("DEFAULT_IP_LIMIT", "2"))
IP_CHECK_INTERVAL = int(os.getenv("IP_CHECK_INTERVAL", "30"))

# ── Feature Toggles ───────────────────────────────────────────
ENABLE_TRAFFIC_LIMITS = os.getenv("ENABLE_TRAFFIC_LIMITS", "True").lower() == "true"
ENABLE_IP_LIMITS = os.getenv("ENABLE_IP_LIMITS", "True").lower() == "true"

# ── Relay RU (обход белых списков ТСПУ) ───────────────────────
# Модуль: relay-chain через РФ VPS (Yandex Cloud)
# Подключение/отключение не влияет на основные каналы
RELAY_ENABLED = os.getenv("RELAY_ENABLED", "False").lower() == "true"
RELAY_IP = os.getenv("RELAY_IP", "185.4.67.223")
RELAY_PORT = int(os.getenv("RELAY_PORT", "443"))

# Домен Cloudflare CDN для резервного WebSocket канала
CLOUDFLARE_CDN_DOMAIN = os.getenv("CLOUDFLARE_CDN_DOMAIN", "fredom.ru")

if RELAY_ENABLED:
    SUB_HOST = "sub.synthosai.ru"
else:
    SUB_HOST = f"{SERVER_IP}.sslip.io"
# HTTP порт 80 — стандартный, не блокируется DPI (ранее 8086 блокировался)
SUB_PORT = int(os.getenv("SUB_PORT", "80"))
RELAY_UUID = os.getenv("RELAY_UUID", "57ca4aae-dcb3-4fdd-9e14-f9afb42b703c")
RELAY_PUBLIC_KEY = os.getenv(
    "RELAY_PUBLIC_KEY",
    "t4Icv6qrpPcxWOp9uxyLbL2cWJ5_QRcXcC1gJ06To1g",
)
RELAY_SHORT_ID = os.getenv("RELAY_SHORT_ID", "abcdef0123456789")
RELAY_SNI = os.getenv("RELAY_SNI", "ozon.ru")
RELAY_GRPC_ENABLED = os.getenv("RELAY_GRPC_ENABLED", "False").lower() == "true"
RELAY_GRPC_HOST = os.getenv("RELAY_GRPC_HOST", "51.250.94.182:10085")


# ── Тесты обхода белых списков (3 независимых релея) ─────────
TEST_RELAYS_ENABLED = os.getenv("TEST_RELAYS_ENABLED", "False").lower() == "true"
TEST_RELAY_IPS = [
    os.getenv("TEST_RELAY_IP_1", "0.0.0.0"),
    os.getenv("TEST_RELAY_IP_2", "0.0.0.0"),
    os.getenv("TEST_RELAY_IP_3", "0.0.0.0"),
]
TEST_RELAY_PORT = int(os.getenv("TEST_RELAY_PORT", "8081"))
TEST_RELAY_SNI = os.getenv("TEST_RELAY_SNI", "ads.x5.ru")
TEST_RELAY_FP = os.getenv("TEST_RELAY_FP", "edge")

# Обратная совместимость
ANTI_STUB_ENABLED = TEST_RELAYS_ENABLED
ANTI_STUB_IP = TEST_RELAY_IPS[0]
ANTI_STUB_PORT = TEST_RELAY_PORT
ANTI_STUB_SNI = TEST_RELAY_SNI
ANTI_STUB_FP = TEST_RELAY_FP


