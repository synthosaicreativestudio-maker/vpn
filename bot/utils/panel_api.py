"""Асинхронный клиент для Subscription Manager Panel API.

Использует один aiohttp.ClientSession на весь жизненный цикл объекта,
что исключает overhead от создания TCP-соединения на каждый запрос.
"""

import aiohttp
import logging

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10)


class PanelAPI:
    """HTTP-клиент к нашей панели (panel/app.py).

    Использование:
        panel = PanelAPI(base_url=PANEL_URL, api_key=PANEL_API_KEY)
        await panel.setup()         # создать сессию
        ...
        await panel.teardown()      # закрыть сессию при остановке бота
    """

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None

    async def setup(self):
        """Создать и сохранить единую HTTP-сессию."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=_DEFAULT_TIMEOUT,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            )
            logger.info("PanelAPI session created")

    async def teardown(self):
        """Закрыть HTTP-сессию при остановке бота."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("PanelAPI session closed")

    def _session_or_fallback(self) -> aiohttp.ClientSession:
        """Вернуть активную сессию или создать временную (fallback)."""
        if self._session and not self._session.closed:
            return self._session
        # Fallback: создаём временную сессию если setup() не был вызван
        logger.warning("PanelAPI: using temporary session — call setup() first")
        return aiohttp.ClientSession(
            timeout=_DEFAULT_TIMEOUT,
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
        )

    def _headers(self) -> dict:
        return {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

    # ── Health ────────────────────────────────────────────────

    async def health(self) -> dict | None:
        """Проверка связи с панелью."""
        try:
            s = self._session_or_fallback()
            async with s.get(f"{self.base_url}/health") as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            logger.error("Panel health check failed: %s", e)
        return None

    # ── Users ─────────────────────────────────────────────────

    async def create_user(
        self,
        email: str,
        uuid: str | None = None,
        ip_limit: int = 2,
        expire_days: int | None = None,
        description: str | None = None,
    ) -> dict | None:
        """Создать пользователя в панели + добавить в Xray."""
        payload: dict = {"email": email, "ip_limit": ip_limit}
        if uuid:
            payload["uuid"] = uuid
        if expire_days:
            payload["expire_days"] = expire_days
        if description:
            payload["description"] = description

        try:
            s = self._session_or_fallback()
            async with s.post(f"{self.base_url}/users", json=payload) as r:
                if r.status == 201:
                    data = await r.json()
                    logger.info("User created: %s", email)
                    return data
                if r.status == 409:
                    logger.info("User %s already exists, fetching links", email)
                    return await self.get_links(email)
                err = await r.text()
                logger.error("Create user failed (%s): %s", r.status, err)
        except Exception as e:
            logger.error("Create user exception: %s", e)
        return None

    async def get_user(self, email: str) -> dict | None:
        """Получить информацию о пользователе."""
        try:
            s = self._session_or_fallback()
            async with s.get(f"{self.base_url}/users/{email}") as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            logger.error("Get user failed: %s", e)
        return None

    async def update_user(self, email: str, **kwargs) -> dict | None:
        """Обновить пользователя в панели (лимиты, трафик, активность)."""
        try:
            s = self._session_or_fallback()
            async with s.patch(f"{self.base_url}/users/{email}", json=kwargs) as r:
                if r.status == 200:
                    return await r.json()
                err = await r.text()
                logger.error("Update user failed (%s): %s", r.status, err)
        except Exception as e:
            logger.error("Update user exception: %s", e)
        return None

    async def get_links(self, email: str) -> dict | None:
        """Получить все VPN-ссылки пользователя."""
        try:
            s = self._session_or_fallback()
            async with s.get(f"{self.base_url}/users/{email}/links") as r:
                if r.status == 200:
                    return await r.json()
                err = await r.text()
                logger.error("Get links failed (%s): %s", r.status, err)
        except Exception as e:
            logger.error("Get links exception: %s", e)
        return None

    async def get_user_ips(self, email: str) -> dict | None:
        """Получить активные IP пользователя."""
        try:
            s = self._session_or_fallback()
            async with s.get(f"{self.base_url}/users/{email}/ips") as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            logger.error("Get user IPs exception: %s", e)
        return None

    async def delete_user(self, email: str) -> bool:
        """Удалить пользователя из панели и Xray."""
        try:
            s = self._session_or_fallback()
            async with s.delete(f"{self.base_url}/users/{email}") as r:
                return r.status == 200
        except Exception as e:
            logger.error("Delete user exception: %s", e)
        return False

    async def get_stats(self) -> dict | None:
        """Статистика панели."""
        try:
            s = self._session_or_fallback()
            async with s.get(f"{self.base_url}/stats") as r:
                if r.status == 200:
                    return await r.json()
        except Exception as e:
            logger.error("Get stats exception: %s", e)
        return None
