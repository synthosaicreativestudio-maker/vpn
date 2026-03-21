"""Асинхронный клиент для Subscription Manager Panel API."""

import aiohttp
import logging

logger = logging.getLogger(__name__)


class PanelAPI:
    """HTTP-клиент к нашей панели (panel/app.py)."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

    # ── Health ────────────────────────────────────────────────

    async def health(self) -> dict | None:
        """Проверка связи с панелью."""
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as r:
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

        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{self.base_url}/users",
                json=payload,
                headers=self._headers(),
            ) as r:
                if r.status == 201:
                    data = await r.json()
                    logger.info("User created: %s", email)
                    return data
                if r.status == 409:
                    logger.info("User %s already exists, fetching links", email)
                    return await self.get_links(email)
                err = await r.text()
                logger.error("Create user failed (%s): %s", r.status, err)
        return None

    async def get_links(self, email: str) -> dict | None:
        """Получить все VPN-ссылки пользователя."""
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{self.base_url}/users/{email}/links",
                headers=self._headers(),
            ) as r:
                if r.status == 200:
                    return await r.json()
                err = await r.text()
                logger.error("Get links failed (%s): %s", r.status, err)
        return None

    async def get_user_ips(self, email: str) -> dict | None:
        """Получить активные IP пользователя."""
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{self.base_url}/users/{email}/ips",
                headers=self._headers(),
            ) as r:
                if r.status == 200:
                    return await r.json()
        return None

    async def delete_user(self, email: str) -> bool:
        """Удалить пользователя из панели и Xray."""
        async with aiohttp.ClientSession() as s:
            async with s.delete(
                f"{self.base_url}/users/{email}",
                headers=self._headers(),
            ) as r:
                return r.status == 200

    async def get_stats(self) -> dict | None:
        """Статистика панели."""
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"{self.base_url}/stats",
                headers=self._headers(),
            ) as r:
                if r.status == 200:
                    return await r.json()
        return None
