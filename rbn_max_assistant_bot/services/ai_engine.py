import os
import re
import logging
from services.market_analyzer import market_analyzer
from services.rag_engine import rag_engine
from services.web_search import needs_web_search, web_search
from services.memory_service import memory_service

# Системный промпт (База знаний РБН)
RBN_SYSTEM_PROMPT = """Ты — аналитик компании РБН (Регион Бизнес Недвижимость).
Делаешь понятный анализ коммерческой недвижимости Тюмени для брокеров.

ПРАВИЛА:
- Пиши просто, без сложных терминов. Как будто объясняешь коллеге-брокеру.
- Используй цифры из предоставленных данных — не выдумывай.
- Если данных не хватает — укажи что нужно уточнить, но не пиши «данные не найдены» или «блок не найден».

ЗАПРЕЩЁННЫЕ СЛОВА (никогда не используй в ответе):
benchmark, CMA, market pressure, Gross Yield, cap rate, Months of Supply,
перцентиль, детерминированный, flow, exposure, liquidity index, RAG, FAISS

ЗАМЕНЫ (используй вместо запрещённых):
- «перцентиль 72%» → «дороже 72% предложений на рынке»
- «market pressure» → «активность спроса»
- «Months of Supply» → «скорость поглощения рынка»
- «Gross Yield» → «доходность от аренды»
- «cap rate» → «доходность»
- «exposure» → «срок продажи/сдачи»

СТРУКТУРА ОТВЕТА:

📊 Анализ объекта

1️⃣ Насколько это востребовано?
Объясни грейд спроса простым языком. Площадь в ядре спроса или нет. Сколько сделок в этом сегменте.

2️⃣ Цена — в рынке или нет?
Сравни с аналогами и средней ценой. Дай чёткий вывод: дорого / в рынке / ниже рынка.

3️⃣ Кто купит/арендует?
Конкретные типы бизнеса, которые реально ищут такие площади в этом районе.

4️⃣ Сколько времени займёт сделка?
Прогноз срока на основе данных. Состояние рынка (спрос vs предложение).

5️⃣ Что можно улучшить?
Практические советы: цена, подача объявления, подготовка помещения.

Пиши кратко, по делу, с конкретными цифрами."""


def md_to_html(text: str) -> str:
    """Конвертирует Markdown-разметку LLM в Telegram-совместимый HTML.

    Обрабатывает: **bold**, *italic*, `code`, ```code blocks```,
    заголовки (###), списки (-/•/числовые).
    """
    if not text:
        return text

    # Экранируем HTML-спецсимволы, которые уже есть в тексте
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    # Code blocks (```) — обрабатываем ДО inline
    text = re.sub(
        r"```(?:\w*)\n?(.*?)```",
        r"<pre>\1</pre>",
        text,
        flags=re.DOTALL,
    )

    # Inline code (`)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    # Bold (**text** или __text__)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    # Italic (*text* или _text_) — НЕ захватываем уже обработанный bold
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"<i>\1</i>", text)

    # Заголовки (### → bold)
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    return text


from groq import AsyncGroq  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

