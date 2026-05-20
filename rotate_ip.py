#!/usr/bin/env python3
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess

OAUTH_TOKEN = "y0__wgBEKLHkMsHGMHdEyDtgJ7LFzDH0sj8BzcedlXM7WCpdcMiDo30tXhV59N_"
ZONE = "ru-central1-a"
WHITELIST_FILE = "/root/whitelist_ips.txt"
YANDEX_WHITELIST_FILE = "/root/yandex_whitelist_ips.txt"
US_SERVER_IP = "37.1.212.51"
SSH_PUBLIC_KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMEBXzDzrAUgKEOev/sZ930x2DNq7On4j2fhGpDkPMUV root@a773095550.local"

def request_json(url, data=None, headers=None, method="GET"):
    """Вспомогательная функция для HTTP REST запросов."""
    if headers is None:
        headers = {}
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {e.reason}\nBody: {err_body}")
        raise e

def get_iam_token(oauth_token):
    print("Получение IAM-токена...")
    url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    data = {"yandexPassportOauthToken": oauth_token}
    res = request_json(url, data=data, method="POST")
    return res["iamToken"]

def get_folder_id(iam_token):
    print("Получение Folder ID...")
    headers = {"Authorization": f"Bearer {iam_token}"}
    
    clouds_res = request_json("https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds", headers=headers)
    if not clouds_res.get("clouds"):
        raise Exception("Облака Yandex Cloud не найдены!")
    cloud_id = clouds_res["clouds"][0]["id"]
    
    folders_res = request_json(f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}", headers=headers)
    if not folders_res.get("folders"):
        raise Exception("Папки в облаке не найдены!")
    return folders_res["folders"][0]["id"]

def get_subnet_id(iam_token, folder_id):
    print(f"Поиск подсети в зоне {ZONE}...")
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = f"https://vpc.api.cloud.yandex.net/vpc/v1/subnets?folderId={folder_id}"
    res = request_json(url, headers=headers)
    for subnet in res.get("subnets", []):
        if subnet["zoneId"] == ZONE:
            return subnet["id"]
    raise Exception(f"Не найдена подсеть в зоне {ZONE}!")

def wait_operation(iam_token, operation_id):
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = f"https://operation.api.cloud.yandex.net/operations/{operation_id}"
    while True:
        res = request_json(url, headers=headers)
        if res.get("done", False):
            if "error" in res:
                raise Exception(f"Ошибка операции: {res['error']}")
            return res.get("response")
        time.sleep(3)

def find_instance(iam_token, folder_id, vm_name):
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}"
    res = request_json(url, headers=headers)
    for inst in res.get("instances", []):
        if inst["name"] == vm_name:
            return inst
    return None

def get_latest_image_id(iam_token):
    print("Получение ID последнего образа Ubuntu 22.04 LTS...")
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = "https://compute.api.cloud.yandex.net/compute/v1/images:latestByFamily?folderId=standard-images&family=ubuntu-2204-lts"
    res = request_json(url, headers=headers)
    return res["id"]

def create_instance(iam_token, folder_id, subnet_id, vm_name):
    image_id = get_latest_image_id(iam_token)
    print(f"Создание виртуальной машины {vm_name} с образом {image_id}...")
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = "https://compute.api.cloud.yandex.net/compute/v1/instances"
    
    user_data = (
        "#cloud-config\n"
        "users:\n"
        "  - name: ubuntu\n"
        "    groups: sudo\n"
        "    shell: /bin/bash\n"
        "    sudo: ['ALL=(ALL) NOPASSWD:ALL']\n"
        "    ssh_authorized_keys:\n"
        f"      - {SSH_PUBLIC_KEY}\n"
    )
    
    data = {
        "folderId": folder_id,
        "name": vm_name,
        "zoneId": ZONE,
        "platformId": "standard-v3",
        "resourcesSpec": {
            "memory": "1073741824", # 1 GB
            "cores": "2",
            "coreFraction": "20"
        },
        "metadata": {
            "user-data": user_data
        },
        "bootDiskSpec": {
            "diskSpec": {
                "imageId": image_id,
                "size": "10737418240", # 10 GB
                "typeId": "network-hdd"
            },
            "autoDelete": True
        },
        "networkInterfaceSpecs": [
            {
                "subnetId": subnet_id,
                "primaryV4AddressSpec": {}
            }
        ]
    }
    
    op = request_json(url, data=data, headers=headers, method="POST")
    res = wait_operation(iam_token, op["id"])
    return res

