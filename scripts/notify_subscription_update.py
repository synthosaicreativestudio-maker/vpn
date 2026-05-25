"""Массовая рассылка обновлённой ссылки подписки через Telegram-бот.

Отправляет всем пользователям, у которых email начинается с tg_ или @,
сообщение с просьбой обновить подписку в Happ.

Запуск:
    cd /root/vpn && python3 -m scripts.notify_subscription_update
"""

import asyncio
import logging
import os
import sys

import aiohttp
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Конфиг ────────────────────────────────────────────────────
PANEL_URL = os.getenv("PANEL_URL", "http://127.0.0.1:8085")
PANEL_API_KEY = os.getenv(
    "PANEL_API_KEY",
    "b534ef20bdea908d3b9b4f5388467d525ba88f7abaddcc5ca8b4c159b75335c3",
)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SUB_BASE = "https://37.1.212.51.sslip.io:8086/sub/happ"

# Маппинг email → tg_id (из описания или email)
# Бот может отправлять только по tg_id


async def get_all_users() -> list[dict]:
    """Получить всех пользователей из панели."""
    headers = {"X-API-KEY": PANEL_API_KEY}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{PANEL_URL}/users", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("users", [])
    return []


def extract_tg_id(user: dict) -> int | None:
    """Извлечь Telegram ID из email или description."""
    email = user.get("email", "")

    # Формат tg_123456789
    if email.startswith("tg_"):
        try:
            return int(email[3:])
        except ValueError:
            pass

    # Из description: "Telegram: 123456789" или "Telegram: @username"
    desc = user.get("description") or ""
    if "Telegram:" in desc:
        part = desc.split("Telegram:")[1].strip().split()[0].strip("()")
        if part.isdigit():
            return int(part)

    return None


async def main():
    if not BOT_TOKEN:
        # Пробуем загрузить из .env
        env_path = os.path.join(os.path.dirname(__file__), "..", "bot", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("BOT_TOKEN="):
                        os.environ["BOT_TOKEN"] = line.split("=", 1)[1].strip()
                        break

    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        logger.error("BOT_TOKEN не задан! Укажите в переменной окружения или bot/.env")
        sys.exit(1)

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))

    users = await get_all_users()
    logger.info("Всего пользователей: %d", len(users))

    sent = 0
    failed = 0
    skipped = 0

    for user in users:
        email = user.get("email", "")
        if email == "relay-bridge" or not user.get("is_active"):
            continue

        tg_id = extract_tg_id(user)
        if not tg_id:
            logger.warning("Пропуск %s — нет tg_id", email)
            skipped += 1
            continue

        sub_token = user.get("sub_token", "")
        if not sub_token:
            logger.warning("Пропуск %s — нет sub_token", email)
            skipped += 1
            continue

        sub_url = f"{SUB_BASE}/{sub_token}?routing=ru"

        text = (
            "🔄 <b>Обновление VPN-подписки</b>\n\n"
            "Мы обновили конфигурацию серверов для более стабильной работы.\n\n"
            "📋 <b>Что нужно сделать:</b>\n"
            "1. Откройте Happ\n"
            "2. Нажмите на подписку → «Обновить подписку»\n"
            "3. Если не обновляется — удалите старую подписку и добавьте новую по ссылке ниже\n\n"
            f"🔗 <b>Ваша ссылка подписки:</b>\n"
            f"<code>{sub_url}</code>\n\n"
            "После добавления Happ автоматически выберет лучший сервер. ✅"
        )

        try:
            await bot.send_message(tg_id, text)
            logger.info("✅ Отправлено: %s (tg_id=%d)", email, tg_id)
            sent += 1
            await asyncio.sleep(0.5)  # Антифлуд Telegram
        except Exception as e:
            logger.error("❌ Ошибка %s (tg_id=%d): %s", email, tg_id, e)
            failed += 1

    logger.info(
        "Итого: отправлено=%d, ошибки=%d, пропущено=%d",
        sent, failed, skipped,
    )

    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
