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

from bot.config import BOT_TOKEN, PANEL_API_KEY, PANEL_PUBLIC_URL, PANEL_URL, ENABLE_TRIAL_FUNNEL
from bot.data.db_manager import DBManager
from bot.utils.panel_api import PanelAPI

AMNEZIA_VPN_LINK = "vpn://ewogICJjb250YWluZXJzIjogWwogICAgewogICAgICAiY29udGFpbmVyIjogImFtbmV6aWEtYXdnIiwKICAgICAgImluc3RhbGxfaWQiOiAiaW5zdGFsbF8yMDI2XzAzXzIxIiwKICAgICAgInBvcnQiOiAiMzA0NDMiLAogICAgICAicHJvdG9jb2wiOiAiYXdnIiwKICAgICAgInNldHRpbmdzIjogewogICAgICAgICJhZGRyZXNzIjogIjEwLjAuMC4yIiwKICAgICAgICAiaDEiOiAiMSIsCiAgICAgICAgImgyIjogIjIiLAogICAgICAgICJoMyI6ICIzIiwKICAgICAgICAiaDQiOiAiNCIsCiAgICAgICAgImpjIjogIjQiLAogICAgICAgICJqbWF4IjogIjcwIiwKICAgICAgICAiam1pbiI6ICI0MCIsCiAgICAgICAgImxhc3RfY29uZmlnIjogIiIsCiAgICAgICAgIm10dSI6ICIxMjgwIiwKICAgICAgICAicG9ydCI6ICIzMDQ0MyIsCiAgICAgICAgInByaXZhdGVfa2V5IjogIkVKTmlLQ2lBbVhzUThremZoZzQ4dXpSYVlFNWF4anpSbzBpK01OaTVGVVk9IiwKICAgICAgICAicHVibGljX2tleSI6ICJZL1lvalk3Q0lkcmhqdVFjazEwMHkwOERlUmYvWWRJL1R2dXlMMjF1WVZZPSIsCiAgICAgICAgInMxIjogIjUiLAogICAgICAgICJzMiI6ICIxMCIKICAgICAgfQogICAgfQogIF0sCiAgImRlc2NyaXB0aW9uIjogIlByZW1pdW0tVlBOLTIwMjYtQW1uZXppYVdHIiwKICAiaG9zdCI6ICIzNy4xLjIxMi41MSIKfQo="

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
        types.InlineKeyboardButton(text="🍎 Hiddify (iOS)", url="https://apps.apple.com/app/hiddify-proxy-vpn/id6596777532"),
        types.InlineKeyboardButton(text="🤖 Hiddify (Android)", url="https://play.google.com/store/apps/details?id=app.hiddify.com")
    )
    builder.row(
        types.InlineKeyboardButton(text="🍏 Happ (iOS)", url="https://apps.apple.com/app/happ-proxy-utility/id6553971216"),
        types.InlineKeyboardButton(text="👽 Happ (Android)", url="https://play.google.com/store/apps/details?id=com.happ.proxy")
    )
    builder.row(
        types.InlineKeyboardButton(text="🛡 Amnezia (iOS)", url="https://apps.apple.com/app/amneziavpn/id1600529900"),
        types.InlineKeyboardButton(text="🤖 Amnezia (Android)", url="https://play.google.com/store/apps/details?id=org.amnezia.vpn")
    )
    builder.row(
        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")
    )
    return builder.as_markup()


