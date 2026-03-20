import json

# 1. Update hiddify_ALL_IN_ONE.json
client_conf_path = "configs_2026_03_20/hiddify_ALL_IN_ONE.json"
with open(client_conf_path, "r") as f:
    client_data = json.load(f)

for outb in client_data.get("outbounds", []):
    if outb.get("tag") == "proxy" or outb.get("tag") == "auto":
        outb["outbounds"] = [x if x != "vless-xhttp" else "vless-grpc" for x in outb["outbounds"]]
    
    if outb.get("tag") == "vless-xhttp":
        outb["tag"] = "vless-grpc"
        outb.pop("transport", None)
        outb["server_port"] = 8443
        outb["tls"]["server_name"] = "taxi.yandex.ru"
        outb["tls"].pop("insecure", None)
        outb["tls"]["reality"] = {
            "enabled": True,
            "public_key": "n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4",
            "short_id": ""
        }
        outb["transport"] = {
            "type": "grpc",
            "service_name": "taxi_grpc_service"
        }
        
    if outb.get("tag") == "hysteria":
        if "tls" in outb:
            outb["tls"]["server_name"] = "ya.ru"

with open(client_conf_path, "w") as f:
    json.dump(client_data, f, indent=2)

# 2. Update xray_config_yandex.json
# Using the backup as a base and writing to root
server_backup = "_backup_configs/xray_config_yandex.json"
server_root = "xray_config_yandex.json"
with open(server_backup, "r") as f:
    server_data = json.load(f)

# Add grpc inbound
new_inbound = {
    "tag": "VLESS-Reality-gRPC",
    "protocol": "vless",
    "listen": "0.0.0.0",
    "port": 8443,
    "settings": {
        "clients": [
            {
                "id": "eb4a1cf2-4235-4b0a-83b2-0e5a298389ed",
                "flow": ""
            }
        ],
        "decryption": "none"
    },
    "streamSettings": {
        "network": "grpc",
        "security": "reality",
        "realitySettings": {
            "show": False,
            "dest": "taxi.yandex.ru:443",
            "xver": 0,
            "serverNames": [
                "taxi.yandex.ru",
                "ya.ru"
            ],
            "privateKey": "4PjME9JBUmV-Td9rZGS9l0147TXqMJtcU_f2iG-PVxA",
            "shortIds": [
                ""
            ],
            "minClientVer": "",
            "maxClientVer": "",
            "maxTimeDiff": 0,
            "publicKey": "n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4"
        },
        "grpcSettings": {
            "serviceName": "taxi_grpc_service"
        }
    },
    "sniffing": {
        "enabled": True,
        "destOverride": ["http", "tls"]
    }
}
server_data["inbounds"].append(new_inbound)

with open(server_root, "w") as f:
    json.dump(server_data, f, indent=2)

print("Configs updated!")
