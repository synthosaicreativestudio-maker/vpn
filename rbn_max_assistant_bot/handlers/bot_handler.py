"""Обработчик сообщений Max-бота РБН.

FSM-состояния хранятся в in-memory словаре (по user_id).
Реализует ту же логику что и Telegram-бот:
  - Приветствие (bot_started)
  - Калькулятор ликвидности (пошаговый ввод)
  - Генератор продающих описаний КН
  - Свободный вопрос ИИ-ментору
"""

import logging
import re
from services.ai_engine import ai_engine, md_to_html
from services.max_api import MaxBotAPI
from services.description_prompts import (
    DESCRIPTION_SYSTEM_PROMPT,
    CLARIFY_SYSTEM_PROMPT,
    GAB_DESCRIPTION_PROMPT,
    GAB_CLARIFY_PROMPT,
)

logger = logging.getLogger(__name__)


def clean_number(text_val: str) -> float:
    """Очищает строку от пробелов, букв и валютных знаков, приводя к float."""
    if not text_val:
        return 0.0
    # Приводим к нижнему регистру
    val_lower = text_val.lower().strip()
    
    # Обработка "млн"
    if "млн" in val_lower:
        match = re.search(r"(\d+(?:[.,]\d+)?)", val_lower)
        if match:
            try:
                return float(match.group(1).replace(",", ".")) * 1_000_000
            except ValueError:
                pass

    # Убираем все кроме цифр, точек и запятых
    cleaned = re.sub(r"[^\d.,]", "", text_val).replace(",", ".")
    
    # Если точек больше одной, возможно это разделители разрядов (например, 10.290.000)
    if cleaned.count('.') > 1:
        parts = cleaned.split('.')
        # Если последняя часть имеет длину 3, то это разделитель тысяч (10.290.000)
        if len(parts[-1]) == 3:
            cleaned = "".join(parts)
        else:
            # Иначе соединяем все кроме последней точки
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
            
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def calculate_gab_financials(price_str: str, map_str: str) -> dict:
    """Вычисляет финансовые параметры ГАБ на основе стоимости и МАП."""
    price = clean_number(price_str)
    monthly_rent = clean_number(map_str)
    
    if price > 0 and monthly_rent > 0:
        gap = monthly_rent * 12
        yield_pct = (gap / price) * 100
        payback_years = price / gap
        payback_months = payback_years * 12
        
        # Красивое текстовое представление окупаемости
        years = int(payback_years)
        months = round((payback_years - years) * 12)
        if months == 12:
            years += 1
            months = 0
            
        if years > 0:
            payback_str = f"{payback_years:.1f} лет"
            if months > 0:
                payback_str += f" (или {years} лет и {months} мес.)"
        else:
            payback_str = f"{months} мес."
            
        return {
            "price": price,
            "map": monthly_rent,
            "gap": gap,
            "yield": round(yield_pct, 1),
            "payback_str": payback_str,
            "payback_years": round(payback_years, 1),
            "payback_months": round(payback_months)
        }
    return {}


def extract_gab_inputs(full_text: str) -> tuple[str, str]:
    """Автоматически парсит цену продажи и МАП из предоставленного текста."""
    price_str = ""
    map_str = ""
    
    # Извлечение всех числовых кандидатов
    candidates = re.findall(r"(\d[\d\s.,]{3,}\d)", full_text)
    numbers = []
    for c in candidates:
        val = clean_number(c)
        if val > 0:
            numbers.append(val)
            
    # 1. Поиск цены продажи
    price_match = re.search(r"(?:стоимость|цена|продаж[аи]|стоит)\s*[:=-]?\s*(\d[\d\s.,]{5,})", full_text, re.IGNORECASE)
    if price_match:
        price_str = price_match.group(1)
    else:
        # Если ключевого слова нет, попробуем взять самое большое число >= 500 000
        large_numbers = [n for n in numbers if n >= 500000]
        if large_numbers:
            price_str = str(int(max(large_numbers)))
            
    # 2. Поиск МАП — ТОЛЬКО по явным ключевым словам, без угадывания
    map_match = re.search(
        r"(?:"
        r"мап"
        r"|арендн(?:ый|ая)\s*(?:плат|поток|ставк)"
        r"|плат[аеи]\s*(?:в\s*месяц|ежемесячн)"
        r"|месячн(?:ая|ый)\s*(?:прибыль|доход|поток|плат|аренд)"
        r"|прибыль\s*в\s*месяц"
        r"|ежемесячн\w*\s*(?:плат|доход|прибыль|аренд)"
        r")"
        r"\s*[:=-]?\s*(\d[\d\s.,]{3,})",
        full_text, re.IGNORECASE,
    )
    if map_match:
        map_str = map_match.group(1)

    return price_str, map_str


# FSM-состояния пользователей: {user_id: {"state": ..., "data": {...}}}
user_states: dict[int, dict] = {}

