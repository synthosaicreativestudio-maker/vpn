import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN") # Токен от ЮKassa

# Marzban API Settings
MARZBAN_URL = os.getenv("MARZBAN_URL", "http://37.1.212.51:8000")
MARZBAN_USERNAME = os.getenv("MARZBAN_USERNAME", "admin")
MARZBAN_PASSWORD = os.getenv("MARZBAN_PASSWORD", "admin_LEJ6U5chSK")

# Database
if os.path.exists("/var/lib/marzban/bot"):
    DB_PATH = "/var/lib/marzban/bot/data/bot_database.db"
else:
    DB_PATH = "bot/data/bot_database.db"
