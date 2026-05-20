"""Клиент для MAX Bot API (platform-api.max.ru).

Чистая реализация через aiohttp, без сторонних фреймворков.
Поддерживает: Long Polling, отправку сообщений, inline-клавиатуры, callback-ответы.
"""

import logging
import ssl

import aiohttp

logger = logging.getLogger(__name__)

BASE_URL = "https://platform-api.max.ru"


class MaxBotAPI:
    """Асинхронный клиент для Max Bot API."""

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": token,
            "Content-Type": "application/json",
        }
        self._session: aiohttp.ClientSession | None = None
        # Max.ru использует сертификаты российских УЦ,
        # которых нет в стандартном trust store macOS/Linux
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self._ssl_ctx)
            # Таймаут 90с — Long Polling ждёт до 30с + запас
            timeout = aiohttp.ClientTimeout(total=90)
            self._session = aiohttp.ClientSession(
                headers=self.headers, connector=connector, timeout=timeout
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    #  Информация о боте
    # ------------------------------------------------------------------

    async def get_me(self) -> dict:
        session = await self._get_session()
        async with session.get(f"{BASE_URL}/me") as resp:
            return await resp.json()

    # ------------------------------------------------------------------
    #  Long Polling
    # ------------------------------------------------------------------

    async def get_updates(
        self,
        marker: int | None = None,
        timeout: int = 30,
        types: str = "message_created,message_callback,bot_started",
    ) -> dict:
        """Получает обновления через long polling."""
        session = await self._get_session()
        params = {"timeout": timeout, "types": types}
        if marker is not None:
            params["marker"] = marker

        async with session.get(f"{BASE_URL}/updates", params=params) as resp:
            return await resp.json()

    # ------------------------------------------------------------------
    #  Webhook subscriptions
    # ------------------------------------------------------------------

    async def get_subscriptions(self) -> dict:
        """Returns active webhook subscriptions."""
        session = await self._get_session()
        async with session.get(f"{BASE_URL}/subscriptions") as resp:
            return await resp.json()

    async def subscribe_webhook(
        self,
        *,
        url: str,
        update_types: list[str] | None = None,
        secret: str | None = None,
    ) -> dict:
        """Subscribes this bot to updates through a webhook endpoint."""
        session = await self._get_session()
        body = {"url": url}
        if update_types:
            body["update_types"] = update_types
        if secret:
            body["secret"] = secret

        async with session.post(f"{BASE_URL}/subscriptions", json=body) as resp:
            result = await resp.json()
            if resp.status != 200:
                logger.error("MAX webhook subscribe error %d: %s", resp.status, result)
            return result

    async def unsubscribe_webhook(self, *, url: str) -> dict:
        """Removes a webhook subscription for this bot."""
        session = await self._get_session()
        async with session.delete(
            f"{BASE_URL}/subscriptions", params={"url": url}
        ) as resp:
            result = await resp.json()
            if resp.status != 200:
                logger.error("MAX webhook unsubscribe error %d: %s", resp.status, result)
            return result

    # ------------------------------------------------------------------
    #  Отправка сообщений
    # ------------------------------------------------------------------

    async def send_message(
        self,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        text: str,
        format: str = "html",
        attachments: list | None = None,
    ) -> dict:
        """Отправляет сообщение пользователю или в чат."""
        session = await self._get_session()

        params = {}
        if user_id:
            params["user_id"] = user_id
        if chat_id:
            params["chat_id"] = chat_id

        body = {"text": text, "format": format}
        if attachments:
            body["attachments"] = attachments

        async with session.post(
            f"{BASE_URL}/messages", params=params, json=body
        ) as resp:
            result = await resp.json()
            if resp.status != 200:
                logger.error("MAX API error %d: %s", resp.status, result)
            return result

    async def send_message_with_keyboard(
        self,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        text: str,
        buttons: list[list[dict]],
        format: str = "html",
    ) -> dict:
        """Отправляет сообщение с inline-клавиатурой."""
        attachments = [
            {
                "type": "inline_keyboard",
                "payload": {"buttons": buttons},
            }
        ]
        return await self.send_message(
            user_id=user_id,
            chat_id=chat_id,
            text=text,
            format=format,
            attachments=attachments,
        )

    # ------------------------------------------------------------------
    #  Callback ответы
    # ------------------------------------------------------------------

    async def answer_callback(
        self,
        callback_id: str,
        notification: str | None = None,
        message: dict | None = None,
    ) -> dict:
        """Отвечает на нажатие inline-кнопки."""
        session = await self._get_session()
        params = {"callback_id": callback_id}
        body = {}
        if notification:
            body["notification"] = notification
        if message:
            body["message"] = message

        async with session.post(
            f"{BASE_URL}/answers", params=params, json=body
        ) as resp:
            return await resp.json()

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    #  Отправка изображений
    # ------------------------------------------------------------------

    async def upload_image(self, file_path: str) -> str | None:
        """Загружает изображение в Max и возвращает token."""
        session = await self._get_session()
        async with session.post(
            f"{BASE_URL}/uploads", params={"type": "image"}
        ) as resp:
            data = await resp.json()
            upload_url = data.get("url")
            if not upload_url:
                logger.error("Не удалось получить upload URL: %s", data)
                return None

        import aiohttp as _aiohttp
        form = _aiohttp.FormData()
        form.add_field("data", open(file_path, "rb"), filename="chart.png", content_type="image/png")
        conn = _aiohttp.TCPConnector(ssl=self._ssl_ctx)
        async with _aiohttp.ClientSession(connector=conn) as upload_session:
            async with upload_session.post(upload_url, data=form) as resp:
                result = await resp.json()
                token = None
                if isinstance(result, dict):
                    token = result.get("token")
                    if not token and "photos" in result:
                        photos = result["photos"]
                        if isinstance(photos, dict):
                            token = photos.get("token")
                        elif isinstance(photos, list) and photos:
                            token = photos[0].get("token")
                if not token:
                    logger.error("Не удалось получить token: %s", result)
                return token

    async def send_image(
        self,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        token: str,
        text: str = "",
    ) -> dict:
        """Отправляет изображение в чат."""
        attachments = [{"type": "image", "payload": {"token": token}}]
        return await self.send_message(
            user_id=user_id, chat_id=chat_id,
            text=text or "📊", attachments=attachments,
        )

    #  Утилиты для кнопок
    # ------------------------------------------------------------------

    @staticmethod
    def callback_button(text: str, payload: str) -> dict:
        return {"type": "callback", "text": text, "payload": payload}

    @staticmethod
    def message_button(text: str, payload: str | None = None) -> dict:
        btn = {"type": "message", "text": text}
        if payload:
            btn["payload"] = payload
        return btn

    @staticmethod
    def link_button(text: str, url: str) -> dict:
        return {"type": "link", "text": text, "url": url}
