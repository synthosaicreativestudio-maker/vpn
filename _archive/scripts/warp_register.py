import requests
import json
import base64
import os

def register_warp():
    url = "https://api.cloudflareclient.com/v0a2158/reg"
    headers = {
        "User-Agent": "okhttp/3.12.1",
        "Content-Type": "application/json"
    }
    
    # Registration doesn't strictly need a body, but some headers are good
    r = requests.post(url, headers=headers, json={})
    if r.status_code != 200:
        print(f"Error registering: {r.status_code}")
        print(r.text)
        return None
    
    data = r.json()
    account_id = data['id']
    token = data['token']
    main_address = data['config']['interface']['addresses']['v4']
    private_key = data['config']['interface']['addresses'].get('private_key', '') # Note: CF doesn't return private key, we need to generate it locally usually
    
    print(f"Account ID: {account_id}")
    print(f"Token: {token}")
    print(f"Address: {main_address}")
    
    return data

# Actually, the correct way is to generate keys LOCALLY first
import subprocess

def get_keys():
    try:
        priv = subprocess.check_output(["/usr/bin/wg", "genkey"]).decode().strip()
        pub = subprocess.check_output(["/usr/bin/echo", priv, "|", "/usr/bin/wg", "pubkey"], shell=True).decode().strip()
        return priv, pub
    except:
        # Fallback if wg is not found (but it should be if wireguard is loaded)
        return None, None

def register_with_pubkey(pubkey):
    url = "https://api.cloudflareclient.com/v0a2158/reg"
    headers = {
        "User-Agent": "okhttp/3.12.1",
        "Content-Type": "application/json"
    }
    body = {
        "key": pubkey,
        "install_id": "",
        "fcm_token": "",
        "referrer": "",
        "warp_enabled": True,
        "tos": "2020-09-01T00:00:00.000+02:00",
        "type": "Android",
        "locale": "en_US"
    }
    r = requests.post(url, headers=headers, json=body)
    return r.json()

# Let's try to run this on the server
