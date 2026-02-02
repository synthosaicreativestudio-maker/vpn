import requests
import json
import subprocess
import base64

def register():
    # 1. Generate keys
    priv = subprocess.check_output(["wg", "genkey"]).decode().strip()
    pub = subprocess.check_output(["sh", "-c", f"echo {priv} | wg pubkey"]).decode().strip()
    
    # 2. Register
    url = "https://api.cloudflareclient.com/v0a2158/reg"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "okhttp/3.12.1"
    }
    body = {
        "key": pub,
        "install_id": "",
        "fcm_token": "",
        "referrer": "",
        "warp_enabled": True,
        "tos": "2020-09-01T00:00:00.000+02:00",
        "type": "Android",
        "locale": "en_US"
    }
    
    r = requests.post(url, headers=headers, json=body)
    data = r.json()
    
    # 3. Form result
    res = {
        "private_key": priv,
        "public_key": data['config']['peers'][0]['public_key'],
        "address_v4": data['config']['interface']['addresses']['v4'],
        "address_v6": data['config']['interface']['addresses']['v6'],
        "reserved": data['config']['interface']['addresses']['reserved'],
        "endpoint": data['config']['peers'][0]['endpoint']['host']
    }
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    register()
