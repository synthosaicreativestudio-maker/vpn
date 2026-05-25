#!/usr/bin/env python3
"""Скрипт для массовой рассылки новых персонализированных ссылок пользователям бота."""

import asyncio
import logging
import sqlite3
import sys
import os

# Добавляем корневую папку в пути импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot
from bot.config import BOT_TOKEN, DB_PATH, SUB_HOST

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("broadcast")


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in configuration!")
        return

    bot = Bot(token=BOT_TOKEN)

    # Подключаемся к БД бота
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        users = cursor.execute("SELECT tg_id, username FROM users").fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to read users from database: {e}")
        return

    if not users:
        logger.info("No users found in database.")
        return

    logger.info(f"Starting broadcast for {len(users)} users...")

    sent_count = 0
    failed_count = 0

    for user in users:
        tg_id = user["tg_id"]
        username = user["username"]

        # Определяем имя для ссылки (email в панели)
        # В панели email формируется как: tg_id, если нет юзернейма, или @username (legacy) / username
        # Но по нашей логике _resolve_email в боте:
        # tg_id -> @username -> username
        # Давайте сделаем имя для ссылки красивым:
        if username:
            sub_name = username
        else:
            sub_name = f"tg_{tg_id}"

        # Красивая релейная ссылка
        sub_url = f"https://{SUB_HOST}:8086/sub/happ/{sub_name}?routing=ru"

        message_text = (
            f"👋 <b>Привет! Мы полностью обновили и улучшили систему обхода блокировок в РФ.</b>\n\n"
            f"Ваш VPN-туннель теперь работает напрямую через сверхбыстрые российские облачные сервера!\n\n"
            f"👇 <b>Пожалуйста, скопируйте эту новую персональную ссылку и вставьте её в приложение Happ вместо старой:</b>\n\n"
            f"<code>{sub_url}</code>\n\n"
            f"<i>Инструкция: Откройте Happ ➡️ Нажмите «+» ➡️ «Добавить из буфера обмена» ➡️ Нажмите кнопку подключения.\n\n"
            f"После этого ваша подписка будет автоматически и стабильно работать напрямую из РФ без сбоев!</i>"
        )

        try:
            await bot.send_message(chat_id=tg_id, text=message_text, parse_mode="HTML")
            logger.info(f"Successfully sent to {tg_id} (@{username or 'no_username'})")
            sent_count += 1
            # Пауза, чтобы не превысить лимиты Telegram (30 сообщений в секунду)
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Failed to send to {tg_id} (@{username or 'no_username'}): {e}")
            failed_count += 1

    logger.info(f"Broadcast completed. Sent: {sent_count}, Failed: {failed_count}")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