def get_instance_network_info(iam_token, instance_id):
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = f"https://compute.api.cloud.yandex.net/compute/v1/instances/{instance_id}"
    inst = request_json(url, headers=headers)
    
    net_if = inst["networkInterfaces"][0]
    current_ip = None
    
    if "primaryV4Address" in net_if and "oneToOneNat" in net_if["primaryV4Address"]:
        nat = net_if["primaryV4Address"]["oneToOneNat"]
        current_ip = nat.get("address")
                 
    return current_ip

def remove_nat(iam_token, instance_id):
    print("Отвязка текущего внешнего IP (удаление One-to-One NAT)...")
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = f"https://compute.api.cloud.yandex.net/compute/v1/instances/{instance_id}/removeOneToOneNat"
    data = {
        "networkInterfaceIndex": "0"
    }
    try:
        op = request_json(url, data=data, headers=headers, method="POST")
        wait_operation(iam_token, op["id"])
    except Exception as e:
        print(f"Предупреждение при удалении NAT: {e}")

def add_ephemeral_nat(iam_token, instance_id):
    print("Запрос нового случайного динамического IP (добавление One-to-One NAT)...")
    headers = {"Authorization": f"Bearer {iam_token}"}
    url = f"https://compute.api.cloud.yandex.net/compute/v1/instances/{instance_id}/addOneToOneNat"
    data = {
        "networkInterfaceIndex": "0",
        "oneToOneNatSpec": {
            "ipVersion": "IPV4"
        }
    }
    op = request_json(url, data=data, headers=headers, method="POST")
    wait_operation(iam_token, op["id"])

def load_whitelist():
    import os
    if os.path.exists(YANDEX_WHITELIST_FILE):
        print(f"Загрузка оптимизированной базы белых IP Яндекса из {YANDEX_WHITELIST_FILE}...")
        ips = set()
        with open(YANDEX_WHITELIST_FILE, "r") as f:
            for line in f:
                ip = line.strip()
                if ip:
                    ips.add(ip)
        print(f"Загружено {len(ips)} уникальных белых IP Яндекса.")
        return ips

    print(f"Загрузка базы белых IP из {WHITELIST_FILE}...")
    ips = set()
    try:
        with open(WHITELIST_FILE, "r") as f:
            for line in f:
                if line.startswith("open tcp 443"):
                    parts = line.split()
                    if len(parts) >= 4:
                        ips.add(parts[3])
    except FileNotFoundError:
        print("База белых IP не найдена локально, пробуем скачать с GitHub...")
        url = "https://raw.githubusercontent.com/openlibrecommunity/twl/main/code/scan/out/whitelist_ips.txt"
        with urllib.request.urlopen(url) as response:
            for line in response:
                line_str = line.decode("utf-8")
                if line_str.startswith("open tcp 443"):
                    parts = line_str.split()
                    if len(parts) >= 4:
                        ips.add(parts[3])
    print(f"Загружено {len(ips)} уникальных белых IP-адресов.")
    return ips

