"""Сервис веб-поиска для актуализации данных.

Использует DuckDuckGo (бесплатно, без API-ключа).
Применяется для получения актуальной информации:
- Ключевая ставка ЦБ РФ
- Курсы валют
- Ставки ипотеки
- Новости рынка недвижимости
"""

import logging
import re
from datetime import datetime

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# Ключевые слова, при которых автоматически запускается веб-поиск
TRIGGER_PATTERNS = [
    r"ключев\w*\s*ставк",      # ключевая ставка
    r"ставк\w*\s*цб",          # ставка ЦБ
    r"центральн\w*\s*банк",    # центральный банк
    r"ипотек\w*\s*ставк",      # ипотечная ставка
    r"ипотек\w*\s*процент",    # ипотечный процент
    r"курс\s*(доллар|евро|юан|валют)",  # курсы валют
    r"инфляц",                 # инфляция
    r"актуальн\w*\s*(цен|став|данн|информац)",  # актуальные данные
    r"сейчас|сегодня|текущ",   # маркеры актуальности
    r"средн\w*\s*ставк\w*\s*аренд",  # средняя ставка аренды
    r"рынок\s*недвижимост\w*\s*202[5-9]",  # рынок недвижимости 2025-2029
    r"прогноз\w*\s*(рын|цен|став)",  # прогнозы
    r"налог\w*\s*(ставк|измен|нов)",  # налоговые изменения
    r"кадастров\w*\s*стоимост",  # кадастровая стоимость
]

_compiled_triggers = [re.compile(p, re.IGNORECASE) for p in TRIGGER_PATTERNS]


def needs_web_search(query: str) -> bool:
    """Определяет, нужен ли веб-поиск для данного запроса."""
    return any(pattern.search(query) for pattern in _compiled_triggers)


def _build_search_query(user_query: str) -> str:
    """Формирует поисковый запрос, обогащая контекстом недвижимости."""
    # Если вопрос уже содержит конкретику — используем как есть
    if len(user_query.split()) > 5:
        return user_query

    # Для коротких запросов добавляем контекст
    today = datetime.now().strftime("%Y")
    return f"{user_query} {today} Россия"


def web_search(query: str, max_results: int = 5) -> str:
    """Выполняет веб-поиск и возвращает форматированный контекст.

    Returns:
        Строка с результатами поиска для вставки в промпт LLM.
        Пустая строка если поиск не удался.
    """
    search_query = _build_search_query(query)
    today = datetime.now().strftime("%d.%m.%Y")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=max_results, region="ru-ru"))

        if not results:
            logger.info("Веб-поиск: нет результатов для '%s'", search_query)
            return ""

        context_parts = [
            f"=== АКТУАЛЬНЫЕ ДАННЫЕ ИЗ ИНТЕРНЕТА (дата поиска: {today}) ===",
        ]
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            if len(body) > 400:
                body = body[:400] + "..."
            source = r.get("href", "")
            context_parts.append(
                f"[{i}] {title}\n{body}\nИсточник: {source}"
            )

        context = "\n\n".join(context_parts)
        logger.info(
            "Веб-поиск: найдено %d результатов для '%s'",
            len(results),
            search_query,
        )
        return context

    except Exception:
        logger.exception("Ошибка веб-поиска для '%s'", search_query)
        return ""