# Константы состояний
STATE_IDLE = None
STATE_CALC_MODE = "calc_mode"
STATE_CALC_DEAL = "calc_deal"
STATE_CALC_GAB_CHECK = "calc_gab_check"
STATE_CALC_GAB_MAP = "calc_gab_map"
STATE_CALC_COPYPASTE = "calc_copypaste"
STATE_DEAL_TYPE = "deal_type"
STATE_OBJ_TYPE = "obj_type"
STATE_AREA = "area"
STATE_PRICE = "price"
STATE_DISTRICT = "district"
STATE_MENTOR = "mentor"

# Генератор описаний
STATE_DESC_MODE = "desc_mode"
STATE_DESC_DEAL = "desc_deal"
STATE_DESC_COPYPASTE = "desc_copypaste"
STATE_DESC_CLARIFY = "desc_clarify"
STATE_DESC_OBJ_TYPE = "desc_obj_type"
STATE_DESC_AREA_FLOOR = "desc_area_floor"
STATE_DESC_ADDRESS = "desc_address"
STATE_DESC_FINISH = "desc_finish"
STATE_DESC_TECHNICAL = "desc_technical"
STATE_DESC_LOCATION = "desc_location"
STATE_DESC_PRICE = "desc_price"
STATE_DESC_EXTRAS = "desc_extras"

# ГАБ
STATE_DESC_GAB_CHECK = "desc_gab_check"
STATE_DESC_GAB_TENANT = "desc_gab_tenant"
STATE_DESC_GAB_MAP = "desc_gab_map"
STATE_DESC_GAB_CONTRACT = "desc_gab_contract"
STATE_DESC_GAB_REASON = "desc_gab_reason"


def get_main_keyboard() -> list[list[dict]]:
    """Главное меню бота — inline-кнопки."""
    return [
        [MaxBotAPI.callback_button("🧮 Оценка объекта (Ликвидность)", "calc_start")],
        [MaxBotAPI.callback_button("✍️ Описание объекта", "desc_start")],
        [MaxBotAPI.callback_button("📚 Задать вопрос ИИ-ментору", "mentor_start")],
    ]


def get_cancel_keyboard() -> list[list[dict]]:
    return [[MaxBotAPI.callback_button("❌ Отмена", "cancel")]]


def get_state(user_id: int) -> dict:
    if user_id not in user_states:
        user_states[user_id] = {"state": STATE_IDLE, "data": {}}
    return user_states[user_id]


def clear_state(user_id: int):
    user_states[user_id] = {"state": STATE_IDLE, "data": {}}


def extract_user_id(update: dict) -> int | None:
    """Извлекает user_id из любого типа обновления Max API.

    Для callback нельзя брать message.sender первым: в MAX это часто
    отправитель исходного сообщения с кнопкой, то есть сам бот.
    """
    update_type = update.get("update_type")

    if update_type == "message_callback":
        uid = update.get("callback", {}).get("user", {}).get("user_id")
        if uid:
            return uid
        uid = update.get("callback", {}).get("user_id")
        if uid:
            return uid
        uid = update.get("user", {}).get("user_id")
        if uid:
            return uid
        uid = update.get("user_id")
        if uid:
            return uid
        return None

    # message.sender.user_id — стабильный ID для текстовых сообщений
    uid = update.get("message", {}).get("sender", {}).get("user_id")
    if uid:
        return uid
    uid = update.get("user_id")
    if uid:
        return uid
    # bot_started / верхнеуровневый user
    uid = update.get("user", {}).get("user_id")
    if uid:
        return uid
    return None


# Защита от дублей (Max иногда шлёт одно обновление несколько раз)
_seen_updates: set[str] = set()
_MAX_SEEN = 1000


