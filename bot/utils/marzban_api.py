import aiohttp
import logging
from bot.config import MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD

logger = logging.getLogger(__name__)

class MarzbanAPI:
    def __init__(self):
        self.base_url = MARZBAN_URL.rstrip('/')
        self.username = MARZBAN_USERNAME
        self.password = MARZBAN_PASSWORD
        self.token = None

    async def get_token(self):
        url = f"{self.base_url}/api/admin/token"
        data = {
            "username": self.username,
            "password": self.password
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    res_data = await response.json()
                    self.token = res_data.get("access_token")
                    return self.token
                else:
                    logger.error(f"Failed to get token: {response.status}")
                    return None

    async def create_user(self, username: str, expire: int = None, data_limit: int = 0):
        if not self.token:
            await self.get_token()
        
        url = f"{self.base_url}/api/user"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "username": username,
            "proxies": {"vless": {}},
            "expire": expire,
            "data_limit": data_limit,
            "data_limit_reset_strategy": "no_reset"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    sub_url = data.get("subscription_url", "")
                    
                    # Если путь относительный, добавляем базу
                    if sub_url and sub_url.startswith("/"):
                        sub_url = f"{self.base_url}{sub_url}"
                    
                    # Заменяем внутренний адрес на публичный IP для ссылки пользователю
                    if sub_url:
                        sub_url = sub_url.replace("localhost", "37.1.212.51").replace("127.0.0.1", "37.1.212.51")
                    
                    data["subscription_url"] = sub_url
                    return data
                elif response.status == 409:
                    logger.warning(f"User {username} already exists")
                    user_data = await self.get_user(username)
                    if user_data:
                        sub_url = user_data.get("subscription_url", "")
                        if sub_url and sub_url.startswith("/"):
                            sub_url = f"{self.base_url}{sub_url}"
                        if sub_url:
                            sub_url = sub_url.replace("localhost", "37.1.212.51").replace("127.0.0.1", "37.1.212.51")
                        user_data["subscription_url"] = sub_url
                    return user_data
                else:
                    logger.error(f"Failed to create user: {response.status}")
                    return None

    async def get_user(self, username: str):
        if not self.token:
            await self.get_token()
            
        url = f"{self.base_url}/api/user/{username}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