def _os_keyboard() -> types.InlineKeyboardMarkup:
    """Выбор операционной системы."""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🍏 iOS (iPhone/iPad)", callback_data="os_ios"),
        types.InlineKeyboardButton(text="🤖 Android", callback_data="os_android")
    )
    builder.row(
        types.InlineKeyboardButton(text="💻 Windows", callback_data="os_windows"),
        types.InlineKeyboardButton(text="🍎 macOS", callback_data="os_macos")
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

    user_data = db.get_user(user.id)
    sub_url = user_data[3] if user_data and len(user_data) > 3 and user_data[3] else ""

    if ENABLE_TRIAL_FUNNEL:
        if sub_url:
            await callback.message.edit_text(
                "✅ <b>У вас уже есть активная подписка!</b>\n\nНа каком устройстве будем настраивать VPN?",
                reply_markup=_os_keyboard()
            )
            return

        if db.has_user_trial(user.id):
            await callback.message.edit_text(
                "❌ <b>Вы уже использовали бесплатный тестовый период.</b>\nДля продолжения работы необходимо продлить подписку.",
                reply_markup=_main_keyboard()
            )
            return

        await callback.message.edit_text("⏳ <b>Активирую тестовый период (2 дня, 10 ГБ трафика)...</b>")
        is_trial = True
    else:
        await callback.message.edit_text("⏳ <b>Создаю ваш VPN-профиль...</b>")
        is_trial = False

    try:
        if is_trial:
            result = await panel.create_user(
                email=email,
                ip_limit=1,
                expire_days=2,
                description=f"Telegram: @{user.username or user.id} (TRIAL)",
            )
            if result:
                await panel.update_user(email, total_gb=10.0)
                db.set_user_trial(user.id)
        else:
            result = await panel.create_user(
                email=email,
                ip_limit=2,
                expire_days=30,
                description=f"Telegram: @{user.username or user.id}",
            )

        if not result and not sub_url:
            await callback.message.edit_text(
                "❌ <b>Ошибка при создании профиля.</b>\n"
                "Попробуйте позже или напишите в поддержку.",
                reply_markup=_main_keyboard(),
            )
            return

        sub_token = result.get("sub_token", "") if result else ""
        if sub_token:
            sub_url = f"{PANEL_PUBLIC_URL}/sub/{sub_token}"
            db.update_subscription(
                user.id,
                result.get("expires_at", ""),
                sub_url,
            )

        if ENABLE_TRIAL_FUNNEL:
            await callback.message.edit_text(
                "✅ <b>Тестовый период успешно активирован!</b>\n\nНа каком устройстве будем настраивать VPN?",
                reply_markup=_os_keyboard()
            )
            return

        # Старая логика (все ссылки разом)
        links = await panel.get_links(email)
        vless_reality = links.get("vless_reality", "") if links else ""

        if sub_url:
            sub_url_happ = sub_url.replace(f"{PANEL_PUBLIC_URL}/sub/", "https://37.1.212.51.sslip.io:8086/sub/happ/")
            text = (
                "✅ <b>Ваш VPN готов!</b>\n\n"
                "<b>📱 Инструкция:</b>\n"
                "Скопируйте нужную ссылку ниже и добавьте её в приложение (обычно через <b>+</b> → <b>Добавить из буфера</b>).\n\n"
                "🤖/🍏 <b>Для Hiddify:</b>\n"
                "1️⃣ <i>Авто-подписка (HTTP):</i>\n"
                f"<pre>{sub_url}</pre>\n"
                "2️⃣ <i>Прямая ссылка (VLESS xHTTP):</i>\n"
                f"<pre>{vless_reality}</pre>\n\n"
                "🍏/👽 <b>Для Happ:</b>\n"
                "1️⃣ <i>Авто-подписка (HTTPS):</i>\n"
                f"<pre>{sub_url_happ}</pre>\n"
                "2️⃣ <i>Прямая ссылка (VLESS xHTTP):</i>\n"
                f"<pre>{vless_reality}</pre>\n\n"
                "🛡 <b>Для AmneziaVPN:</b>\n"
                "1️⃣ <i>Прямая ссылка (VLESS Vision):</i>\n"
                f"<pre>{vless_reality}</pre>\n"
                "2️⃣ <i>Конфиг JSON (AmneziaWG):</i>\n"
                f"<pre>{AMNEZIA_VPN_LINK}</pre>"
            )
        else:
            text = "✅ <b>Профиль создан!</b>\nНе удалось получить ссылку."
        await callback.message.edit_text(text, reply_markup=_apps_keyboard())

    except Exception as e:
        logger.error("Registration error: %s", e)
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка.</b> Попробуйте ещё раз.",
            reply_markup=_main_keyboard(),
        )


