import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "8784903598:AAFbs2HJtgVlkcQGX2V6D5V5SAlCXtlvd10")

# Subscription Manager Panel
PANEL_URL = os.getenv("PANEL_URL", "http://127.0.0.1:8085")
PANEL_PUBLIC_URL = os.getenv("PANEL_PUBLIC_URL", "http://37.1.212.51:8085")
PANEL_API_KEY = os.getenv(
    "PANEL_API_KEY",
    "b534ef20bdea908d3b9b4f5388467d525ba88f7abaddcc5ca8b4c159b75335c3",
)

# Database (локальная БД бота для Telegram-привязки)
if os.path.exists("/var/lib/marzban/bot"):
    DB_PATH = "/var/lib/marzban/bot/data/bot_database.db"
else:
    DB_PATH = "bot/data/bot_database.db"

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