class AIEngine:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_key:
            self.gemini_client = genai.Client(api_key=self.gemini_key)
            self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        else:
            self.gemini_client = None

    async def _generate_text(self, system_prompt: str, user_message: str, user_id: int = None) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        if user_id:
            history = memory_service.get_history(user_id)
            # Оптимизируем объем: берем последние 6 сообщений вместо 10
            for msg in history[-6:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        model_to_use = self.model
        if model_to_use == "llama-3.1-8b-instant":
            model_to_use = "llama-3.3-70b-versatile"

        try:
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as groq_err:
            logging.warning("Ошибка Groq (%s), пробуем резервный Gemini...", groq_err)
            
            if self.gemini_client:
                try:
                    gemini_contents = []
                    for msg in messages:
                        if msg["role"] == "system":
                            continue
                        role = "user" if msg["role"] == "user" else "model"
                        gemini_contents.append(
                            types.Content(
                                role=role,
                                parts=[types.Part.from_text(text=msg["content"])]
                            )
                        )
                    
                    config = types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.7,
                        max_output_tokens=4096,
                    )
                    
                    async with self.gemini_client.aio as aclient:
                        response = await aclient.models.generate_content(
                            model=self.gemini_model,
                            contents=gemini_contents,
                            config=config
                        )
                        if response.text:
                            logging.info("Успешный fallback ответ от Gemini")
                            return response.text
                except Exception as gemini_err:
                    logging.exception("Ошибка резервного ИИ-сервиса (Gemini)")
                    return f"❌ Ошибка ИИ-сервиса: Groq ({groq_err!s}) | Gemini ({gemini_err!s})"
            
            return f"❌ Ошибка ИИ-сервиса (Groq): {groq_err!s}"

    async def generate_with_prompt(self, system_prompt: str, user_message: str, user_id: int = None) -> str:
        """Универсальный вызов LLM. Если передан user_id, учитывает историю диалога."""
        try:
            return await self._generate_text(system_prompt, user_message, user_id)
        except Exception as e:
            logging.exception("Ошибка ИИ-сервиса (Groq/Gemini)")
            return f"❌ Ошибка ИИ-сервиса: {e!s}"

    async def extract_calc_params(self, text: str) -> dict:
        """Извлекает параметры объекта из сырого текста для калькулятора.
        
        Сначала пробует ИИ, при ошибке — fallback на регулярные выражения.
        """
        # --- Fallback: regex-парсер (работает всегда) ---
        result = self._regex_extract_params(text)
        
        # Если regex нашёл площадь и цену — используем его (быстро и надёжно)
        if result.get("area") and result.get("price"):
            return result
        
        # --- ИИ-парсер (если regex не справился) ---
        prompt = (
            "Извлеки из текста параметры коммерческой недвижимости и верни СТРОГО в формате JSON:\n"
            '{"area": 0.0, "price": 0.0, "district": "", "obj_type": ""}\n\n'
            "Правила:\n"
            "1. area - площадь (число).\n"
            "2. price - цена в рублях (число).\n"
            "3. district - район Тюмени.\n"
            "4. obj_type - один из: Стрит-ритейл / ПСН, Офис, Торговое помещение, Склад/База.\n\n"
            f"Текст:\n{text}"
        )
        try:
            response = await self._generate_text(prompt, "Извлеки данные")
            import json
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception:
            logging.exception("Ошибка парсинга параметров (Gemini), используем regex")
        
        return result
    
    @staticmethod
    def _regex_extract_params(text: str) -> dict:
        """Извлекает параметры из текста регулярками (без ИИ)."""
        result = {"area": 0.0, "price": 0.0, "district": "", "obj_type": ""}
        lower = text.lower()
        
        # Площадь: "177 м²", "177м2", "177 кв.м"
        area_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:м2|м²|кв\.?\s*м)", lower)
        if area_match:
            result["area"] = float(area_match.group(1).replace(",", "."))
        
        # Цена: "32 000 000 ₽", "32000000 руб", "32 000 000"
        # Ищем числа от 100 000 и выше (чтобы не путать с площадью/этажом)
        price_candidates = re.findall(r"(\d[\d\s]{5,}(?:\d))", text)
        for candidate in price_candidates:
            cleaned = candidate.replace(" ", "")
            val = float(cleaned)
            if val >= 100000:
                result["price"] = val
                break
        
        # Если не нашли — ищем формат "32 000 000 ₽"
        if not result["price"]:
            price_match = re.search(r"(\d[\d\s,.]+)\s*(?:₽|руб|р\.)", text)
            if price_match:
                cleaned = re.sub(r"[^\d]", "", price_match.group(1))
                if cleaned:
                    result["price"] = float(cleaned)
        
        # Тип объекта
        if "офис" in lower:
            result["obj_type"] = "Офис"
        elif "торгов" in lower:
            result["obj_type"] = "Торговое помещение"
        elif "склад" in lower or "база" in lower or "производств" in lower:
            result["obj_type"] = "Склад/База"
        elif "псн" in lower or "стрит" in lower or "свобод" in lower:
            result["obj_type"] = "Стрит-ритейл / ПСН"
        elif "помещ" in lower or "коммерч" in lower:
            result["obj_type"] = "Стрит-ритейл / ПСН"
        
        # Район
        district_patterns = [
            (r"(?:ленинск|калинин)", "Восточный / Широтная"),
            (r"центр", "Центр"),
            (r"кпд|50\s*лет", "КПД / 50 лет ВЛКСМ"),
            (r"заречн", "Заречный"),
        ]
        for pattern, district in district_patterns:
            if re.search(pattern, lower):
                result["district"] = district
                break
        
        return result

    async def get_mentor_answer(self, user_question: str, user_id: int = None) -> str:
        try:
            # Ищем контекст в локальной базе FAISS + BM25
            try:
                context = rag_engine.search_context(user_question)
            except Exception:
                logging.warning("RAG недоступен, продолжаем без контекста")
                context = ""
            benchmark_context = market_analyzer.analyze_from_text(user_question)

            # Ищем актуальные данные в интернете (если нужно)
            web_context = ""
            if needs_web_search(user_question):
                web_context = web_search(user_question, max_results=3)
                logging.info("Веб-поиск активирован для: %s", user_question[:50])

            final_system_prompt = RBN_SYSTEM_PROMPT

            if context:
                final_system_prompt += f"\n\n{context}"

            if benchmark_context:
                final_system_prompt += f"\n\n{benchmark_context}"

            if web_context:
                final_system_prompt += (
                    f"\n\n{web_context}\n\n"
                    "[ВАЖНО: Выше приведены актуальные данные из интернета. "
                    "Используй их для ответа на вопрос, указывая источники. "
                    "Если данные противоречат базе знаний — приоритет у свежих данных из сети.]"
                )

            if context and not web_context:
                final_system_prompt += (
                    "\n\n[ВАЖНО: При ответе опирайся на предоставленные внутренние "
                    "документы выше, адаптируя их под вопрос пользователя. "
                    "Если контекст не отвечает на вопрос, используй общие знания.]"
                )

            raw_answer = await self._generate_text(final_system_prompt, user_question, user_id)

            # Сохраняем в память если есть id
            if user_id:
                memory_service.add_message(user_id, "user", user_question)
                memory_service.add_message(user_id, "assistant", raw_answer)

            return md_to_html(raw_answer)

        except Exception as e:
            logging.exception("Ошибка ИИ-сервиса (Groq)")
            return f"❌ Ошибка ИИ-сервиса: {e!s}"

    async def analyze_property(self, deal_type, obj_type, area, price, district, user_id: int = None, is_gab: bool = False, monthly_rent: float = 0) -> tuple[str, str | None]:
        benchmark_context = market_analyzer.analyze(
            deal_type=deal_type,
            obj_type=obj_type,
            area=area,
            price=price,
            district=district,
            is_gab=is_gab,
            monthly_rent=monthly_rent,
        )

        if not benchmark_context:
            return "❌ Не удалось собрать данные для этого объекта.", None

        # Генерация графика
        chart_path = None
        try:
            area_f = float(re.sub(r"[^\d.,]", "", str(area)).replace(",", ".") or "0")
            price_f = float(re.sub(r"[^\d.,]", "", str(price)).replace(",", ".") or "0")
            if area_f > 0 and price_f > 0:
                chart_path = market_analyzer.generate_chart(
                    deal_type=deal_type, obj_type=obj_type,
                    area=area_f, price=price_f, district=district,
                )
        except Exception:
            logging.exception("Ошибка генерации графика")

        is_rent = "аренд" in deal_type.lower() or "сдать" in deal_type.lower()
        if not is_rent:
            # Для продажи — ИИ-аналитик (и для ГАБ, и без ГАБ)
            try:
                gab_label = "Да (есть действующий арендатор)" if is_gab else "Нет (арендатора нет, МАП расчётный/рыночный)"
                user_msg = (
                    f"Проанализируй объект коммерческой недвижимости:\n"
                    f"Тип сделки: {deal_type}\n"
                    f"Тип объекта: {obj_type}\n"
                    f"Площадь: {area} м²\n"
                    f"Цена: {price} ₽\n"
                    f"Район: {district}\n"
                    f"Готовый арендный бизнес (ГАБ): {gab_label}\n"
                    f"МАП (ежемесячная аренда): {monthly_rent} ₽/мес\n\n"
                    f"Рыночные данные от калькулятора РБН:\n{benchmark_context}"
                )
                ai_analysis = await self._generate_text(AI_INVESTMENT_ANALYST_PROMPT, user_msg, user_id)
                if ai_analysis and not ai_analysis.startswith("❌"):
                    return md_to_html(ai_analysis), chart_path
            except Exception:
                logging.exception("Ошибка генерации ИИ-анализа, фаллбек на детерминированный отчет")

        return benchmark_context, chart_path


