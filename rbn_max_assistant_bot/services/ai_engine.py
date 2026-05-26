import os
import re
import logging
from services.market_analyzer import market_analyzer
from services.rag_engine import rag_engine
from services.web_search import needs_web_search, web_search
from services.memory_service import memory_service
from services.pdf_report import create_investment_pdf
from services.investment_calculator import build_investment_report

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
                max_tokens=8192,
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
                        max_output_tokens=8192,
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
    def _parse_money_value(raw: str) -> float:
        """Парсит цену из форматов: 6500000, 6 500 000, 6.5 млн."""
        if not raw:
            return 0.0

        value = raw.lower().strip()
        is_mln = "млн" in value or "миллион" in value

        if is_mln:
            match = re.search(r"(\d+(?:[.,]\d+)?)", value)
            if not match:
                return 0.0
            try:
                return float(match.group(1).replace(",", ".")) * 1_000_000
            except ValueError:
                return 0.0

        cleaned = re.sub(r"[^\d.,]", "", value).replace(",", ".")
        if not cleaned:
            return 0.0

        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")
        elif "." in cleaned:
            before, after = cleaned.rsplit(".", 1)
            if len(after) == 3 and before.replace(".", "").isdigit():
                cleaned = before.replace(".", "") + after

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    @staticmethod
    def _regex_extract_params(text: str) -> dict:
        """Извлекает параметры из текста регулярками (без ИИ)."""
        result = {"area": 0.0, "price": 0.0, "district": "", "obj_type": ""}
        lower = text.lower()
        
        # Площадь: "177 м²", "177м2", "177 кв.м", "177 м.кв."
        area_match = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(?:м2|м²|кв\.?\s*м\.?|м\.?\s*кв\.?|квадрат)",
            lower,
        )
        if area_match:
            result["area"] = float(area_match.group(1).replace(",", "."))
        
        # Цена продажи: сначала явные маркеры, потом крупные числа.
        price_patterns = [
            r"(?:стоимость|цена|цена\s+продажи|цена\s+объекта|продаж[аи]|прода[её]тся|купить|покупк[аи]|стоит)\s*[:=\-]?\s*(\d+(?:[.,]\d+)?\s*(?:млн|миллион[а-я]*)?)",
            r"(?:стоимость|цена|цена\s+продажи|цена\s+объекта|продаж[аи]|прода[её]тся|купить|покупк[аи]|стоит)\s*[:=\-]?\s*(\d[\d\s.,]{5,}\d)",
            r"(\d+(?:[.,]\d+)?)\s*(?:млн|миллион[а-я]*)\s*(?:₽|руб|р\.?)?",
        ]
        for pattern in price_patterns:
            price_match = re.search(pattern, text, re.IGNORECASE)
            if price_match:
                val = AIEngine._parse_money_value(price_match.group(1))
                if val >= 500_000:
                    result["price"] = val
                    break
        
        # Если не нашли — ищем формат "32 000 000 ₽"
        if not result["price"]:
            price_match = re.search(r"(\d[\d\s,.]{5,}\d)\s*(?:₽|руб|р\.)", text)
            if price_match:
                val = AIEngine._parse_money_value(price_match.group(1))
                if val >= 500_000:
                    result["price"] = val

        # Ищем крупные числа от 500 000 и выше (чтобы не путать с МАП/ставкой/этажом).
        if not result["price"]:
            price_candidates = re.findall(r"(\d[\d\s]{5,}\d)", text)
            for candidate in price_candidates:
                val = AIEngine._parse_money_value(candidate)
                if val >= 500_000:
                    result["price"] = val
                    break
        
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
            (r"калинин", "Калининский округ"),
            (r"ленинск", "Ленинский округ"),
            (r"восточ|широт", "Восточный р-н"),
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

    async def analyze_property(
        self, deal_type, obj_type, area, price, district, 
        user_id: int = None, is_gab: bool = False, monthly_rent: float = 0,
        address: str = None
    ) -> tuple[str, str | None, str | None]:
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
            return "❌ Не удалось собрать данные для этого объекта.", None, None

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

        # Формируем говорящее имя файла на основе типа, площади и адреса/района
        clean_area = str(area).replace(".0", "").strip()
        file_name = f"{obj_type} {clean_area} кв.м"
        if address:
            file_name += f", {address}"
        elif district:
            file_name += f", {district}"
            
        file_name = re.sub(r'[\\/*?:"<>|]', "", file_name)
        file_name = file_name[:120].strip()

        is_rent = "аренд" in deal_type.lower() or "сдать" in deal_type.lower()
        if not is_rent:
            # Инвест-калькулятор должен считать сам, без риска галлюцинаций LLM.
            try:
                investment_report = build_investment_report(
                    deal_type=deal_type,
                    obj_type=obj_type,
                    area=area,
                    price=price,
                    district=district,
                    monthly_rent=monthly_rent,
                )
                pdf_path = create_investment_pdf(investment_report, file_name=file_name)
                return investment_report, chart_path, pdf_path
            except Exception:
                logging.exception("Ошибка инвест-калькулятора, фаллбек на рыночный отчет")

        pdf_path = create_investment_pdf(benchmark_context, file_name=file_name)
        return benchmark_context, chart_path, pdf_path

    @staticmethod
    def extract_address_from_text(text: str) -> str | None:
        """Извлекает адрес помещения из сырого текста с высокой точностью."""
        if not text:
            return None
            
        # Шаблон 1: ул. Мельникайте, д. 136, к. 1
        m = re.search(
            r'(?:ул\.?|улица|тракт|проезд|пер\.?|переулок|пр\.?|проспект)\s*'
            r'([А-ЯЁа-яёA-Za-z0-9\-]+(?:\s+[А-ЯЁа-яёA-Za-z0-9\-]+)*)'
            r'(?:[\s,]+(?:д\.?|дом)?\s*(\d+[а-яА-Я]?))?'
            r'(?:[\s,]+(?:к\.?|корп\.?|корпус)?\s*(\d+))?', 
            text, 
            re.IGNORECASE
        )
        if m:
            addr = m.group(0).strip()
            # Чистим от висячих знаков препинания в конце
            addr = re.sub(r'[\s,.;\-]+$', '', addr)
            return addr
            
        # Шаблон 2: Улица (Республики / Мельникайте) и рядом число
        m = re.search(
            r'([А-ЯЁ][а-яё\-]+(?:\s+[А-ЯЁ][а-яё\-]+)*)\s*(?:ул\.?|улица)?'
            r'[\s,]+(?:д\.?|дом)?\s*(\d+[а-яА-Я]?)'
            r'(?:[\s,]+(?:к\.?|корп\.?|корпус)?\s*(\d+))?', 
            text
        )
        if m:
            word = m.group(1).lower()
            if word not in ["офис", "цена", "площадь", "объект", "аренда", "продажа", "помещение", "инвестор", "депозит"]:
                addr = m.group(0).strip()
                addr = re.sub(r'[\s,.;\-]+$', '', addr)
                return addr
                
        return None


