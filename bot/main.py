import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.config import BOT_TOKEN, PAYMENT_TOKEN
from bot.utils.marzban_api import MarzbanAPI
from bot.data.db_manager import DBManager
import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота, диспетчера и менеджеров
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
marzban = MarzbanAPI()
db = DBManager()

# Тарифы
TARIFFS = {
    "trial": {"name": "🎁 Тест (3 дня)", "days": 3, "price": 0},
    "1_month": {"name": "📅 1 месяц", "days": 30, "price": 199},
    "3_months": {"name": "📅 3 месяца", "days": 90, "price": 549},
    "6_months": {"name": "📅 6 месяцев", "days": 180, "price": 999},
    "12_months": {"name": "📅 12 месяцев", "days": 365, "price": 1499},
}

def get_tariffs_keyboard():
    builder = InlineKeyboardBuilder()
    for key, data in TARIFFS.items():
        builder.row(types.InlineKeyboardButton(
            text=f"{data['name']} — {data['price']}₽",
            callback_data=f"buy_{key}"
        ))
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    db.add_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "<b>👋 Привет! Я твой VPN-бот.</b>\n\n"
        "Здесь ты можешь купить подписку и получить доступ к быстрому интернету без ограничений.\n\n"
        "👇 <b>Выберите подходящий тариф:</b>",
        reply_markup=get_tariffs_keyboard()
    )

@dp.callback_query(F.data == "buy_trial")
async def process_trial(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    # Проверка, был ли уже использован тест
    if user_data and user_data[2]: # индекс 2 - subscription_expires
        await callback.answer("❌ Вы уже использовали тестовый период или имеете подписку.", show_alert=True)
        return

    await callback.message.edit_text("⏳ <b>Создаю ваш тестовый доступ...</b>")
    
    # Создание юзера в Marzban
    username = f"user_{user_id}"
    expire_timestamp = int((datetime.datetime.now() + datetime.timedelta(days=3)).timestamp())
    
    try:
        res = await marzban.create_user(username=username, expire=expire_timestamp)
        
        if res:
            sub_url = res.get("subscription_url")
            db.update_subscription(user_id, datetime.datetime.fromtimestamp(expire_timestamp).isoformat(), sub_url)
            
            links = res.get("links", [])
            vless_link = links[0] if links else ""
            
            await callback.message.edit_text(
                "✅ <b>Тестовый доступ на 3 дня готов!</b>\n\n"
                "1️⃣ <b>Скачайте приложение Happ:</b>\n"
                "• <a href='https://apps.apple.com/app/id6444665403'>Скачать для iPhone</a>\n"
                "• <a href='https://play.google.com/store/apps/details?id=com.happ.app'>Скачать для Android</a>\n\n"
                "2️⃣ <b>Настройте подключение:</b>\n"
                "• Скопируйте одну из ссылок ниже (нажмите на неё).\n"
                "• В приложении нажмите <b>+</b> или <b>Добавить конфигурацию</b>.\n"
                "• Выберите <b>Import from Clipboard</b> (Импорт).\n\n"
                "<i>Если первая ссылка не принимается, используйте вторую (VLESS).</i>"
            )
            
            # Ссылка на подписку
            await callback.message.answer(f"🔗 <b>Ссылка-подписка (авто-обновление):</b>\n<code>{sub_url}</code>")
            
            # Прямая ссылка VLESS как альтернатива
            if vless_link:
                await callback.message.answer(f"⚙️ <b>Прямая VLESS-ссылка:</b>\n<code>{vless_link}</code>")
        else:
            await callback.message.edit_text("❌ <b>Ошибка при создании доступа.</b> Попробуйте позже.")
    except Exception as e:
        logger.error(f"Error in process_trial: {e}")
        await callback.message.edit_text("❌ <b>Произошла ошибка.</b> Пожалуйста, попробуйте еще раз или напишите поддержке.")

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    tariff_key = callback.data.split("_", 1)[1]
    if tariff_key == "trial": return
    
    tariff = TARIFFS.get(tariff_key)
    
    if not PAYMENT_TOKEN:
        await callback.answer("❌ Оплата временно недоступна (не настроен токен).", show_alert=True)
        return

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"Подписка: {tariff['name']}",
        description=f"Доступ к VPN на {tariff['days']} дней",
        payload=tariff_key,
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[
            types.LabeledPrice(label=tariff['name'], amount=tariff['price'] * 100) # Цена в копейках
        ],
        start_parameter="vpn_subscription",
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    user_id = message.from_user.id
    tariff_key = message.successful_payment.invoice_payload
    tariff = TARIFFS.get(tariff_key)
    
    await message.answer(f"✅ <b>Оплата прошла успешно!</b> Оформляю подписку: {tariff['name']}...")
    
    # Логика продления/создания в Marzban
    username = f"user_{user_id}"
    days = tariff['days']
    
    try:
        # Получаем текущее состояние (чтобы продлить, если уже есть)
        current_user = await marzban.get_user(username)
        if current_user and current_user.get("expire"):
            current_expire = current_user.get("expire")
            new_expire = int(current_expire + (days * 24 * 60 * 60))
        else:
            new_expire = int((datetime.datetime.now() + datetime.timedelta(days=days)).timestamp())
        
        res = await marzban.create_user(username=username, expire=new_expire)
        
        if res:
            sub_url = res.get("subscription_url")
            db.update_subscription(user_id, datetime.datetime.fromtimestamp(new_expire).isoformat(), sub_url)
            
            links = res.get("links", [])
            vless_link = links[0] if links else ""

            await message.answer(
                f"✨ <b>Подписка успешно оформлена!</b>\n"
                f"📅 <b>Действует до:</b> {datetime.datetime.fromtimestamp(new_expire).strftime('%d.%m.%Y')}\n\n"
                f"🚀 <b>Инструкция по установке:</b>\n"
                f"• <a href='https://apps.apple.com/app/id6444665403'>Скачать Happ для iPhone</a>\n"
                f"• <a href='https://play.google.com/store/apps/details?id=com.happ.app'>Скачать Happ для Android</a>\n\n"
                f"👇 <b>Ваши ключи доступа (нажмите для копирования):</b>"
            )
            
            await message.answer(f"🔗 <b>Ссылка-подписка (авто-обновление):</b>\n<code>{sub_url}</code>")
            
            if vless_link:
                await message.answer(f"⚙️ <b>Прямая VLESS-ссылка:</b>\n<code>{vless_link}</code>")
        else:
            await message.answer("❌ <b>Произошла ошибка при обновлении подписки.</b> Пожалуйста, напишите поддержке.")
    except Exception as e:
        logger.error(f"Error in process_successful_payment: {e}")
        await message.answer("❌ <b>Произошла критическая ошибка.</b> Пожалуйста, напишите поддержке.")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    token = await marzban.get_token()
    user_data = db.get_user(message.from_user.id)
    
    status_text = "<b>✅ Связь с сервером Marzban:</b> OK\n" if token else "<b>❌ Связь с сервером Marzban:</b> Error\n"
    if user_data and user_data[2]:
        status_text += f"📅 <b>Подписка до:</b> {user_data[2]}"
    else:
        status_text += "🔴 <b>Подписка не активна</b>"
        
    await message.answer(status_text)

async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
