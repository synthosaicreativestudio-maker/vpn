import asyncio
import aiohttp
import json
from bot.config import MARZBAN_URL, MARZBAN_USERNAME, MARZBAN_PASSWORD

async def test():
    base_url = MARZBAN_URL.rstrip('/')
    token = None
    
    # 1. Get Token
    async with aiohttp.ClientSession() as session:
        url = f"{base_url}/api/admin/token"
        data = {
            "username": MARZBAN_USERNAME, 
            "password": MARZBAN_PASSWORD
        }
        async with session.post(url, data=data) as resp:
            if resp.status == 200:
                res = await resp.json()
                token = res.get("access_token")
                print("Token received")
            else:
                print(f"Token failed: {resp.status}")
                return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Test payloads
    test_cases = [
        {
            "proxies": {"vless": {"flow": "xtls-rprx-vision"}},
            "inbounds": {"vless": ["VLESS_IN"]}
        },
        {
            "proxies": {"vless": {}},
            "inbounds": {"vless": ["VLESS_IN"]}
        }
    ]
    
    for i, p in enumerate(test_cases):
        print(f"\n--- Testing Payload {i+1}: {json.dumps(p)} ---")
        username = f"test_user_{i+109}"
        
        payload = p.copy()
        payload["username"] = username
        payload["expire"] = 0
        payload["data_limit"] = 0
        payload["data_limit_reset_strategy"] = "no_reset"
        
        async with aiohttp.ClientSession() as session:
            # Delete if exists
            await session.delete(f"{base_url}/api/user/{username}", headers=headers)
            
            # Create
            async with session.post(f"{base_url}/api/user", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    links = data.get("links", [])
                    print(f"Status: 200. Links: {len(links)}")
                    print(f"Full Response: {json.dumps(data, indent=2)}")
                else:
                    text = await resp.text()
                    print(f"Failed: {resp.status} - {text}")

if __name__ == "__main__":
    asyncio.run(test())
