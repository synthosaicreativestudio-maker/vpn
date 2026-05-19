import hashlib
import logging
import aiohttp

logger = logging.getLogger(__name__)

TERMINAL_KEY = "1778920894454"
TERMINAL_PASSWORD = "pvqr*Y$rWWPINSh6"

async def init_tbank_payment(amount: int, order_id: str, description: str) -> str:
    url = "https://securepay.tinkoff.ru/v2/Init"
    payload = {
        "TerminalKey": TERMINAL_KEY,
        "Amount": amount * 100,
        "OrderId": order_id,
        "Description": description,
    }
    
    # Считаем токен
    token_data = payload.copy()
    token_data["Password"] = TERMINAL_PASSWORD
    sorted_keys = sorted(token_data.keys())
    concatenated_values = "".join(str(token_data[k]) for k in sorted_keys)
    token = hashlib.sha256(concatenated_values.encode('utf-8')).hexdigest()
    
    payload["Token"] = token
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                if result.get("Success"):
                    return result.get("PaymentURL")
                else:
                    logger.error(f"T-Bank Init Error: {result}")
                    return None
    except Exception as e:
        logger.error(f"T-Bank Init Exception: {e}")
        return None
