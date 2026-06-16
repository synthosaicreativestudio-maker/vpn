"""VPN Subscription Bot — Telegram-бот для управления подписками.

Работает через Subscription Manager Panel API.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

from bot.config import BOT_TOKEN, PANEL_API_KEY, PANEL_URL, PLANS, SUB_HOST
from bot.data.db_manager import DBManager
from bot.utils.panel_api import PanelAPI
from bot.tbank import init_tbank_payment

AMNEZIA_VPN_LINK = "vpn://ewogICJjb250YWluZXJzIjogWwogICAgewogICAgICAiY29udGFpbmVyIjogImFtbmV6aWEtYXdnIiwKICAgICAgImluc3RhbGxfaWQiOiAiaW5zdGFsbF8yMDI2XzAzXzIxIiwKICAgICAgInBvcnQiOiAiMzA0NDMiLAogICAgICAicHJvdG9jb2wiOiAiYXdnIiwKICAgICAgInNldHRpbmdzIjogewogICAgICAgICJhZGRyZXNzIjogIjEwLjAuMC4yIiwKICAgICAgICAiaDEiOiAiMSIsCiAgICAgICAgImgyIjogIjIiLAogICAgICAgICJoMyI6ICIzIiwKICAgICAgICAiaDQiOiAiNCIsCiAgICAgICAgImpjIjogIjQiLAogICAgICAgICJqbWF4IjogIjcwIiwKICAgICAgICAiam1pbiI6ICI0MCIsCiAgICAgICAgImxhc3RfY29uZmlnIjogIiIsCiAgICAgICAgIm10dSI6ICIxMjgwIiwKICAgICAgICAicG9ydCI6ICIzMDQ0MyIsCiAgICAgICAgInByaXZhdGVfa2V5IjogIkVKTmlLQ2lBbVhzUThremZoZzQ4dXpSYVlFNWF4anpSbzBpK01OaTVGVVk9IiwKICAgICAgICAicHVibGljX2tleSI6ICJZL1lvalk3Q0lkcmhqdVFjazEwMHkwOERlUmYvWWRJL1R2dXlMMjF1WVZZPSIsCiAgICAgICAgInMxIjogIjUiLAogICAgICAgICJzMiI6ICIxMCIKICAgICAgfQogICAgfQogIF0sCiAgImRlc2NyaXB0aW9uIjogIlByZW1pdW0tVlBOLTIwMjYtQW1uZXppYVdHIiwKICAiaG9zdCI6ICIzNy4xLjIxMi41MSIKfQo="

# ── PID Lock (предотвращает запуск двух экземпляров бота) ───────────────────
_PID_FILE = "/tmp/vpn_bot.pid"


def _acquire_pid_lock() -> bool:
    """Проверить, что нет другого запущенного бота. 
    Возвращает False если другой процесс уже запущен.
    """
    if os.path.exists(_PID_FILE):
        try:
            with open(_PID_FILE) as f:
                old_pid = int(f.read().strip())
            # Проверяем, жив ли процесс
            os.kill(old_pid, 0)
            return False  # Процесс жив, не запускаемся
        except (ProcessLookupError, ValueError):
            pass  # Процесс мёртв, перезапишем PID

    with open(_PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def _release_pid_lock():
    """\u0423далить PID-файл при остановке."""
    if os.path.exists(_PID_FILE):
        try:
            os.remove(_PID_FILE)
        except OSError:
            pass


# ── Настройка ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
panel = PanelAPI(base_url=PANEL_URL, api_key=PANEL_API_KEY)
db = DBManager()


# ── Helpers ───────────────────────────────────────────────────


async def _resolve_email(user: types.User) -> str:
    """Находит существующего пользователя или создаёт email.

    Порядок: tg_ID → @username (legacy) → username (без @).
    """
    # Проверяем по старому формату tg_ID
    old_email = f"tg_{user.id}"
    existing = await panel.get_user(old_email)
    if existing:
        return old_email
    # Проверяем по username
    if user.username:
        # Legacy формат с @
        legacy = f"@{user.username}"
        existing = await panel.get_user(legacy)
        if existing:
            return legacy
        # Новый формат без @ (совместим с Xray access log)
        clean = user.username
        existing = await panel.get_user(clean)
        if existing:
            return clean
        return clean
    return old_email


def _parse_expiry(raw: str) -> tuple[str, int]:
    """Парсит дату истечения. Возвращает (date_str, days_left)."""
    dt_str = raw[:10]  # "2026-05-18"
    try:
        # Убираем микросекунды и добавляем UTC если нет timezone
        clean = raw.replace("Z", "+00:00")
        if "+" not in clean[10:] and "-" not in clean[11:]:
            clean += "+00:00"
        expires = datetime.fromisoformat(clean)
        days_left = (expires - datetime.now(timezone.utc)).days
    except Exception:
        days_left = -1
    return dt_str, days_left


def _fmt_gb(value: float) -> str:
    """Форматирует Гб: показывает МБ если < 1 Гб."""
    if value < 1.0:
        return f"{value * 1024:.0f} МБ"
    return f"{value:.2f} Гб"


async def _get_happ_url(user: types.User) -> str | None:
    """Получить актуальную Happ-ссылку из панели."""
    email = await _resolve_email(user)
    user_info = await panel.get_user(email)
    if user_info and user_info.get("sub_token"):
        # HTTP:80 — стандартный порт, не блокируется DPI
        return (
            f"http://{SUB_HOST}/sub/happ/"
            f"{user_info['sub_token']}?routing=ru"
        )
    return None


async def _get_hiddify_url(user: types.User) -> str | None:
    """Получить актуальную Hiddify-ссылку из панели."""
    email = await _resolve_email(user)
    user_info = await panel.get_user(email)
    if user_info and user_info.get("sub_token"):
        # HTTP:80 — стандартный порт, не блокируется DPI
        return (
            f"http://{SUB_HOST}/sub/hiddify/"
            f"{user_info['sub_token']}?routing=ru"
        )
    return None


def _main_keyboard() -> types.InlineKeyboardMarkup:
    """Главное меню бота."""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🚀 Получить VPN", callback_data="register")
    )
    builder.row(
        types.InlineKeyboardButton(text="🔗 Моя подписка", callback_data="my_links"),
        types.InlineKeyboardButton(text="📊 Статус", callback_data="status")
    )
    builder.row(
        types.InlineKeyboardButton(text="💳 Продлить", callback_data="plans")
    )
    return builder.as_markup()


def _plans_keyboard(show_trial: bool = True) -> types.InlineKeyboardMarkup:
    """Клавиатура выбора тарифного плана."""
    builder = InlineKeyboardBuilder()
    if show_trial:
        builder.row(types.InlineKeyboardButton(
            text="🆓 Попробовать 3 дня (бесплатно)",
            callback_data="plan_trial"
        ))
    builder.row(types.InlineKeyboardButton(
        text="1 мес — 200₽", callback_data="plan_1m"
    ))
    builder.row(types.InlineKeyboardButton(
        text="3 мес — 500₽", callback_data="plan_3m"
    ))
    builder.row(types.InlineKeyboardButton(
        text="5 мес — 1 000₽", callback_data="plan_5m"
    ))
    builder.row(types.InlineKeyboardButton(
        text="12 мес — 1 500₽ ⭐", callback_data="plan_12m"
    ))
    builder.row(types.InlineKeyboardButton(
        text="🏠 Главное меню", callback_data="menu"
    ))
    return builder.as_markup()


def _apps_keyboard() -> types.InlineKeyboardMarkup:
    """Кнопки для скачивания Happ."""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🍏 Happ (iOS)", url="https://apps.apple.com/app/happ-proxy-utility/id6553971216"),
        types.InlineKeyboardButton(text="🤖 Happ (Android)", url="https://play.google.com/store/apps/details?id=com.happ.proxy")
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
        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")
    )
    return builder.as_markup()


def _app_select_keyboard(os_type: str) -> types.InlineKeyboardMarkup:
    """Выбор приложения (Happ или Hiddify) для конкретной ОС."""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="📱 Happ", callback_data=f"app_happ_{os_type}"),
        types.InlineKeyboardButton(text="🛡 Hiddify", callback_data=f"app_hiddify_{os_type}")
    )
    builder.row(
        types.InlineKeyboardButton(text="🔄 Изменить ОС", callback_data="register_os")
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
    """Показать выбор тарифного плана."""
    user = callback.from_user
    email = await _resolve_email(user)

    # Проверяем, есть ли уже подписка
    existing = await panel.get_user(email)
    if existing and existing.get("is_active"):
        # Формируем статус подписки
        text = "✅ <b>У вас уже есть активная подписка!</b>\n\n"

        # Дата и оставшиеся дни
        raw = existing.get("expires_at", "")
        if raw:
            dt_str, days_left = _parse_expiry(raw)
            if days_left > 0:
                text += f"📅 <b>Подписка до:</b> {dt_str} ({days_left} дн.)\n"
            else:
                text += f"📅 <b>Подписка:</b> истекла {dt_str}\n"
        else:
            text += "♾ <b>Подписка:</b> бессрочная\n"

        # Трафик
        used = existing.get("used_gb", 0)
        total = existing.get("total_gb", 0)
        if total > 0:
            text += f"📊 <b>Трафик:</b> {_fmt_gb(used)} / {total:.0f} Гб\n"
        else:
            text += f"📊 <b>Трафик:</b> {_fmt_gb(used)} (безлимит)\n"

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(
            text="📱 Настроить устройство", callback_data="register_os"
        ))
        builder.row(types.InlineKeyboardButton(
            text="💳 Продлить подписку", callback_data="plans"
        ))
        builder.row(types.InlineKeyboardButton(
            text="🏠 Главное меню", callback_data="menu"
        ))
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        return

    # Показываем тарифы
    show_trial = not db.has_user_trial(user.id)
    await callback.message.edit_text(
        "<b>📋 Выберите тарифный план:</b>\n\n"
        "Все планы включают:\n"
        "• Обход блокировок РФ\n"
        "• До 2 устройств\n"
        "• Трафик 50 Гб/мес\n",
        reply_markup=_plans_keyboard(show_trial=show_trial),
    )
    await callback.answer()


@dp.callback_query(F.data == "plans")
async def cb_plans(callback: types.CallbackQuery):
    """Показать тарифные планы для продления."""
    show_trial = not db.has_user_trial(callback.from_user.id)
    await callback.message.edit_text(
        "<b>💳 Выберите тариф для продления:</b>",
        reply_markup=_plans_keyboard(show_trial=show_trial),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan_select(callback: types.CallbackQuery):
    """Обработка выбора тарифного плана."""
    plan_id = callback.data.replace("plan_", "")
    plan = PLANS.get(plan_id)
    if not plan:
        await callback.answer("❌ План не найден", show_alert=True)
        return

    user = callback.from_user
    email = await _resolve_email(user)

    # Тестовый период
    if plan_id == "trial":
        if db.has_user_trial(user.id):
            await callback.answer(
                "❌ Вы уже использовали тестовый период", show_alert=True
            )
            return

        await callback.message.edit_text(
            "⏳ <b>Активирую тестовый период (3 дня, 10 Гб)...</b>"
        )
        try:
            result = await panel.create_user(
                email=email,
                ip_limit=plan["ip_limit"],
                expire_days=plan["days"],
                description=f"Telegram: @{user.username or user.id} (TRIAL)",
            )
            if result:
                await panel.update_user(email, total_gb=plan["traffic_gb"])
                db.set_user_trial(user.id)
                sub_token = result.get("sub_token", "")
                if sub_token:
                    sub_url = f"http://{SUB_HOST}/sub/happ/{sub_token}?routing=ru"
                    db.update_subscription(user.id, result.get("expires_at", ""), sub_url)
                await callback.message.edit_text(
                    "✅ <b>Тестовый период активирован!</b>\n\n"
                    f"📅 Срок: {plan['days']} дня\n"
                    f"📊 Трафик: {plan['traffic_gb']} Гб\n\n"
                    "На каком устройстве настраиваем?",
                    reply_markup=_os_keyboard(),
                )
            else:
                await callback.message.edit_text(
                    "❌ <b>Ошибка создания.</b> Попробуйте позже.",
                    reply_markup=_main_keyboard(),
                )
        except Exception as e:
            logger.error("Trial error: %s", e)
            await callback.message.edit_text(
                "❌ <b>Ошибка.</b> Попробуйте позже.",
                reply_markup=_main_keyboard(),
            )
        return

    # Генерируем прямую ссылку на оплату в Т-Банке
    order_id = f"TG_{user.id}_{int(time.time())}"
    
    # Отправляем сообщение об ожидании
    wait_msg = await callback.message.edit_text("⏳ Инициализация защищенного соединения с Т-Банком...")
    
    pay_url = await init_tbank_payment(plan['price'], order_id, "IT-консалтинг и безопасность")
    
    if not pay_url:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🏠 Назад", callback_data="menu"))
        await wait_msg.edit_text("❌ Ошибка при создании платежа. Пожалуйста, попробуйте позже.", reply_markup=builder.as_markup())
        return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💳 Оплатить", url=pay_url))
    builder.row(types.InlineKeyboardButton(text="🏠 Отмена", callback_data="menu"))

    await wait_msg.edit_text(
        f"<b>💳 План: {plan['name']}</b>\n\n"
        f"💰 Стоимость: {plan['price']}₽\n"
        f"📅 Срок: {plan['days']} дней\n"
        f"📊 Трафик: {plan['traffic_gb']} Гб/мес\n"
        f"📱 Устройства: {plan['ip_limit']}\n\n"
        "<i>Нажмите кнопку «Оплатить», чтобы перейти в безопасный шлюз Т-Банка.\n"
        "Сразу после успешной оплаты бот пришлет вам ссылку на VPN.</i>",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()




@dp.callback_query(F.data == "register_os")
async def cb_register_os(callback: types.CallbackQuery):
    """Переход на выбор ОС из экрана подписки."""
    await callback.message.edit_text(
        "📱 <b>На каком устройстве настраиваем?</b>",
        reply_markup=_os_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("os_"))
async def cb_os_selection(callback: types.CallbackQuery):
    """Переход на выбор приложения для выбранной ОС."""
    os_type = callback.data.split("_")[1]

    text = (
        "<b>🎨 Выберите приложение для настройки:</b>\n\n"
        "Мы поддерживаем два современных и удобных приложения:\n\n"
        "1. <b>Happ</b> (Sing-Box) — Рекомендуемое легкое приложение с красивым интерфейсом.\n"
        "2. <b>Hiddify</b> — Мощный кроссплатформенный клиент с глубокой аналитикой.\n\n"
        "Выберите оболочку, которую хотите настроить:"
    )
    await callback.message.edit_text(text, reply_markup=_app_select_keyboard(os_type))
    await callback.answer()


@dp.callback_query(F.data.startswith("app_"))
async def cb_app_selection(callback: types.CallbackQuery):
    """Выдача инструкции и ссылки для выбранного приложения и ОС."""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("❌ Неверный запрос", show_alert=True)
        return

    client = parts[1]      # "happ" или "hiddify"
    os_type = parts[2]     # "ios" or "android"
    user = callback.from_user

    if client == "happ":
        sub_url = await _get_happ_url(user)
        if not sub_url:
            await callback.answer("❌ Профиль не найден. Нажмите «Получить VPN».", show_alert=True)
            return

        happ_ios = "https://apps.apple.com/app/happ-proxy-utility/id6553971216"
        happ_android = "https://play.google.com/store/apps/details?id=com.happ.proxy"

        app_link = happ_ios if os_type == "ios" else happ_android
        os_name = "iOS (AppStore)" if os_type == "ios" else "Android (Google Play)"

        text = (
            f"📱 Инструкция для <b>Happ ({os_name})</b>:\n\n"
            f"<b>Шаг 1:</b> Скачайте <b>Happ</b> по кнопке ниже.\n\n"
            f"<b>Шаг 2:</b> Скопируйте ссылку подписки (она в следующем сообщении).\n\n"
            f"<b>Шаг 3:</b> Откройте Happ → нажмите <b>+</b> → <b>Добавить из буфера обмена</b> → нажмите кнопку подключения."
        )

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="📥 Скачать Happ", url=app_link))
        builder.row(types.InlineKeyboardButton(text="🔄 Изменить приложение", callback_data=f"os_{os_type}"))
        builder.row(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.message.answer(f"<code>{sub_url}</code>")

    elif client == "hiddify":
        sub_url = await _get_hiddify_url(user)
        if not sub_url:
            await callback.answer("❌ Профиль не найден. Нажмите «Получить VPN».", show_alert=True)
            return

        hiddify_ios = "https://apps.apple.com/app/hiddify-next/id6475092033"
        hiddify_android = "https://play.google.com/store/apps/details?id=app.hiddify.com"

        app_link = hiddify_ios if os_type == "ios" else hiddify_android
        os_name = "iOS (AppStore)" if os_type == "ios" else "Android (Google Play)"

        text = (
            f"📱 Инструкция для <b>Hiddify ({os_name})</b>:\n\n"
            f"<b>Шаг 1:</b> Скачайте <b>Hiddify</b> по кнопке ниже.\n\n"
            f"<b>Шаг 2:</b> Скопируйте ссылку подписки (она в следующем сообщении).\n\n"
            f"<b>Шаг 3:</b> Откройте Hiddify → нажмите <b>Новый профиль</b> → <b>Добавить из буфера обмена</b> (или нажмите <b>+ Добавить профиль</b> и вставьте ссылку) → нажмите кнопку подключения."
        )

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="📥 Скачать Hiddify", url=app_link))
        builder.row(types.InlineKeyboardButton(text="🔄 Изменить приложение", callback_data=f"os_{os_type}"))
        builder.row(types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.message.answer(f"<code>{sub_url}</code>")

    await callback.answer()


# ── Мои ссылки ────────────────────────────────────────────────


@dp.callback_query(F.data == "my_links")
async def cb_my_links(callback: types.CallbackQuery):
    """Показать выбор ОС перед выдачей ссылки подписки."""
    sub_url_happ = await _get_happ_url(callback.from_user)

    if not sub_url_happ:
        await callback.answer(
            "❌ Профиль не найден. Нажмите «Получить VPN» сначала.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "📱 <b>На каком устройстве настраиваем подписку?</b>\n\n"
        "Выберите вашу операционную систему для получения оптимальной ссылки и инструкции:",
        reply_markup=_os_keyboard(),
    )
    await callback.answer()


# ── Статус ────────────────────────────────────────────────────


@dp.callback_query(F.data == "status")
async def cb_status(callback: types.CallbackQuery):
    """Статус подписки и подключения."""
    email = await _resolve_email(callback.from_user)

    # Проверяем связь с панелью
    health = await panel.health()
    panel_ok = health and health.get("status") == "online"
    xray_ok = health.get("xray_connected", False) if health else False

    text = "<b>📊 Статус:</b>\n\n"
    text += f"🖥 Панель: {'✅ Онлайн' if panel_ok else '❌ Оффлайн'}\n"
    text += f"🛡 VPN-сервер: {'✅ Работает' if xray_ok else '❌ Недоступен'}\n\n"

    # Проверяем подписку из панели (актуальные данные)
    user_info = await panel.get_user(email)
    if user_info and user_info.get("expires_at"):
        raw = user_info["expires_at"]
        # Форматируем дату красиво
        dt_str, days_left = _parse_expiry(raw)
        if days_left > 0:
            text += f"📅 <b>Подписка до:</b> {dt_str} ({days_left} дн.)\n"
        else:
            text += f"📅 <b>Подписка:</b> истекла {dt_str}\n"
        if not user_info.get("is_active", True):
            text += "🔴 <b>Подписка приостановлена</b>\n"
    elif user_info and not user_info.get("expires_at"):
        text += "♾ <b>Подписка:</b> бессрочная\n"
    else:
        text += "🔴 <b>Подписка не активна</b>\n"

    # Трафик
    if user_info:
        used = user_info.get("used_gb", 0)
        total = user_info.get("total_gb", 0)
        if total > 0:
            text += f"📊 <b>Трафик:</b> {_fmt_gb(used)} / {total:.0f} Гб\n"
        else:
            text += f"📊 <b>Трафик:</b> {_fmt_gb(used)} (безлимит)\n"

    # Устройства (IP count)
    if user_info:
        ips_data = await panel.get_user_ips(email)
        count = ips_data.get("count", 0) if ips_data else 0
        limit = user_info.get("ip_limit", 2)
        text += f"📱 <b>Устройства:</b> {count}/{limit}\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu")
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# ── Webhook T-Bank ────────────────────────────────────────────

async def tbank_webhook(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        logger.info("Webhook from T-Bank: OrderId=%s Status=%s", data.get("OrderId"), data.get("Status"))

        status = data.get("Status")
        if status in ("CONFIRMED", "AUTHORIZED"):
            order_id = data.get("OrderId", "")
            amount_kopecks = data.get("Amount", 0)
            amount = amount_kopecks / 100

            # ── Идемпотентность: не обрабатывать дублирующиеся вебхуки ──
            if db.order_exists(order_id):
                logger.info("Duplicate webhook for order %s — skipping", order_id)
                return web.Response(text="OK", status=200)

            # Парсим tg_id (ожидаем формат TG_12345_123...)
            if order_id.startswith("TG_"):
                parts = order_id.split("_")
                if len(parts) >= 2:
                    tg_id_str = parts[1]
                    try:
                        tg_id = int(tg_id_str)

                        # Определяем план по сумме (хрупко, но работает для текущих тарифов)
                        plan_id = None
                        plan = None
                        amount_to_plan = {200: "1m", 500: "3m", 1000: "5m", 1500: "12m"}
                        plan_id = amount_to_plan.get(int(amount))
                        if plan_id:
                            plan = PLANS.get(plan_id)

                        # Записываем платёж в БД (до активации, для надёжности)
                        db.add_payment(
                            tg_id=tg_id,
                            order_id=order_id,
                            amount=amount,
                            plan_id=plan_id or "unknown",
                            status="CONFIRMED",
                        )

                        # Чек
                        receipt_text = (
                            "🧾 <b>Электронный чек</b>\n\n"
                            f"<b>Услуга:</b> IT-консалтинг и безопасность\n"
                            f"<b>Сумма:</b> {amount:.2f} ₽\n"
                            f"<b>Заказ №:</b> {order_id}\n"
                            f"<b>Статус:</b> Оплачено ✅\n\n"
                        )

                        if plan:
                            email = f"tg_{tg_id}"
                            # Создаем или обновляем пользователя в панели
                            result = await panel.create_user(
                                email=email,
                                ip_limit=plan["ip_limit"],
                                expire_days=plan["days"],
                                description=f"Telegram: {tg_id} (PAID)",
                            )
                            if result:
                                await panel.update_user(email, total_gb=plan["traffic_gb"])
                                if "sub_happ" in result:
                                    sub_url = result["sub_happ"]
                                else:
                                    sub_token = result.get("sub_token", "")
                                    sub_url = f"http://{SUB_HOST}/sub/happ/{sub_token}?routing=ru"
                                db.update_subscription(tg_id, result.get("expires_at", ""), sub_url)

                                success_text = receipt_text + (
                                    "🎉 <b>Оплата успешно получена! Подписка активирована.</b>\n\n"
                                    f"📅 <b>Срок:</b> {plan['days']} дней\n"
                                    f"📊 <b>Трафик:</b> {plan['traffic_gb']} Гб\n\n"
                                    f"Ваша уникальная ссылка для подключения (скопируйте её):\n"
                                    f"<code>{sub_url}</code>\n\n"
                                    f"Для настройки устройства перейдите в <b>🏠 Главное меню</b> → <b>🔗 Моя подписка</b>."
                                )
                                await bot.send_message(tg_id, success_text)
                            else:
                                await bot.send_message(
                                    tg_id,
                                    receipt_text + "❌ Ошибка активации подписки. Свяжитесь с поддержкой.",
                                )
                        else:
                            await bot.send_message(
                                tg_id,
                                receipt_text + "⏳ Подписка обрабатывается вручную, так как сумма не совпала с тарифом.",
                            )

                    except ValueError:
                        logger.error("Cannot parse tg_id from order_id: %s", order_id)

        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error("Webhook error: %s", e)
        return web.Response(text="OK", status=200)

# ── Фоновые задачи ────────────────────────────────────────────


async def _expiry_notification_task():
    """Уведомляет пользователей об истечении подписки за 3 дня и за 1 день.
    
    Запускается один раз в сутки (проверка каждые 12 часов).
    """
    logger.info("⏰ Expiry notification task started")
    while True:
        try:
            for days in (3, 1):
                expiring = db.get_users_with_expiring_subscriptions(days)
                for user in expiring:
                    tg_id = user.get("tg_id")
                    if not tg_id:
                        continue
                    try:
                        emoji = "⚠️" if days == 1 else "📅"
                        text = (
                            f"{emoji} <b>Ваша VPN-подписка истекает через {days} дня!</b>\n\n"
                            "Чтобы не потерять доступ к VPN, продлите подписку заранее.\n"
                        )
                        builder = InlineKeyboardBuilder()
                        builder.row(
                            types.InlineKeyboardButton(
                                text="💳 Продлить подписку",
                                callback_data="plans",
                            )
                        )
                        await bot.send_message(tg_id, text, reply_markup=builder.as_markup())
                        logger.info(
                            "Expiry notification sent: tg_id=%s days_left=%d", tg_id, days
                        )
                    except Exception as e:
                        logger.debug("Не удалось отправить уведомление для tg_id=%s: %s", tg_id, e)
        except Exception as e:
            logger.error("Ошибка в задаче уведомлений: %s", e)
        # Проверка каждые 24 часа (раз в сутки)
        await asyncio.sleep(24 * 60 * 60)


# ── Запуск ────────────────────────────────────────────────


async def main():
    logger.info("🤖 VPN Bot starting...")
    commands = [
        BotCommand(command="start", description="🏠 Главное меню")
    ]
    await bot.set_my_commands(commands)

    # Инициализируем единую HTTP-сессию для панели
    await panel.setup()

    # Запускаем фоновую задачу уведомлений об истечении
    asyncio.create_task(_expiry_notification_task())

    # Запускаем веб-сервер для Webhook
    app = web.Application()
    app.router.add_post('/tbank_webhook', tbank_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    logger.info("🌐 Webhook server started on port 8080")

    try:
        await dp.start_polling(bot)
    finally:
        await panel.teardown()
        _release_pid_lock()


if __name__ == "__main__":
    if not _acquire_pid_lock():
        print(f"ERROR: Another VPN bot instance is already running (PID file: {_PID_FILE})")
        print("Kill the existing process or remove the PID file manually.")
        sys.exit(1)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    finally:
        _release_pid_lock()
