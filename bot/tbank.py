"""Интеграция с Т-Банк (Тинькофф) Интернет-эквайринг.

Документация API: https://www.tbank.ru/kassa/dev/payments/
"""
import hashlib
import logging

import aiohttp

from bot.config import TBANK_TERMINAL_KEY, TBANK_PASSWORD, TBANK_API_URL

logger = logging.getLogger(__name__)


async def init_tbank_payment(amount: int, order_id: str, description: str) -> str | None:
    """Инициализировать платёж и получить URL платёжной страницы.

    Args:
        amount: Сумма в рублях (будет переведена в копейки).
        order_id: Уникальный идентификатор заказа.
        description: Описание товара/услуги.

    Returns:
        URL для редиректа пользователя или None при ошибке.
    """
    url = f"{TBANK_API_URL}Init"
    payload = {
        "TerminalKey": TBANK_TERMINAL_KEY,
        "Amount": amount * 100,  # перевод в копейки
        "OrderId": order_id,
        "Description": description,
    }

    # Формирование токена подписи (SHA-256 по отсортированным значениям + пароль)
    token_data = payload.copy()
    token_data["Password"] = TBANK_PASSWORD
    sorted_keys = sorted(token_data.keys())
    concatenated_values = "".join(str(token_data[k]) for k in sorted_keys)
    token = hashlib.sha256(concatenated_values.encode("utf-8")).hexdigest()

    payload["Token"] = token

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                result = await response.json()
                if result.get("Success"):
                    return result.get("PaymentURL")
                logger.error("T-Bank Init Error: %s", result)
                return None
    except Exception as e:
        logger.error("T-Bank Init Exception: %s", e)
        return None
