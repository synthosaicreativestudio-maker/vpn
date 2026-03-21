import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.getenv("BOT_TOKEN", "8784903598:AAFbs2HJtgVlkcQGX2V6D5V5SAlCXtlvd10")

# Subscription Manager Panel
PANEL_URL = os.getenv("PANEL_URL", "http://127.0.0.1:8085")
PANEL_API_KEY = os.getenv(
    "PANEL_API_KEY",
    "b534ef20bdea908d3b9b4f5388467d525ba88f7abaddcc5ca8b4c159b75335c3",
)

# Database (локальная БД бота для Telegram-привязки)
if os.path.exists("/var/lib/marzban/bot"):
    DB_PATH = "/var/lib/marzban/bot/data/bot_database.db"
else:
    DB_PATH = "bot/data/bot_database.db"