@dp.callback_query(F.data.startswith("os_"))
async def cb_os_selection(callback: types.CallbackQuery):
    """Выдача конкретной инструкции по ОС."""
    os_type = callback.data.split("_")[1]
    user_data = db.get_user(callback.from_user.id)
    sub_url = user_data[3] if user_data and len(user_data) > 3 and user_data[3] else None

    if not sub_url:
        await callback.answer("❌ Профиль не найден. Нажмите «Получить VPN».", show_alert=True)
        return

    hiddify_ios = "https://apps.apple.com/app/hiddify-proxy-vpn/id6596777532"
    hiddify_android = "https://play.google.com/store/apps/details?id=app.hiddify.com"
    hiddify_windows = "https://github.com/hiddify/hiddify-next/releases/latest"
    hiddify_macos = "https://github.com/hiddify/hiddify-next/releases/latest"

    app_link = ""
    if os_type == "ios":
        app_link = hiddify_ios
        os_name = "iOS (AppStore)"
    elif os_type == "android":
        app_link = hiddify_android
        os_name = "Android (Google Play)"
    elif os_type == "windows":
        app_link = hiddify_windows
        os_name = "Windows"
    else:
        app_link = hiddify_macos
        os_name = "macOS"

    text = (
        f"📱 Инструкция для <b>{os_name}</b>:\n\n"
        f"<b>Шаг 1:</b> Скачайте и установите приложение <b>Hiddify</b> по ссылке ниже.\n\n"
        f"<b>Шаг 2:</b> Нажмите на эту ссылку, чтобы скопировать её:\n"
        f"<code>{sub_url}</code>\n\n"
        f"<b>Шаг 3:</b> Откройте Hiddify, нажмите <b>«Новый профиль»</b> (или значок ➕), выберите <b>«Добавить из буфера обмена»</b> и нажмите большую кнопку для подключения."
    )

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📥 Скачать Hiddify", url=app_link))
    builder.row(types.InlineKeyboardButton(text="🔄 Инструкция для другого устройства", callback_data="register"))
    builder.row(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu"))

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


# ── Мои ссылки ────────────────────────────────────────────────


@dp.callback_query(F.data == "my_links")
async def cb_my_links(callback: types.CallbackQuery):
    """Показать ссылку подписки пользователя."""
    email = _email_from_tg(callback.from_user)
    user_data = db.get_user(callback.from_user.id)
    sub_url = user_data[3] if user_data and len(user_data) > 3 and user_data[3] else None

    if not sub_url:
        await callback.answer(
            "❌ Профиль не найден. Нажмите «Получить VPN» сначала.",
            show_alert=True,
        )
        return

    if ENABLE_TRIAL_FUNNEL:
        await callback.message.edit_text(
            "✅ <b>У вас есть активная подписка!</b>\n\nНа каком устройстве выбрать инструкцию?",
            reply_markup=_os_keyboard()
        )
        return

    links = await panel.get_links(email)
    vless_reality = links.get("vless_reality", "") if links else ""

    sub_url_happ = sub_url.replace(f"{PANEL_PUBLIC_URL}/sub/", "https://37.1.212.51.sslip.io:8086/sub/happ/")
    text = (
        "<b>🔗 Ваши ссылки подписки:</b>\n\n"
        "Скопируйте нужную ссылку для вашего приложения:\n\n"
        "🤖/🍏 <b>Для Hiddify:</b>\n"
        "1️⃣ <i>Авто-подписка (HTTP):</i>\n"
        f"<pre>{sub_url}</pre>\n"
        "2️⃣ <i>Прямая ссылка (VLESS xHTTP):</i>\n"
        f"<pre>{vless_reality}</pre>\n\n"
        "🍏/👽 <b>Для Happ:</b>\n"
        "1️⃣ <i>Авто-подписка (HTTPS):</i>\n"
        f"<pre>{sub_url_happ}</pre>\n"
        "2️⃣ <i>Прямая ссылка (VLESS xHTTP):</i>\n"
        f"<pre>{vless_reality}</pre>\n\n"
        "🛡 <b>Для AmneziaVPN:</b>\n"
        "1️⃣ <i>Прямая ссылка (VLESS Vision):</i>\n"
        f"<pre>{vless_reality}</pre>\n"
        "2️⃣ <i>Конфиг JSON (AmneziaWG):</i>\n"
        f"<pre>{AMNEZIA_VPN_LINK}</pre>"
    )

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