AI_INVESTMENT_ANALYST_PROMPT = """Ты — инвестиционный аналитик компании РБН (Регион Бизнес Недвижимость).
Говори просто и понятно, как объясняешь другу-инвестору. Каждую цифру сопровождай
пояснением «что это значит на практике». Без сложного жаргона — или сразу расшифровывай.

АКТУАЛЬНЫЕ РЫНОЧНЫЕ СТАВКИ:
• Ключевая ставка ЦБ РФ: 14.5%
• Средняя доходность банковских депозитов: ~13% годовых

ЗАПРЕЩЁННЫЕ СЛОВА (никогда не используй):
benchmark, CMA, market pressure, перцентиль, детерминированный, flow, exposure, liquidity index

СТРУКТУРА АНАЛИТИЧЕСКОЙ СПРАВКИ (строго 8 блоков):

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1️⃣ КРАТКОЕ РЕЗЮМЕ

Одним абзацем: что за объект, сколько приносит чистыми в год (NOI),
какая доходность (Cap Rate), за сколько лет окупится, стоит ли покупать.
Это самое главное — инвестор читает только это, остальное — для глубокого анализа.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2️⃣ ИСХОДНЫЕ ДАННЫЕ

Выпиши всё что известно: площадь, цена, цена за м², район, этаж, вход, состояние.
• Если это ГАБ — арендатор, ставка, срок договора, индексация.
• Если НЕ ГАБ — чётко напиши: "Объект продаётся БЕЗ арендатора.
  МАП рассчитан по рыночным ставкам аренды для данного района и площади."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3️⃣ ФИНАНСОВАЯ МОДЕЛЬ

Считай каждую цифру и объясняй простым языком:

• МАП (аренда в месяц): ... ₽/мес
• Валовой годовой доход (GPI = МАП × 12): ... ₽/год
  → "Столько объект приносит в год до вычета расходов"
• Расходы (OPEX ≈ 15% от GPI): ... ₽/год
  → "Налоги, коммуналка, эксплуатация, резерв на простой"
• Чистый доход (NOI = GPI − OPEX): ... ₽/год
  → "Столько реально остаётся в кармане инвестора"
• Доходность (Cap Rate = NOI ÷ Цена × 100): ...%
  → "Процент, который объект зарабатывает на вложенные деньги каждый год"
• Окупаемость (Цена ÷ NOI): ... лет
  → "Через сколько лет арендный доход полностью вернёт стоимость покупки"

📈 ПОЛНАЯ ДОХОДНОСТЬ (IRR) — за весь период владения:
Рассчитай примерный IRR на горизонте 7 лет с учётом:
  — Ежегодный арендный доход (NOI)
  — Рост стоимости объекта: ~5% в год (среднее по рынку КН)
  — Индексация аренды: ~5% в год
  — Стоимость объекта через 7 лет = Цена × 1.05^7

Формула упрощённая: IRR ≈ Cap Rate + Рост стоимости.
Выведи итоговый IRR и сравни с депозитом.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4️⃣ СПРАВЕДЛИВАЯ ЦЕНА ДЛЯ ИНВЕСТОРА

Покажи таблицу: при какой цене этот объект — отличная, нормальная или рисковая сделка.
Используй формулу: Справедливая цена = МАП × множитель (в месяцах).

ЛОГИКА МНОЖИТЕЛЕЙ (чем надёжнее объект, тем больше инвестор готов платить):

• Премиум ГАБ (федеральная сеть, долгий договор, надёжный арендатор):
  Множитель ×120–132 от МАП → окупаемость ~10–11 лет по NOI
  → "Инвестор платит премию за низкий риск и стабильный поток"

• Стандартный ГАБ (обычный арендатор, средний договор):
  Множитель ×108–120 от МАП → окупаемость ~9–10 лет по NOI
  → "Нормальная рыночная цена"

• Рисковый ГАБ (ненадёжный арендатор, короткий договор, локальный бизнес):
  Множитель ×84–108 от МАП → окупаемость ~7–9 лет по NOI
  → "Инвестор требует скидку за высокий риск"

Рассчитай диапазоны цен для каждой категории.
Чётко укажи: текущая цена попадает в какую категорию и почему.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5️⃣ ОБЪЕКТ vs ДЕПОЗИТ — ЧЕСТНОЕ СРАВНЕНИЕ

Сравни конкретными цифрами на горизонте 5 лет — что получит инвестор.

ДЕПОЗИТ под 13% годовых:
• Вложил: [цена объекта] ₽
• Через 5 лет получил процентами: [цена × 0.13 × 5] ₽
• Тело вклада НЕ растёт (те же деньги, только обесценились на инфляцию)
• Итого заработал: ... ₽

ОБЪЕКТ НЕДВИЖИМОСТИ:
• Вложил: [цена объекта] ₽
• Арендный доход за 5 лет (NOI с учётом индексации 5%/год): ... ₽
• Рост стоимости объекта за 5 лет (+5%/год): объект подорожал до ... ₽
• Итого заработал: арендный доход + прирост стоимости = ... ₽

ВЫВОД: "Да, депозит даёт 13% сразу и без хлопот.
Но через 5 лет объект недвижимости приносит суммарно больше,
потому что сам актив дорожает + аренда индексируется.
Депозит — это аренда денег. Недвижимость — это владение активом."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6️⃣ РИСКИ И КРАСНЫЕ ФЛАГИ

Проверь по чек-листу и оцени каждый пункт (низкий / средний / высокий):
• Ставка аренды завышена? (выше рынка = красный флаг)
• Арендатор надёжный? (если нет арендатора — кто реально снимет?)
• Договор зарегистрирован в Росреестре? (менее 11 мес = риск)
• Собственник скрывает арендатора? (красный флаг)
• Причина продажи подозрительная?
• Объект в обременении?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7️⃣ КАК УВЕЛИЧИТЬ СТОИМОСТЬ ОБЪЕКТА

Конкретные шаги для увеличения капитализации:
• Посадить надёжного арендатора (федеральная сеть, медицина, общепит)
• Заложить в договор индексацию 5–7% ежегодно
• Перевести расходы (OPEX) на арендатора по договору (NNN-lease)
• Увеличить ставку через ремонт/улучшения
• Упаковать как ГАБ и перепродать с премией

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8️⃣ ИТОГОВЫЙ ВЫВОД

• Справедлива ли запрашиваемая цена? (чёткий ответ)
• Кому подойдёт этот объект?
  — Рантье (стабильный доход, минимум хлопот)
  — Диверсификатор (часть портфеля в недвижимости)
  — Предприниматель (использует сам)
  — Новичок (первая инвестиция в КН)
  — Переговорщик (купить дешевле, перепродать)
• Стоит ли покупать? (да / нет / да, но при условии...)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ВОПРОСЫ ДЛЯ ПРОВЕРКИ (Due Diligence)

Если не хватает критической информации — в конце выведи список
вопросов, которые брокер должен задать собственнику.

СТИЛЬ: пиши так, чтобы человек без финансового образования всё понял.
Структурируй списками и жирным шрифтом. Только русский язык.
"""


ai_engine = AIEngine()


