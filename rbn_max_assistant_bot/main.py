"""Точка входа Max-бота РБН.

Использует Long Polling для получения обновлений от MAX API.
"""

import asyncio
import logging
import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from aiohttp import web
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.max_api import MaxBotAPI  # noqa: E402
from handlers.bot_handler import handle_update  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def polling_loop(api: MaxBotAPI):
    """Бесконечный цикл Long Polling."""
    marker = None
    logger.info("Запуск Long Polling...")

    while True:
        try:
            response = await api.get_updates(marker=marker, timeout=30)
            updates = response.get("updates", [])
            new_marker = response.get("marker")

            if new_marker:
                marker = new_marker

            for update in updates:
                # Сохраняем порядок событий: callback должен успеть обновить FSM
                # до обработки следующего текстового сообщения пользователя.
                await handle_update(api, update)

        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Ошибка в polling loop, переподключение через 5с...")
            await asyncio.sleep(5)


async def run_webhook_server(
    api: MaxBotAPI,
    webhook_url: str | None,
    webhook_secret: str | None,
    webhook_host: str,
    webhook_port: int,
    webhook_path: str,
):
    async def health(_: web.Request) -> web.Response:
        return web.json_response({"ok": True})

    async def webhook_handler(request: web.Request) -> web.Response:
        if webhook_secret:
            received_secret = request.headers.get("X-Max-Bot-Api-Secret")
            if received_secret != webhook_secret:
                logger.warning("Webhook request rejected: bad secret")
                return web.json_response({"ok": False}, status=403)

        try:
            update = await request.json()
        except Exception:
            logger.exception("Webhook request rejected: invalid JSON")
            return web.json_response({"ok": False}, status=400)

        logger.info("Webhook update received: %s", update.get("update_type"))
        asyncio.create_task(handle_update(api, update))
        return web.json_response({"ok": True})

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_post(webhook_path, webhook_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, webhook_host, webhook_port)

    try:
        await site.start()
        logger.info("Webhook server started on %s:%s%s", webhook_host, webhook_port, webhook_path)

        if webhook_url:
            await api.unsubscribe_webhook(url=webhook_url)
            result = await api.subscribe_webhook(
                url=webhook_url,
                secret=webhook_secret,
            )
            logger.info("Webhook subscription result: %s", result)
        else:
            logger.warning("WEBHOOK_URL is not set. Start ngrok, set WEBHOOK_URL, then restart the bot.")

        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main():
    token = os.getenv("MAX_BOT_TOKEN")
    if not token:
        logger.error("MAX_BOT_TOKEN не задан в .env!")
        return

    webhook_url = os.getenv("WEBHOOK_URL")
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    webhook_host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    webhook_port = int(os.getenv("WEBHOOK_PORT", "8080"))
    webhook_path = os.getenv("WEBHOOK_PATH", "/webhook/max")

    api = MaxBotAPI(token)

    # Проверяем подключение
    try:
        me = await api.get_me()
        logger.info("Бот Max подключён: %s (@%s)", me.get("name"), me.get("username"))
    except Exception:
        logger.exception("Не удалось подключиться к MAX API")
        await api.close()
        return

    try:
        if webhook_url:
            await run_webhook_server(
                api,
                webhook_url,
                webhook_secret,
                webhook_host,
                webhook_port,
                webhook_path,
            )
        else:
            logger.info("WEBHOOK_URL не задан, запускаем Long Polling...")
            await polling_loop(api)
    finally:
        await api.close()
        logger.info("Бот Max остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот Max остановлен по Ctrl+C.")
