"""VPN Subscription Bot — Telegram-бот для управления подписками.

Работает через Subscription Manager Panel API.
Без оплаты (тестовый режим).
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import BOT_TOKEN, PANEL_API_KEY, PANEL_PUBLIC_URL, PANEL_URL
from bot.data.db_manager import DBManager
from bot.utils.panel_api import PanelAPI

# ── Настройка ─────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
panel = PanelAPI(base_url=PANEL_URL, api_key=PANEL_API_KEY)
db = DBManager()


# ── Helpers ───────────────────────────────────────────────────


def _email_from_tg(user: types.User) -> str:
    """Генерирует уникальный email-идентификатор из Telegram ID."""
    return f"tg_{user.id}"


def _main_keyboard() -> types.InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🚀 Получить VPN", callback_data="register")
    )
    builder.row(
        types.InlineKeyboardButton(text="🔗 Мои ссылки", callback_data="my_links")
    )
    builder.row(
        types.InlineKeyboardButton(text="📊 Статус", callback_data="status")
    )
    return builder.as_markup()


def _apps_keyboard() -> types.InlineKeyboardMarkup:
    """Кнопки для скачивания приложений."""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="🍎 Hiddify (iPhone)",
            url="https://apps.apple.com/app/hiddify-proxy-vpn/id6596777532",
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="🤖 Hiddify (Android)",
            url="https://play.google.com/store/apps/details?id=app.hiddify.com",
        )
    )
    builder.row(
        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")
    )
    return builder.as_markup()


# ── Команды ───────────────────────────────────────────────────


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветствие и главное меню."""
    db.add_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "<b>👋 Привет! Я VPN-бот.</b>\n\n"
        "Я помогу тебе получить доступ к быстрому и безопасному VPN.\n\n"
        "👇 <b>Выберите действие:</b>",
        reply_markup=_main_keyboard(),
    )


@dp.callback_query(F.data == "menu")
async def cb_menu(callback: types.CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.edit_text(
        "<b>🏠 Главное меню</b>\n\nВыберите действие:",
        reply_markup=_main_keyboard(),
    )
    await callback.answer()


# ── Регистрация ───────────────────────────────────────────────


@dp.callback_query(F.data == "register")
async def cb_register(callback: types.CallbackQuery):
    """Регистрация пользователя в панели и выдача ссылок."""
    user = callback.from_user
    email = _email_from_tg(user)

    await callback.message.edit_text("⏳ <b>Создаю ваш VPN-профиль...</b>")

    try:
        # Попытка создать нового юзера
        result = await panel.create_user(
            email=email,
            ip_limit=2,
            expire_days=30,
            description=f"Telegram: @{user.username or user.id}",
        )

        if not result:
            await callback.message.edit_text(
                "❌ <b>Ошибка при создании профиля.</b>\n"
                "Попробуйте позже или напишите в поддержку.",
                reply_markup=_main_keyboard(),
            )
            return

        # Если есть sub_token — новый юзер, сохраняем
        sub_token = result.get("sub_token", "")
        if sub_token:
            sub_url = f"{PANEL_PUBLIC_URL}/sub/{sub_token}"
            db.update_subscription(
                user.id,
                result.get("expires_at", ""),
                sub_url,
            )
        else:
            # Юзер уже существовал — берём sub_url из локальной БД
            user_data = db.get_user(user.id)
            sub_url = user_data[3] if user_data and user_data[3] else ""

        # Получаем ссылки (гарантированно есть для обоих случаев)
        links_data = result if "vless_reality" in result else await panel.get_links(email)

        if links_data:
            vless_link = links_data.get("vless_reality", "")
            text = (
                "✅ <b>Ваш VPN-профиль готов!</b>\n\n"
                "<b>📱 Инструкция:</b>\n"
                "1. Установите приложение Hiddify (кнопки ниже)\n"
                "2. Скопируйте ссылку ниже\n"
                "3. В Hiddify нажмите <b>+</b> → <b>Добавить из буфера</b>\n\n"
                "👇 <b>Ваш ключ (нажмите чтобы скопировать):</b>\n"
                f"<code>{vless_link}</code>\n\n"
            )
            if sub_url:
                text += (
                    "🔄 <b>Ссылка подписки</b> (авто-обновление):\n"
                    f"<code>{sub_url}</code>"
                )
        else:
            text = (
                "✅ <b>Профиль создан!</b>\n\n"
                "Нажмите <b>🔗 Мои ссылки</b> для получения ключей."
            )

        await callback.message.edit_text(text, reply_markup=_apps_keyboard())

    except Exception as e:
        logger.error("Registration error: %s", e)
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка.</b> Попробуйте ещё раз.",
            reply_markup=_main_keyboard(),
        )


# ── Мои ссылки ────────────────────────────────────────────────


@dp.callback_query(F.data == "my_links")
async def cb_my_links(callback: types.CallbackQuery):
    """Показать все VPN-ссылки пользователя."""
    email = _email_from_tg(callback.from_user)

    links_data = await panel.get_links(email)
    if not links_data:
        await callback.answer(
            "❌ Профиль не найден. Нажмите «Получить VPN» сначала.",
            show_alert=True,
        )
        return

    text = "<b>🔗 Ваши VPN-ссылки:</b>\n\n"

    labels = {
        "vless_reality": "🔌 VLESS Vision",
        "vless_xhttp": "🕵️ VLESS xHTTP",
        "vless_grpc": "📡 VLESS gRPC",
        "vless_ws": "🌐 VLESS WebSocket",
        "hysteria2": "🚀 Hysteria2",
        "vless_h2": "🔒 VLESS H2",
    }

    for key, label in labels.items():
        link = links_data.get(key, "")
        if link:
            text += f"<b>{label}:</b>\n<code>{link}</code>\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=_apps_keyboard(),
    )


# ── Статус ────────────────────────────────────────────────────


@dp.callback_query(F.data == "status")
async def cb_status(callback: types.CallbackQuery):
    """Статус подписки и подключения."""
    email = _email_from_tg(callback.from_user)

    # Проверяем связь с панелью
    health = await panel.health()
    panel_ok = health and health.get("status") == "online"
    xray_ok = health.get("xray_connected", False) if health else False

    text = "<b>📊 Статус:</b>\n\n"
    text += f"🖥 Панель: {'✅ Онлайн' if panel_ok else '❌ Оффлайн'}\n"
    text += f"🛡 VPN-сервер: {'✅ Работает' if xray_ok else '❌ Недоступен'}\n\n"

    # Проверяем подписку
    user_data = db.get_user(callback.from_user.id)
    if user_data and user_data[2]:
        text += f"📅 <b>Подписка до:</b> {user_data[2]}\n"
    else:
        text += "🔴 <b>Подписка не активна</b>\n"

    # Проверяем IP
    ips_data = await panel.get_user_ips(email)
    if ips_data:
        count = ips_data.get("count", 0)
        limit = ips_data.get("ip_limit", 2)
        text += f"📱 <b>Устройства:</b> {count}/{limit}\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# ── Запуск ────────────────────────────────────────────────────


async def main():
    logger.info("🤖 VPN Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
