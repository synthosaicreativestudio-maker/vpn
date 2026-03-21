"""Конфигурация панели управления подписками.

Все значения берутся из переменных окружения (файл .env).
Дефолты соответствуют текущей боевой конфигурации сервера.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ── API Security ──────────────────────────────────────────────
API_KEY = os.getenv("PANEL_API_KEY", "change_me_in_production_2026")
API_KEY_HEADER = "X-API-KEY"

# ── Xray gRPC ─────────────────────────────────────────────────
XRAY_GRPC_HOST = os.getenv("XRAY_GRPC_HOST", "127.0.0.1:10085")

# ── Server ────────────────────────────────────────────────────
SERVER_IP = os.getenv("SERVER_IP", "37.1.212.51")

# ── Protocol Ports ────────────────────────────────────────────
PORT_VLESS_REALITY = int(os.getenv("PORT_VLESS_REALITY", "10443"))
PORT_VLESS_XHTTP = int(os.getenv("PORT_VLESS_XHTTP", "10444"))
PORT_VLESS_GRPC = int(os.getenv("PORT_VLESS_GRPC", "18443"))
PORT_SHADOW_TLS = int(os.getenv("PORT_SHADOW_TLS", "443"))
PORT_TUIC = int(os.getenv("PORT_TUIC", "30445"))
PORT_HYSTERIA2 = int(os.getenv("PORT_HYSTERIA2", "10443"))

# ── Reality Keys ──────────────────────────────────────────────
REALITY_PUBLIC_KEY = os.getenv(
    "REALITY_PUBLIC_KEY",
    "n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4",
)
REALITY_SHORT_ID = os.getenv("REALITY_SHORT_ID", "00")
REALITY_SNI = os.getenv("REALITY_SNI", "taxi.yandex.ru")

# ── Shadow-TLS ────────────────────────────────────────────────
SHADOW_TLS_PASSWORD = os.getenv("SHADOW_TLS_PASSWORD", "SecureShadow2026V3")

# ── Xray Inbound Tags ────────────────────────────────────────
INBOUND_TAG_VISION = os.getenv("INBOUND_TAG_VISION", "VLESS-Reality-Vision")
INBOUND_TAG_XHTTP = os.getenv("INBOUND_TAG_XHTTP", "VLESS-Reality-XHTTP")
INBOUND_TAG_GRPC = os.getenv("INBOUND_TAG_GRPC", "VLESS-Reality-gRPC")

# ── Paths ─────────────────────────────────────────────────────
XRAY_ACCESS_LOG = os.getenv("XRAY_ACCESS_LOG", "/var/lib/marzban/access.log")
DB_PATH = os.getenv("PANEL_DB_PATH", "panel/data/panel.db")
BOT_DB_PATH = os.getenv("BOT_DB_PATH", "bot/data/bot.db")

# ── IP Limit ──────────────────────────────────────────────────
DEFAULT_IP_LIMIT = int(os.getenv("DEFAULT_IP_LIMIT", "2"))
IP_CHECK_INTERVAL = int(os.getenv("IP_CHECK_INTERVAL", "30"))
