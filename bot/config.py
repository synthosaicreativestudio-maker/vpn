import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Subscription Manager Panel
PANEL_URL = os.getenv("PANEL_URL", "http://127.0.0.1:8085")
PANEL_PUBLIC_URL = os.getenv("PANEL_PUBLIC_URL", "http://38.180.81.181:8085")
PANEL_API_KEY = os.getenv(
    "PANEL_API_KEY",
    "b534ef20bdea908d3b9b4f5388467d525ba88f7abaddcc5ca8b4c159b75335c3",
)

# Database (локальная БД бота для Telegram-привязки)
DB_PATH = "bot/data/bot.db"

# Feature Toggles
ENABLE_TRIAL_FUNNEL = os.getenv("ENABLE_TRIAL_FUNNEL", "False").lower() == "true"

# ── Тарифные планы ────────────────────────────────────────────
PLANS = {
    "trial": {"name": "🆓 Тест 3 дня", "days": 3, "price": 0, "traffic_gb": 10, "ip_limit": 2},
    "1m": {"name": "1 месяц", "days": 30, "price": 200, "traffic_gb": 50, "ip_limit": 2},
    "3m": {"name": "3 месяца", "days": 90, "price": 500, "traffic_gb": 50, "ip_limit": 2},
    "5m": {"name": "5 месяцев", "days": 150, "price": 1000, "traffic_gb": 50, "ip_limit": 2},
    "12m": {"name": "12 месяцев", "days": 365, "price": 1500, "traffic_gb": 50, "ip_limit": 2},
}

# ── Т-Банк Эквайринг ─────────────────────────────────────────
TBANK_TERMINAL_KEY = os.getenv("TBANK_TERMINAL_KEY", "1778844937330DEMO")
TBANK_PASSWORD = os.getenv("TBANK_PASSWORD", "oBDLqS9c34ydSNdZ")
TBANK_API_URL = "https://securepay.tinkoff.ru/v2/"

# Relay configuration for subscription links
RELAY_ENABLED = os.getenv("RELAY_ENABLED", "True").lower() == "true"
RELAY_IP = os.getenv("RELAY_IP", "185.4.67.223")
SERVER_IP = os.getenv("SERVER_IP", "38.180.81.181")

# Домен Cloudflare CDN для резервного WebSocket канала
CLOUDFLARE_CDN_DOMAIN = os.getenv("CLOUDFLARE_CDN_DOMAIN", "fredom.ru")

if RELAY_ENABLED:
    SUB_HOST = "sub.synthosai.ru"
else:
    SUB_HOST = f"{SERVER_IP}.sslip.io"
# HTTP порт 80 — стандартный, не блокируется DPI (ранее 8086 блокировался)
SUB_PORT = int(os.getenv("SUB_PORT", "80"))
