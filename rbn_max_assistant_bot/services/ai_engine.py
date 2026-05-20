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
            
        return benchmark_context, chart_path


ai_engine = AIEngine()
