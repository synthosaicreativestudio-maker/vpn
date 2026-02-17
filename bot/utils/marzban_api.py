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

    def _fix_user_data(self, data):
        if not data:
            return data
            
        public_ip = "37.1.212.51"
        
        # Исправляем subscription_url
        sub_url = data.get("subscription_url", "")
        if sub_url:
            if sub_url.startswith("/"):
                sub_url = f"{self.base_url}{sub_url}"
            sub_url = sub_url.replace("localhost", public_ip).replace("127.0.0.1", public_ip)
            data["subscription_url"] = sub_url
            
        # Исправляем прямые ссылки (links)
        links = data.get("links", [])
        fixed_links = []
        for link in links:
            fixed_links.append(link.replace("localhost", public_ip).replace("127.0.0.1", public_ip))
        data["links"] = fixed_links
        
        return data

    async def create_user(self, username: str, expire: int = None, data_limit: int = 0):
        if not self.token:
            await self.get_token()
        
        url = f"{self.base_url}/api/user"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Для гарантированной генерации VLESS Reality ссылки нужно:
        # 1. Явно указать flow (xtls-rprx-vision)
        # 2. Явно включить inbound (VLESS_IN), иначе Marzban его исключает
        payload = {
            "username": username,
            "proxies": {
                "vless": {
                    "flow": "xtls-rprx-vision"
                }
            },
            "inbounds": {
                "vless": ["VLESS_IN"]
            },
            "expire": expire,
            "data_limit": data_limit,
            "data_limit_reset_strategy": "no_reset"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Marzban API success for {username}: links found: {len(data.get('links', []))}")
                    return self._fix_user_data(data)
                elif response.status == 409:
                    logger.warning(f"User {username} already exists")
                    user_data = await self.get_user(username)
                    return user_data
                else:
                    err_text = await response.text()
                    logger.error(f"Failed to create user: {response.status}, response: {err_text}")
                    return None

    async def get_user(self, username: str):
        if not self.token:
            await self.get_token()
            
        url = f"{self.base_url}/api/user/{username}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._fix_user_data(data)
                else:
                    return None