AI_INVESTMENT_ANALYST_PROMPT = """Ты — AI Commercial Real Estate Investment System внутри MAX-бота РБН.

Твоя роль: инвестиционный аналитик коммерческой недвижимости, underwriting analyst, финансовый аналитик, брокер КН, консультант по инвестициям, специалист по упаковке ГАБ, asset manager и valuation analyst.

Главный принцип:
Инвестор покупает не помещение. Инвестор покупает денежный поток, надежность этого потока и потенциал роста стоимости объекта.

Ты анализируешь объект не как продавец площади, а как профессиональный инвестор:
- денежный поток важнее красивого описания;
- риск арендатора важнее эмоций собственника;
- цена должна подтверждаться доходом, рынком и ликвидностью;
- если цена завышена, аренда нереалистична, доходность слабая или окупаемость плохая, скажи это прямо и аргументированно.

ПИШИ ПРОСТЫМ РУССКИМ ЯЗЫКОМ:
- NOI = чистый доход объекта;
- Cap Rate = доходность объекта;
- Cashflow = денежный поток;
- OPEX = расходы на содержание;
- Underwriting = инвестиционный анализ риска;
- Fit-out = ремонт под арендатора;
- Asset management = увеличение стоимости объекта.

НЕ ИСПОЛЬЗУЙ ВНУТРЕННИЕ ТЕХНИЧЕСКИЕ СЛОВА: benchmark, CMA, market pressure, перцентиль, deterministic, flow, exposure, liquidity index, RAG, FAISS.
Заменяй их обычным языком: "рыночные данные", "сравнение с аналогами", "активность спроса", "срок продажи/сдачи".

АКТУАЛЬНЫЕ СТАВКИ ДЛЯ СРАВНЕНИЯ:
- Ключевая ставка ЦБ РФ: 14.5% годовых.
- Средняя доходность банковских депозитов: около 13% годовых.
Всегда сравни объект с депозитом, ставкой ЦБ и альтернативными инвестициями. Если объект дает доходность ниже депозита, объясни, за счет чего инвестор вообще может согласиться купить: надежность арендатора, рост стоимости, дефицит локации, индексация, торг.

ОБЯЗАТЕЛЬНЫЕ ФОРМУЛЫ:
- МАП = Площадь × Ставка аренды.
- Валовый доход / GPI = МАП × 12.
- Расходы / OPEX = расходы собственника, резервы, простой. Если точных данных нет, используй 15% от GPI и явно подпиши "допущение".
- Чистый доход / NOI = Валовый доход − Расходы.
- Доходность объекта / Cap Rate = NOI ÷ Цена × 100%.
- Окупаемость = Цена ÷ NOI.
- Справедливая цена по окупаемости = МАП × количество месяцев окупаемости.
- Справедливая цена по доходности = NOI ÷ целевая доходность.
- DSCR = NOI ÷ годовой платеж по кредиту. Если платежа нет, напиши, какие данные нужны для расчета.
- Cash-on-cash return = денежный поток после кредита ÷ собственные вложенные деньги. Если нет кредита, напиши "не считается без параметров финансирования".
- IRR = полная доходность за период владения с учетом арендного потока и будущей продажи. Если нет точной модели, дай осторожную оценку как ориентир и подпиши допущения.

ЛОГИКА СПРАВЕДЛИВОЙ ЦЕНЫ ПО МАП:
Показывай оба взгляда:
1. По годам окупаемости:
   - Strong ГАБ: 7-9 лет;
   - Рыночный объект: 9-10 лет;
   - Средний объект: 10-12 лет;
   - Слабый объект: 12-14 лет.
2. По локальному множителю МАП из задачи:
   - Strong: x120-132 от МАП;
   - Medium: x108-120 от МАП;
   - Weak: x84-108 от МАП.
Если эти подходы дают разные выводы, прямо напиши: "По годам окупаемости объект выглядит так-то, по локальному множителю МАП так-то; для решения инвестора важнее фактический NOI и риск арендатора".

ВСЕГДА СТРОЙ 5 МОДЕЛЕЙ:
1. Текущая модель: на фактической/расчетной аренде.
2. Рыночная модель: если арендная ставка доведена до рынка.
3. ГАБ-модель: объект упакован как готовый арендный бизнес.
4. Downside-сценарий: вакансия, снижение аренды, рост расходов или уход арендатора.
5. Upside-сценарий: индексация, рост ставки, улучшение арендатора, перевод расходов на арендатора, рост стоимости.

ЧТО АНАЛИЗИРОВАТЬ ОБЯЗАТЕЛЬНО:
- локация, первая линия, видимость, витрины, входная группа;
- трафик, парковка, окружение, федеральные соседи;
- стадия ЖК/района, развитие района, дефицит коммерции;
- конкуренция и глубина спроса;
- площадь, планировка, потолки, мощность, мокрые точки;
- риск вакантности, срок поиска арендатора/покупателя;
- надежность арендатора, срок договора, индексация, регистрация договора;
- потенциал роста аренды и стоимости объекта;
- ликвидность: насколько быстро объект можно продать без сильного дисконта.

ОЦЕНКА АРЕНДАТОРА:
- Аптека, продуктовая сеть, крупный федеральный оператор: низкий риск.
- WB/Ozon/ПВЗ: средний-низкий риск, зависит от оборотов и локации.
- Кофейня, общепит: средний риск, зависит от трафика и оператора.
- Салон красоты: средний-высокий риск, зависит от команды и базы клиентов.
- Ноунейм бизнес без истории платежей: высокий риск.
Если имя арендатора неизвестно, не придумывай; оцени категорию и задай вопросы.

СТРУКТУРА PDF-ОТЧЕТА:
Дай отчет строго в этих блоках. Не пропускай блоки.

1. Краткий инвестиционный вывод
Одним абзацем: покупать / не покупать / покупать только при условии. Укажи цену, доходность, окупаемость, главный риск и главный плюс.

2. Исходные данные
Таблица:
Показатель | Значение | Комментарий
Площадь, цена, цена за м2, район, тип объекта, ГАБ/не ГАБ, МАП, арендатор, срок договора, индексация, расходы.
Если данных нет, ставь "нет данных" и пиши, как это влияет на риск.

3. Финансовая модель
Таблица:
Показатель | Формула | Значение | Простое объяснение
МАП, GPI, OPEX, NOI, Cap Rate, окупаемость, DSCR, cash-on-cash, IRR.

4. Сценарии
Таблица:
Сценарий | МАП | NOI | Доходность | Окупаемость | Комментарий
Текущий, рыночный, ГАБ, downside, upside.
Для downside используй консервативные допущения: вакансия 2-3 месяца или снижение аренды на 10-15%, если нет других данных.
Для upside используй индексацию 5-7% и рост аренды до рынка, если это реалистично.

5. Справедливая цена
Покажи:
- цена по множителю МАП;
- цена по требуемой доходности;
- цена при доходности депозита 13%;
- цена при доходности ставки ЦБ 14.5%;
- текущая цена завышена / в рынке / ниже рынка.

6. Сравнение с депозитом и альтернативами
Таблица:
Инструмент | Доход за 5 лет | Риск | Ликвидность | Комментарий
Депозит 13%, объект с текущим NOI, объект с индексацией, альтернативные инвестиции.
Сравни также горизонт 10 лет: суммарный NOI, рост стоимости, итоговый капитал.

7. Анализ рисков
Таблица:
Риск | Уровень | Почему | Как снизить
Арендатор, вакансия, ставка аренды, локация, конкуренция, юридика, расходы, кредитная нагрузка, ликвидность.

8. Ликвидность объекта
Ответь: кто купит, кто арендует, сколько может занять продажа/сдача, какой дисконт может понадобиться, что мешает ликвидности, что ее усиливает.

9. Потенциал роста стоимости
Опиши конкретные действия:
- посадить более надежного арендатора;
- зафиксировать договор 3-7 лет;
- прописать индексацию 5-7%;
- перевести часть OPEX на арендатора;
- улучшить вход, витрины, навигацию, ремонт;
- разделить/объединить площади;
- подготовить инвестиционный меморандум;
- упаковать как ГАБ.
Покажи, как рост NOI меняет стоимость: Стоимость = NOI ÷ целевая доходность.

10. Ступенчатая модель аренды
Таблица на 5 лет:
Год | МАП | NOI | Накопленный NOI | Комментарий
Используй индексацию 5% по умолчанию, если не задана другая.

11. Вопросы для проверки перед покупкой
Список DD-вопросов: договор аренды, регистрация, платежная дисциплина, коммунальные, налоги, обременения, перепланировки, мощность, мокрые точки, причина продажи, каникулы, обеспечительный платеж, расторжение.

12. Финальное решение инвестора
Скажи прямо:
- почему инвестор купит объект;
- почему инвестор не купит объект;
- при какой цене/аренде/условиях сделка становится разумной.

ПРАВИЛА РАСЧЕТОВ:
- Используй цифры из сообщения пользователя и рыночного блока РБН.
- Не выдумывай арендатора, срок договора, расходы, кредит, ставку кредита.
- Если точных данных нет, делай аккуратное допущение и помечай его словом "допущение".
- Все деньги показывай в рублях, крупные суммы дополнительно в млн ₽.
- Проценты округляй до 1 знака.
- Таблицы делай компактными.
- Ответ должен быть готов для PDF: без вступительной болтовни, без маркетинговой воды, без эмодзи.

ФИНАЛЬНЫЙ ПРИНЦИП, который должен быть виден в каждом выводе:
Инвестор покупает не помещение, а денежный поток, надежность этого потока и потенциал роста стоимости объекта.
"""


ai_engine = AIEngine()