def configure_remote_relay(ip_address):
    print(f"\n=== Начинаем удаленную настройку релея на IP {ip_address} ===")
    
    max_wait = 24
    ssh_ok = False
    for i in range(max_wait):
        print(f"Проверка доступности SSH (попытка {i+1}/{max_wait})...")
        res = subprocess.run(
            ["ssh", "-i", "/root/.ssh/id_ed25519", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", f"ubuntu@{ip_address}", "echo ok"],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            print("✅ SSH доступен!")
            ssh_ok = True
            break
        time.sleep(5)
        
    if not ssh_ok:
        raise Exception("❌ Не удалось подключиться к релею по SSH за отведенное время.")

    bash_script = """#!/bin/bash
set -e

echo "=== Обновление пакетов и установка зависимостей ==="
sudo apt-get update -y
sudo apt-get install -y curl jq

echo "=== Установка Xray Core ==="
sudo bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install

echo "=== Запись конфигурации Xray для ретрансляции ==="
sudo mkdir -p /usr/local/etc/xray
sudo tee /usr/local/etc/xray/config.json > /dev/null << 'EOF'
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "port": 443,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "37.1.212.51",
        "port": 443,
        "network": "tcp"
      },
      "tag": "relay-443-tcp"
    },
    {
      "port": 2053,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "37.1.212.51",
        "port": 2053,
        "network": "tcp"
      },
      "tag": "relay-2053-tcp"
    },
    {
      "port": 2083,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "37.1.212.51",
        "port": 2083,
        "network": "tcp"
      },
      "tag": "relay-2083-tcp"
    },
    {
      "port": 2087,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "37.1.212.51",
        "port": 2087,
        "network": "tcp"
      },
      "tag": "relay-2087-tcp"
    },
    {
      "port": 8081,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "37.1.212.51",
        "port": 443,
        "network": "tcp"
      },
      "tag": "relay-8081-tcp"
    },
    {
      "port": 10443,
      "protocol": "dokodemo-door",
      "settings": {
        "address": "37.1.212.51",
        "port": 10443,
        "network": "udp"
      },
      "tag": "relay-10443-udp"
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "settings": {}
    }
  ]
}
EOF

echo "=== Включение BBR и оптимизация ядра ==="
if ! grep -q "net.core.default_qdisc=fq" /etc/sysctl.conf; then
  echo "net.core.default_qdisc=fq" | sudo tee -a /etc/sysctl.conf
fi
if ! grep -q "net.ipv4.tcp_congestion_control=bbr" /etc/sysctl.conf; then
  echo "net.ipv4.tcp_congestion_control=bbr" | sudo tee -a /etc/sysctl.conf
fi
sudo sysctl -p

echo "=== Запуск и включение Xray в автозагрузку ==="
sudo systemctl daemon-reload
sudo systemctl enable xray
sudo systemctl restart xray

echo "=== Настройка релея завершена успешно! ==="
"""

    print("Выполнение конфигурационного скрипта на удаленном релее...")
    process = subprocess.Popen(
        ["ssh", "-i", "/root/.ssh/id_ed25519", "-o", "StrictHostKeyChecking=no", f"ubuntu@{ip_address}", "bash"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = process.communicate(input=bash_script)
    
    if process.returncode != 0:
        print("❌ Ошибка при выполнении настройки релея:")
        print(stderr)
        raise Exception(f"Ошибка настройки релея: {stderr}")
        
    print("✅ Релей успешно настроен!")
    print(stdout)

def update_panel_config(vm_idx, new_ip):
    config_path = "/root/vpn/panel/config.py"
    print(f"\n=== Обновление конфигурации панели (релей #{vm_idx} -> {new_ip}) ===")
    
    try:
        with open(config_path, "r") as f:
            content = f.read()
            
        import re
        # Заменяем TEST_RELAY_IP_N
        pattern = r'(TEST_RELAY_IP_' + str(vm_idx) + r'\s*=\s*os\.getenv\("TEST_RELAY_IP_' + str(vm_idx) + r'",\s*["\']).*?(["\']\))'
        new_content = re.sub(pattern, r'\g<1>' + new_ip + r'\2', content)
        
        # Для обратной совместимости (если vm_idx == 1, обновляем ANTI_STUB_IP и RELAY_IP)
        if vm_idx == 1:
            new_content = re.sub(r'(ANTI_STUB_IP\s*=\s*os\.getenv\("ANTI_STUB_IP",\s*["\']).*?(["\']\))', r'\g<1>' + new_ip + r'\2', new_content)
            new_content = re.sub(r'(RELAY_IP\s*=\s*os\.getenv\("RELAY_IP",\s*["\']).*?(["\']\))', r'\g<1>' + new_ip + r'\2', new_content)
            
        with open(config_path, "w") as f:
            f.write(new_content)
            
        print(f"✅ Конфигурация для TEST_RELAY_IP_{vm_idx} успешно обновлена.")
    except Exception as e:
        print(f"❌ Ошибка обновления конфигурации: {e}")
        raise e

def restart_panel():
    print("\n=== Перезапуск vpn-panel ===")
    res = subprocess.run(["systemctl", "restart", "vpn-panel.service"], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Ошибка перезапуска vpn-panel: {res.stderr}")
        raise Exception(f"Ошибка перезапуска vpn-panel: {res.stderr}")
    print("✅ Служба vpn-panel успешно перезапущена.")

def main():
    try:
        whitelist = load_whitelist()
        
        iam_token = get_iam_token(OAUTH_TOKEN)
        folder_id = get_folder_id(iam_token)
        subnet_id = get_subnet_id(iam_token, folder_id)
        
        vm_names = ["relay-stub-1", "relay-stub-2", "relay-stub-3"]
        
        while True:
            print("\n==========================================")
            print(f"Запуск очередной проверки релеев: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("==========================================")
            
            config_changed = False
            
            for idx, vm_name in enumerate(vm_names, 1):
                print(f"\nПроверка релея #{idx} ({vm_name})...")
                
                try:
                    iam_token = get_iam_token(OAUTH_TOKEN)
                except Exception as e:
                    print(f"Ошибка получения IAM-токена: {e}. Попробуем в следующей итерации.")
                    break
                
                inst = find_instance(iam_token, folder_id, vm_name)
                if not inst:
                    print(f"Виртуалка {vm_name} не найдена. Создаем.")
                    inst = create_instance(iam_token, folder_id, subnet_id, vm_name)
                    instance_id = inst["id"]
                else:
                    instance_id = inst["id"]
                    print(f"Виртуалка {vm_name} найдена: ID {instance_id}")
                
                current_ip = get_instance_network_info(iam_token, instance_id)
                
                ip_ok = False
                if current_ip:
                    if current_ip in whitelist:
                        print(f"✅ IP {current_ip} для {vm_name} находится в белом списке.")
                        ip_ok = True
                    else:
                        print(f"❌ IP {current_ip} для {vm_name} отсутствует в белом списке.")
                else:
                    print(f"⚠️ У {vm_name} нет внешнего IP.")
                
                if not ip_ok:
                    attempts = 0
                    if current_ip:
                        remove_nat(iam_token, instance_id)
                        current_ip = None
                        
                    while True:
                        attempts += 1
                        print(f"Подбор IP для {vm_name}, попытка #{attempts}...")
                        
                        while True:
                            try:
                                add_ephemeral_nat(iam_token, instance_id)
                                break
                            except Exception as e:
                                err_msg = str(e)
                                if "Quota limit" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg or "limit exceeded" in err_msg.lower():
                                    print("⚠️ Rate Limit Yandex Cloud. Ждем 60 секунд...")
                                    time.sleep(60)
                                else:
                                    raise e
                                    
                        current_ip = get_instance_network_info(iam_token, instance_id)
                        if current_ip in whitelist:
                            print(f"🎉 Найден белый IP {current_ip} для {vm_name}!")
                            break
                        else:
                            print(f"❌ IP {current_ip} заблокирован. Сбрасываем.")
                            remove_nat(iam_token, instance_id)
                            current_ip = None
                            time.sleep(10)
                    
                    configure_remote_relay(current_ip)
                    update_panel_config(idx, current_ip)
                    config_changed = True

            if config_changed:
                restart_panel()
                
            print("\nВсе релеи проверены. Засыпаем на 10 минут...")
            time.sleep(600)
            
    except KeyboardInterrupt:
        print("\nСкрипт остановлен пользователем.")
        sys.exit(0)
    except Exception as e:
        print(f"Критическая ошибка в работе демона: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