async def handle_update(api: MaxBotAPI, update: dict):
    """Главный роутер — определяет тип обновления и вызывает нужный обработчик."""
    update_type = update.get("update_type")

    # Дедупликация: пропускаем уже обработанные обновления
    ts = update.get("timestamp")
    uid = extract_user_id(update)
    
    # Пытаемся найти уникальный ID события (message_id или callback_id)
    entity_id = None
    if update_type == "message_callback":
        entity_id = update.get("callback", {}).get("callback_id")
    elif update_type == "message_created":
        entity_id = update.get("message", {}).get("id")

    dedup_key = f"{ts}_{update_type}_{uid}_{entity_id}"
    
    if dedup_key in _seen_updates:
        return
    _seen_updates.add(dedup_key)
    if len(_seen_updates) > _MAX_SEEN:
        # Очищаем старые записи
        to_remove = list(_seen_updates)[:_MAX_SEEN // 2]
        for k in to_remove:
            _seen_updates.discard(k)

    try:
        if update_type == "bot_started":
            await handle_bot_started(api, update)

        elif update_type == "message_callback":
            await handle_callback(api, update)

        elif update_type == "message_created":
            await handle_message(api, update)

    except Exception:
        logger.exception("Ошибка при обработке обновления: %s", update_type)


# ------------------------------------------------------------------
#  /start (bot_started)
# ------------------------------------------------------------------

async def handle_bot_started(api: MaxBotAPI, update: dict):
    user = update.get("user", {})
    user_id = user.get("user_id")
    name = user.get("name", "")
    chat_id = update.get("chat_id")

    clear_state(user_id)

    text = (
        f"👋 Приветствую, <b>{name}</b>!\n\n"
        "Я — ИИ-ассистент брокеров коммерческой недвижимости <b>РБН</b>.\n\n"
        "🔹 <b>Оценка объекта</b> — рассчитаю ликвидность, "
        "целевых арендаторов и сравню цену с рынком Тюмени.\n"
        "🔹 <b>Задать вопрос</b> — проконсультирую по маркетингу, "
        "скриптам или аналитике рынка."
    )
    target = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
    await api.send_message_with_keyboard(
        **target, text=text, buttons=get_main_keyboard()
    )


# ------------------------------------------------------------------
#  Callback-кнопки
# ------------------------------------------------------------------

async def handle_callback(api: MaxBotAPI, update: dict):
    callback = update.get("callback", {})
    callback_id = callback.get("callback_id")
    payload = callback.get("payload", "")
    user_id = extract_user_id(update)
    message = update.get("message", {})
    chat_id = message.get("recipient", {}).get("chat_id")

    target = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
    logger.info("CALLBACK user_id=%s payload=%s state=%s", user_id, payload, get_state(user_id)["state"])

    # Подтверждаем нажатие
    await api.answer_callback(callback_id)

    if payload == "cancel":
        # Если состояние уже сброшено — игнорируем устаревший callback
        if get_state(user_id)["state"] == STATE_IDLE:
            return
        clear_state(user_id)
        await api.send_message_with_keyboard(
            **target,
            text="Оценка отменена. Вы в главном меню.",
            buttons=get_main_keyboard(),
        )
        return

    if payload == "calc_start":
        get_state(user_id)["state"] = STATE_CALC_MODE
        buttons = [
            [MaxBotAPI.callback_button("📋 Вставить данные из CRM", "calc_copypaste")],
            [MaxBotAPI.callback_button("📝 Заполнить пошагово", "calc_stepbystep")],
            [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
        ]
        await api.send_message_with_keyboard(
            **target,
            text="Выберите способ оценки:\n\n"
                 "📋 <b>Вставить данные</b> — скопируйте информацию из CRM\n"
                 "📝 <b>Пошагово</b> — я задам вопросы по каждому параметру",
            buttons=buttons,
        )
        return

    # --- Аналитика: выбор режима ---
    if payload in ("calc_copypaste", "calc_stepbystep"):
        st = get_state(user_id)
        st["data"]["calc_mode"] = "copypaste" if payload == "calc_copypaste" else "stepbystep"
        st["state"] = STATE_CALC_DEAL
        buttons = [
            [
                MaxBotAPI.callback_button("Сдать в аренду", "calc_deal_rent"),
                MaxBotAPI.callback_button("Продать", "calc_deal_sell"),
            ],
            [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
        ]
        await api.send_message_with_keyboard(
            **target, text="Какой тип сделки предстоит?", buttons=buttons
        )
        return

    # --- Аналитика: тип сделки и проверка на ГАБ ---
    if payload.startswith("calc_deal_"):
        deal = "аренда" if payload == "calc_deal_rent" else "продажа"
        st = get_state(user_id)
        st["data"]["deal_type"] = deal

        if deal == "продажа":
            st["state"] = STATE_CALC_GAB_CHECK
            buttons = [
                [
                    MaxBotAPI.callback_button("✅ Да, с арендатором (ГАБ)", "calc_gab_yes"),
                    MaxBotAPI.callback_button("❌ Нет", "calc_gab_no"),
                ],
                [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
            ]
            await api.send_message_with_keyboard(
                **target,
                text="Это Готовый Арендный Бизнес (ГАБ)?",
                buttons=buttons,
            )
        else:
            st["data"]["is_gab"] = False
            await _proceed_after_calc_deal(api, target, st)
        return

    # --- Аналитика: проверка на ГАБ ---
    if payload in ("calc_gab_yes", "calc_gab_no"):
        st = get_state(user_id)
        st["data"]["is_gab"] = payload == "calc_gab_yes"
        await _proceed_after_calc_deal(api, target, st)
        return

    if payload == "mentor_start":
        get_state(user_id)["state"] = STATE_MENTOR
        await api.send_message_with_keyboard(
            **target,
            text="Напишите свой вопрос. Я отвечу, опираясь на стратегию РБН "
                 "и базу знаний рынка КН Тюмени.",
            buttons=get_cancel_keyboard(),
        )
        return



    # --- Калькулятор: тип объекта ---
    if payload.startswith("obj_"):
        obj_map = {
            "obj_psn": "Стрит-ритейл / ПСН",
            "obj_office": "Офис",
            "obj_trade": "Торговое помещение",
            "obj_warehouse": "Склад/База",
        }
        st = get_state(user_id)
        st["data"]["obj_type"] = obj_map.get(payload, payload)
        st["state"] = STATE_AREA
        await api.send_message_with_keyboard(
            **target,
            text="Укажите площадь (в м²), например: <b>45</b>",
            buttons=get_cancel_keyboard(),
        )
        return

    # --- Калькулятор: район ---
    if payload.startswith("dist_"):
        dist_map = {
            "dist_center": "Центр",
            "dist_kpd": "КПД / 50 лет ВЛКСМ",
            "dist_zarech": "Заречный",
            "dist_east": "Восточный / Широтная",
        }
        st = get_state(user_id)
        st["data"]["district"] = dist_map.get(payload, payload)

        # Если ГАБ — спросить МАП перед расчётом
        if st["data"].get("is_gab"):
            st["state"] = STATE_CALC_GAB_MAP
            await api.send_message_with_keyboard(
                **target,
                text="💰 Укажите ежемесячную арендную плату (МАП):\n"
                     "<i>Например: 120000</i>",
                buttons=get_cancel_keyboard(),
            )
            return

        st["state"] = STATE_IDLE

        await api.send_message(**target, text="⏳ Анализирую объект по базе РБН...")

        result = await ai_engine.analyze_property(
            deal_type=st["data"]["deal_type"],
            obj_type=st["data"]["obj_type"],
            area=st["data"]["area"],
            price=st["data"]["price"],
            district=st["data"]["district"],
            user_id=user_id,
            is_gab=False,
        )
        clear_state(user_id)
        await _send_analysis_with_chart(api, target, result)
        return

    # --- Генератор описаний: точка входа ---
    if payload == "desc_start":
        get_state(user_id)["state"] = STATE_DESC_MODE
        buttons = [
            [MaxBotAPI.callback_button("📋 Вставить данные из CRM", "desc_copypaste")],
            [MaxBotAPI.callback_button("📝 Заполнить пошагово", "desc_stepbystep")],
            [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
        ]
        await api.send_message_with_keyboard(
            **target,
            text="Выберите способ создания описания:\n\n"
                 "📋 <b>Вставить данные</b> — скопируйте информацию из CRM\n"
                 "📝 <b>Пошагово</b> — я задам вопросы по каждому параметру",
            buttons=buttons,
        )
        return

    # --- Генератор описаний: выбор режима ---
    if payload in ("desc_copypaste", "desc_stepbystep"):
        st = get_state(user_id)
        st["data"]["desc_mode"] = "copypaste" if payload == "desc_copypaste" else "stepbystep"
        st["state"] = STATE_DESC_DEAL
        buttons = [
            [
                MaxBotAPI.callback_button("🏷 Сдать в аренду", "desc_deal_rent"),
                MaxBotAPI.callback_button("💰 Продать", "desc_deal_sell"),
            ],
            [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
        ]
        await api.send_message_with_keyboard(
            **target, text="Выберите тип сделки:", buttons=buttons
        )
        return

    # --- Генератор описаний: тип сделки ---
    if payload.startswith("desc_deal_"):
        deal = "аренда" if payload == "desc_deal_rent" else "продажа"
        st = get_state(user_id)
        st["data"]["desc_deal_type"] = deal

        if deal == "продажа":
            st["state"] = STATE_DESC_GAB_CHECK
            buttons = [
                [
                    MaxBotAPI.callback_button("✅ Да, есть арендатор (ГАБ)", "gab_yes"),
                    MaxBotAPI.callback_button("❌ Нет", "gab_no"),
                ],
                [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
            ]
            await api.send_message_with_keyboard(
                **target,
                text="Есть ли действующий арендатор?\n\n"
                     "Если <b>да</b> — описание для инвестора (ГАБ).\n"
                     "Если <b>нет</b> — обычное описание продажи.",
                buttons=buttons,
            )
        else:
            st["data"]["is_gab"] = False
            await _proceed_after_deal_max(api, target, st)
        return

    # --- ГАБ: да/нет ---
    if payload in ("gab_yes", "gab_no"):
        st = get_state(user_id)
        st["data"]["is_gab"] = payload == "gab_yes"
        await _proceed_after_deal_max(api, target, st)
        return

    # --- Генератор описаний: тип объекта (пошагово) ---
    if payload.startswith("dobj_"):
        dobj_map = {
            "dobj_office": "Офис",
            "dobj_trade": "Торговое помещение",
            "dobj_psn": "Стрит-ритейл / ПСН",
            "dobj_warehouse": "Склад",
            "dobj_food": "Общепит",
            "dobj_free": "Свободного назначения",
        }
        st = get_state(user_id)
        st["data"]["desc_obj_type"] = dobj_map.get(payload, payload)
        st["state"] = STATE_DESC_AREA_FLOOR
        await api.send_message_with_keyboard(
            **target,
            text="Площадь и этаж:\n<i>Например: 80 м², 1 этаж из 5</i>",
            buttons=get_cancel_keyboard(),
        )
        return

    # --- Меню ---
    if payload == "main_menu":
        clear_state(user_id)
        await api.send_message_with_keyboard(
            **target, text="Вы в главном меню.", buttons=get_main_keyboard()
        )
        return


# ------------------------------------------------------------------
#  Текстовые сообщения (ввод данных калькулятора + свободный вопрос)
# ------------------------------------------------------------------


async def _send_analysis_with_chart(api: MaxBotAPI, target: dict, result_tuple):
    """Отправляет текст отчёта + scatter-plot график."""
    import os
    text, chart_path = result_tuple
    await _safe_send(api, target, text)
    if chart_path and os.path.exists(chart_path):
        try:
            token = await api.upload_image(chart_path)
            if token:
                await api.send_image(**target, token=token)
            os.unlink(chart_path)
        except Exception:
            logger.exception("Ошибка отправки графика")


async def handle_message(api: MaxBotAPI, update: dict):
    message = update.get("message", {})
    body = message.get("body", {})
    text = body.get("text", "").strip()
    user_id = extract_user_id(update)
    chat_id = message.get("recipient", {}).get("chat_id")

    if not text or not user_id:
        return

    target = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
    st = get_state(user_id)
    state = st["state"]
    logger.info("MESSAGE user_id=%s state=%s text=%s", user_id, state, text[:50])

    # --- Калькулятор ГАБ: ввод МАП ---
    if state == STATE_CALC_GAB_MAP:
        import re as _re
        cleaned = _re.sub(r"[^\d]", "", text)
        monthly_rent = float(cleaned) if cleaned else 0
        if monthly_rent <= 0:
            await api.send_message_with_keyboard(
                **target,
                text="❌ Не удалось распознать сумму. Укажите МАП цифрами, например: <b>120000</b>",
                buttons=get_cancel_keyboard(),
            )
            return
        st["data"]["monthly_rent"] = monthly_rent
        st["state"] = STATE_IDLE

        await api.send_message(**target, text="⏳ Анализирую объект по базе РБН...")
        result = await ai_engine.analyze_property(
            deal_type=st["data"]["deal_type"],
            obj_type=st["data"]["obj_type"],
            area=st["data"]["area"],
            price=st["data"]["price"],
            district=st["data"]["district"],
            user_id=user_id,
            is_gab=True,
            monthly_rent=monthly_rent,
        )
        clear_state(user_id)
        await _send_analysis_with_chart(api, target, result)
        return

    # --- Калькулятор: копипаст ---
    if state == STATE_CALC_COPYPASTE:
        await api.send_message(**target, text="⏳ Извлекаю параметры из текста...")
        params = await ai_engine.extract_calc_params(text)
        
        if not params or not params.get("area") or not params.get("price"):
            await api.send_message_with_keyboard(
                **target, 
                text="❌ Не удалось распознать площадь и цену. Попробуйте ввести данные пошагово.",
                buttons=get_cancel_keyboard()
            )
            return
            
        st["data"]["area"] = str(params["area"])
        st["data"]["price"] = str(params["price"])
        st["data"]["district"] = params.get("district", "Центр")
        st["data"]["obj_type"] = params.get("obj_type", "Свободного назначения")
        
        is_gab = st["data"].get("is_gab", False)
        monthly_rent = 0
        
        # Для ГАБ из CRM: спрашиваем МАП отдельно
        if is_gab:
            st["state"] = STATE_CALC_GAB_MAP
            await api.send_message_with_keyboard(
                **target,
                text="💰 Укажите ежемесячную арендную плату (МАП):\n"
                     "<i>Например: 120000</i>",
                buttons=get_cancel_keyboard(),
            )
            return
        
        st["state"] = STATE_IDLE
        await api.send_message(**target, text="⏳ Анализирую объект по базе РБН...")
        result = await ai_engine.analyze_property(
            deal_type=st["data"].get("deal_type", "аренда"),
            obj_type=st["data"]["obj_type"],
            area=st["data"]["area"],
            price=st["data"]["price"],
            district=st["data"]["district"],
            user_id=user_id,
            is_gab=False,
        )
        clear_state(user_id)
        await _send_analysis_with_chart(api, target, result)
        return

    # --- Калькулятор: площадь ---
    if state == STATE_AREA:
        st["data"]["area"] = text
        st["state"] = STATE_PRICE
        await api.send_message_with_keyboard(
            **target,
            text="Укажите желаемую цену (только цифры, в рублях):",
            buttons=get_cancel_keyboard(),
        )
        return

    # --- Калькулятор: цена ---
    if state == STATE_PRICE:
        st["data"]["price"] = text
        st["state"] = STATE_DISTRICT
        buttons = [
            [
                MaxBotAPI.callback_button("Центр", "dist_center"),
                MaxBotAPI.callback_button("КПД / 50 лет ВЛКСМ", "dist_kpd"),
            ],
            [
                MaxBotAPI.callback_button("Заречный", "dist_zarech"),
                MaxBotAPI.callback_button("Восточный / Широтная", "dist_east"),
            ],
            [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
        ]
        await api.send_message_with_keyboard(
            **target,
            text="В каком районе находится объект?",
            buttons=buttons,
        )
        return

    # --- Генератор описаний: копипаст ---
    if state == STATE_DESC_COPYPASTE:
        st["data"]["crm_data"] = text
        deal = st["data"].get("desc_deal_type", "аренда")
        await api.send_message(**target, text="⏳ Анализирую данные...")

        user_msg = f"Тип сделки: {deal}\n\nДанные объекта из CRM:\n{text}"
        clarify_prompt = GAB_CLARIFY_PROMPT if st["data"].get("is_gab") else CLARIFY_SYSTEM_PROMPT
        result = await ai_engine.generate_with_prompt(clarify_prompt, user_msg, user_id=user_id)

        if "ГОТОВО" in result.strip().upper():
            await _generate_description(api, target, user_id)
        else:
            st["data"]["clarify_questions"] = result
            st["state"] = STATE_DESC_CLARIFY
            await api.send_message_with_keyboard(
                **target, text=result, buttons=get_cancel_keyboard()
            )
        return

    # --- Генератор описаний: уточнения ---
    if state == STATE_DESC_CLARIFY:
        st["data"]["clarify_answers"] = text
        await _generate_description(api, target, user_id)
        return

    # --- Генератор описаний: пошагово ---
    if state == STATE_DESC_AREA_FLOOR:
        st["data"]["desc_area_floor"] = text
        st["state"] = STATE_DESC_ADDRESS
        await api.send_message_with_keyboard(
            **target, text="Адрес объекта или район:", buttons=get_cancel_keyboard()
        )
        return

    if state == STATE_DESC_ADDRESS:
        st["data"]["desc_address"] = text
        st["state"] = STATE_DESC_FINISH
        await api.send_message_with_keyboard(
            **target,
            text="Отделка и тип входа:\n"
                 "<i>Например: чистовая, отдельный вход, потолки 3.5 м</i>\n\n"
                 "Напишите или отправьте <b>-</b> чтобы пропустить.",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_FINISH:
        st["data"]["desc_finish"] = "" if text.strip() == "-" else text
        st["state"] = STATE_DESC_TECHNICAL
        await api.send_message_with_keyboard(
            **target,
            text="Технические параметры:\n"
                 "<i>Мощность (кВт), вентиляция, мокрые точки</i>\n\n"
                 "Напишите или отправьте <b>-</b> чтобы пропустить.",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_TECHNICAL:
        st["data"]["desc_technical"] = "" if text.strip() == "-" else text
        st["state"] = STATE_DESC_LOCATION
        await api.send_message_with_keyboard(
            **target,
            text="Локация и парковка:\n"
                 "<i>Трафик, соседние объекты, парковка</i>\n\n"
                 "Напишите или отправьте <b>-</b> чтобы пропустить.",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_LOCATION:
        st["data"]["desc_location"] = "" if text.strip() == "-" else text
        st["state"] = STATE_DESC_PRICE
        await api.send_message_with_keyboard(
            **target,
            text="Цена и условия:\n<i>Стоимость, КУ, залог, каникулы</i>",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_PRICE:
        st["data"]["desc_price"] = text
        st["state"] = STATE_DESC_EXTRAS
        await api.send_message_with_keyboard(
            **target,
            text="Дополнительные комментарии (необязательно):\n"
                 "Напишите или отправьте <b>-</b> чтобы пропустить.",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_EXTRAS:
        st["data"]["desc_extras"] = "" if text.strip() == "-" else text
        if st["data"].get("is_gab"):
            st["state"] = STATE_DESC_GAB_TENANT
            await api.send_message_with_keyboard(
                **target,
                text="🏢 Название арендатора:\n"
                     "<i>Например: Магнит, федеральная аптека</i>",
                buttons=get_cancel_keyboard(),
            )
        else:
            await _generate_description(api, target, user_id)
        return

    # --- ГАБ-шаги ---
    if state == STATE_DESC_GAB_TENANT:
        st["data"]["gab_tenant"] = text
        st["state"] = STATE_DESC_GAB_MAP
        await api.send_message_with_keyboard(
            **target,
            text="💰 Ежемесячная арендная плата (МАП):\n"
                 "<i>Например: 150 000 руб/мес</i>",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_GAB_MAP:
        st["data"]["gab_map"] = text
        # В copypaste-режиме остальные данные уже есть — сразу генерируем
        if st["data"].get("desc_mode") == "copypaste":
            await _generate_description(api, target, user_id)
            return
        st["state"] = STATE_DESC_GAB_CONTRACT
        await api.send_message_with_keyboard(
            **target,
            text="📅 Срок договора и индексация:\n"
                 "<i>Например: до 2029, индексация 5% в год</i>",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_GAB_CONTRACT:
        st["data"]["gab_contract"] = text
        st["state"] = STATE_DESC_GAB_REASON
        await api.send_message_with_keyboard(
            **target,
            text="❓ Причина продажи:\n"
                 "<i>Напишите или отправьте <b>-</b> чтобы пропустить</i>",
            buttons=get_cancel_keyboard(),
        )
        return

    if state == STATE_DESC_GAB_REASON:
        st["data"]["gab_reason"] = "" if text.strip() == "-" else text
        await _generate_description(api, target, user_id)
        return

    # --- Ментор: свободный вопрос ---
    if state == STATE_MENTOR:
        clear_state(user_id)
        await api.send_message(**target, text="⏳ Анализирую ваш вопрос...")
        result = await ai_engine.get_mentor_answer(text, user_id=user_id)
        await _safe_send(api, target, result)
        return

    # --- Без состояния: любой текст → ментор / аналитика ---
    if text.lower() in ("/start", "start", "старт", "меню", "menu", "начать"):
        clear_state(user_id)
        await api.send_message_with_keyboard(
            **target, text="Вы в главном меню.", buttons=get_main_keyboard()
        )
        return

    # Это сохраняет быстрый рабочий сценарий: брокер может просто вставить
    # данные из CRM одним сообщением и получить анализ без прохождения опросника.
    logger.info("SENDING typing indicator to user_id=%s", user_id)
    try:
        typing_res = await api.send_message(**target, text="⏳ Анализирую ваш вопрос...")
        logger.info("Typing indicator sent, result: %s", str(typing_res)[:200])
    except Exception:
        logger.exception("Failed to send typing indicator")
    result = await ai_engine.get_mentor_answer(text, user_id=user_id)
    logger.info("AI response generated, length=%d, sending to user_id=%s", len(result), user_id)
    await _safe_send(api, target, result)


# ------------------------------------------------------------------
#  Переход после выбора сделки
# ------------------------------------------------------------------

async def _proceed_after_calc_deal(api: MaxBotAPI, target: dict, st: dict):
    if st["data"]["calc_mode"] == "copypaste":
        st["state"] = STATE_CALC_COPYPASTE
        await api.send_message_with_keyboard(
            **target,
            text="Вставьте текст объявления или информацию из CRM:",
            buttons=get_cancel_keyboard(),
        )
    else:
        st["state"] = STATE_OBJ_TYPE
        buttons = [
            [
                MaxBotAPI.callback_button("Стрит-ритейл / ПСН", "obj_psn"),
                MaxBotAPI.callback_button("Офис", "obj_office"),
            ],
            [
                MaxBotAPI.callback_button("Торговое помещение", "obj_trade"),
                MaxBotAPI.callback_button("Склад/База", "obj_warehouse"),
            ],
            [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
        ]
        await api.send_message_with_keyboard(
            **target, text="Выберите тип объекта:", buttons=buttons
        )

async def _proceed_after_deal_max(api: MaxBotAPI, target: dict, st: dict):
    """Переход к копипасту или пошаговому после определения сделки + ГАБ."""
    if st["data"].get("desc_mode") == "copypaste":
        st["state"] = STATE_DESC_COPYPASTE
        await api.send_message_with_keyboard(
            **target,
            text="📋 Скопируйте данные об объекте из CRM и отправьте "
                 "мне одним сообщением.\n\n"
                 "Я проанализирую и, если чего-то не хватит, задам вопросы.",
            buttons=get_cancel_keyboard(),
        )
    else:
        st["state"] = STATE_DESC_OBJ_TYPE
        buttons = [
            [
                MaxBotAPI.callback_button("Офис", "dobj_office"),
                MaxBotAPI.callback_button("Торговое помещение", "dobj_trade"),
            ],
            [
                MaxBotAPI.callback_button("Стрит-ритейл / ПСН", "dobj_psn"),
                MaxBotAPI.callback_button("Склад", "dobj_warehouse"),
            ],
            [
                MaxBotAPI.callback_button("Общепит", "dobj_food"),
                MaxBotAPI.callback_button("Свободного назначения", "dobj_free"),
            ],
            [MaxBotAPI.callback_button("❌ Отмена", "cancel")],
        ]
        await api.send_message_with_keyboard(
            **target, text="Тип объекта:", buttons=buttons
        )


# ------------------------------------------------------------------
#  Генерация описания
# ------------------------------------------------------------------

async def _generate_description(api: MaxBotAPI, target: dict, user_id: int):
    """Собирает данные из FSM и генерирует описание через LLM."""
    st = get_state(user_id)
    data = st["data"]
    deal = data.get("desc_deal_type", "аренда")
    is_gab = data.get("is_gab", False)

    if data.get("desc_mode") == "copypaste":
        property_info = f"Данные из CRM:\n{data.get('crm_data', '')}"
        if data.get("clarify_answers"):
            property_info += f"\n\nДополнительные ответы:\n{data['clarify_answers']}"
    else:
        parts = [
            f"Тип объекта: {data.get('desc_obj_type', '')}",
            f"Площадь и этаж: {data.get('desc_area_floor', '')}",
            f"Адрес: {data.get('desc_address', '')}",
        ]
        if data.get("desc_finish"):
            parts.append(f"Отделка и вход: {data['desc_finish']}")
        if data.get("desc_technical"):
            parts.append(f"Техника: {data['desc_technical']}")
        if data.get("desc_location"):
            parts.append(f"Локация: {data['desc_location']}")
        parts.append(f"Цена и условия: {data.get('desc_price', '')}")
        if data.get("desc_extras"):
            parts.append(f"Дополнительно: {data['desc_extras']}")
        property_info = "\n".join(parts)

    # ГАБ-данные
    if data.get("desc_mode") != "copypaste" and is_gab:
        gab_parts = [
            f"Арендатор: {data.get('gab_tenant', '')}",
            f"МАП (аренда/мес): {data.get('gab_map', '')}",
            f"Срок договора и индексация: {data.get('gab_contract', '')}",
        ]
        if data.get("gab_reason"):
            gab_parts.append(f"Причина продажи: {data['gab_reason']}")
        property_info += "\n" + "\n".join(gab_parts)

    # Вычисляем финансовые показатели для ГАБ
    fin_data = {}
    if is_gab:
        price_str = ""
        map_str = ""

        if data.get("desc_mode") == "copypaste":
            # Цену извлекаем из текста, МАП — ВСЕГДА спрашиваем у пользователя
            price_str, _ = extract_gab_inputs(property_info)

            # Если МАП ещё не введён пользователем — запрашиваем
            if not data.get("gab_map"):
                st["state"] = STATE_DESC_GAB_MAP
                await api.send_message_with_keyboard(
                    **target,
                    text="💰 Укажите ежемесячную арендную плату (МАП):\n"
                         "<i>Например: 150000</i>",
                    buttons=get_cancel_keyboard(),
                )
                return

            map_str = data["gab_map"]
        else:
            # Берем из пошагового ввода
            price_str = data.get("desc_price", "")
            map_str = data.get("gab_map", "")

        fin_data = calculate_gab_financials(price_str, map_str)

    sys_prompt = GAB_DESCRIPTION_PROMPT if is_gab else DESCRIPTION_SYSTEM_PROMPT

    # Формируем user_msg с жесткими финансовыми показателями для ГАБ
    if is_gab and fin_data:
        financials_block = (
            "\n=== РАССЧИТАННЫЕ ФИНАНСОВЫЕ ПОКАЗАТЕЛИ (ИСПОЛЬЗУЙ СТРОГО ИХ!):\n"
            f"• Стоимость объекта: {int(fin_data['price']):,} ₽\n"
            f"• МАП (месячный арендный поток): {int(fin_data['map']):,} ₽\n"
            f"• ГАП (годовой арендный поток): {int(fin_data['gap']):,} ₽\n"
            f"• Чистая доходность: {fin_data['yield']}% годовых\n"
            f"• Срок окупаемости: {fin_data['payback_str']}\n"
            "========================================================\n"
        )
        
        user_msg = (
            f"Тип сделки: {deal}\n\n{property_info}\n\n"
            f"{financials_block}\n"
            f"Создай продающий заголовок по формуле:\n"
            f"📌 ГАБ: [тип/арендатор], [площадь] м², доходность {fin_data['yield']}%\n"
            f"И напиши полное описание из 7 блоков. Помни: в блоке ФИНАНСОВЫЕ ПОКАЗАТЕЛИ "
            f"ты должен использовать СТРОГО указанные выше рассчитанные показатели (Стоимость, МАП, ГАП, "
            f"Доходность и Окупаемость), не пытайся пересчитывать или округлять их самостоятельно!"
        )
    else:
        user_msg = (
            f"Тип сделки: {deal}\n\n{property_info}\n\n"
            f"Создай продающий заголовок и полное описание из 7 блоков."
        )

    await api.send_message(**target, text="⏳ Генерирую продающее описание...")

    raw = await ai_engine.generate_with_prompt(sys_prompt, user_msg, user_id=user_id)
    raw = re.sub(
        r"(?im)^\s*(?:[-*•]\s*)?(?:\d+[.)]\s*)?(?:\*\*)?"
        r"призыв\s+к\s+действию(?:\*\*)?\s*:?\s*$\n?",
        "",
        raw,
    )

    # Подпись компании
    client_type = "арендатора" if deal == "аренда" else "покупателя"
    raw += (
        "\n\nРегион Бизнес Недвижимость\n"
        "Коммерческая Недвижимость\n"
        f"Без комиссии для {client_type}"
    )

    html = md_to_html(raw)
    clear_state(user_id)
    await _safe_send(api, target, html)


# ------------------------------------------------------------------
#  Утилита безопасной отправки
# ------------------------------------------------------------------

async def _safe_send(api: MaxBotAPI, target: dict, text: str):
    """Отправляет ответ с HTML. При ошибке — без форматирования."""
    logger.info("_safe_send called, text_len=%d, target=%s", len(text), target)
    try:
        res = await api.send_message_with_keyboard(
            **target, text=text, buttons=get_main_keyboard()
        )
        logger.info("_safe_send OK: %s", str(res)[:200])
    except Exception:
        logger.warning("HTML-разметка невалидна, отправляю без форматирования")
        try:
            res = await api.send_message_with_keyboard(
                **target, text=text, format="", buttons=get_main_keyboard()
            )
            logger.info("_safe_send (plain) OK: %s", str(res)[:200])
        except Exception:
            logger.exception("Ошибка отправки сообщения в Max")
            await api.send_message_with_keyboard(
                **target,
                text="⚠️ Не удалось отобразить ответ. Попробуйте ещё раз.",
                format="",
                buttons=get_main_keyboard(),
            )
