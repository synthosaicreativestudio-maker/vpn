#!/usr/bin/env python3
import sys
import json
import socket
import urllib.request
import urllib.error

OAUTH_TOKEN = "y0__wgBEKLHkMsHGMHdEyDtgJ7LFzDH0sj8BzcedlXM7WCpdcMiDo30tXhV59N_"
ZONE = "ru-central1-a"

def request_json(url, data=None, headers=None, method="GET"):
    if headers is None:
        headers = {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        try:
            err_json = json.loads(err)
            return {"error": err_json}
        except Exception:
            return {"error": err}
    except Exception as e:
        return {"error": str(e)}

def test_tcp_port(ip, port, timeout=3):
    """Проверяет доступность TCP-порта с локального компьютера."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def main():
    print("=== Запуск локального исследования Yandex Cloud & Сети ===")
    
    # 1. Получение IAM-токена
    print("\n[1/4] Авторизация в Yandex Cloud...")
    url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    res = request_json(url, data={"yandexPassportOauthToken": OAUTH_TOKEN}, method="POST")
    if "error" in res:
        print(f"❌ Ошибка авторизации: {res['error']}")
        sys.exit(1)
    iam_token = res["iamToken"]
    headers = {"Authorization": f"Bearer {iam_token}"}
    
    # 2. Получение Folder ID
    clouds = request_json("https://resource-manager.api.cloud.yandex.net/resource-manager/v1/clouds", headers=headers)
    if "error" in clouds or not clouds.get("clouds"):
        print("❌ Не удалось получить список облаков.")
        sys.exit(1)
    cloud_id = clouds["clouds"][0]["id"]
    
    folders = request_json(f"https://resource-manager.api.cloud.yandex.net/resource-manager/v1/folders?cloudId={cloud_id}", headers=headers)
    if "error" in folders or not folders.get("folders"):
        print("❌ Не удалось получить список папок.")
        sys.exit(1)
    folder_id = folders["folders"][0]["id"]
    print(f"✅ Успешно вошли. Folder ID: {folder_id}")

    # 3. Список ВМ
    print("\n[2/4] Проверка виртуальных машин...")
    vms = request_json(f"https://compute.api.cloud.yandex.net/compute/v1/instances?folderId={folder_id}", headers=headers)
    active_ips = []
    if "instances" in vms:
        for inst in vms["instances"]:
            name = inst["name"]
            status = inst["status"]
            ip = None
            if inst.get("networkInterfaces"):
                net_if = inst["networkInterfaces"][0]
                if net_if.get("primaryV4Address") and net_if["primaryV4Address"].get("oneToOneNat"):
                    ip = net_if["primaryV4Address"]["oneToOneNat"].get("address")
            print(f"  • ВМ: {name:<25} | Статус: {status:<10} | IP: {ip or 'Нет внешнего IP'}")
            if ip:
                active_ips.append((name, ip))
    else:
        print("  Виртуальные машины не найдены.")

    # 4. Список внешних IP-адресов в каталоге
    print("\n[3/4] Проверка внешних IP-адресов (Лимит в каталоге обычно 5)...")
    addrs = request_json(f"https://vpc.api.cloud.yandex.net/vpc/v1/addresses?folderId={folder_id}", headers=headers)
    stuck_ips = []
    total_ips = 0
    if "addresses" in addrs:
        for addr in addrs["addresses"]:
            total_ips += 1
            addr_id = addr["id"]
            name = addr.get("name", "Без имени")
            ip = addr.get("ipV4Address", {}).get("address", "None")
            reserved = addr.get("reserved", False)
            used = "ИСПОЛЬЗУЕТСЯ" if ip != "None" else "ЗАВИС (Пустой)"
            print(f"  • IP: {ip:<15} | ID: {addr_id} | Резерв: {str(reserved):<5} | Статус: {used} ({name})")
            if ip == "None":
                stuck_ips.append(addr_id)
    
    print(f"\nВсего занято внешних адресов: {total_ips} из 5 допустимых.")
    
    if stuck_ips:
        print(f"\n⚠️ ОБНАРУЖЕНО {len(stuck_ips)} ЗАВИСШИХ АДРЕСОВ, КОТОРЫЕ БЛОКИРУЮТ ВЫДАЧУ НОВЫХ IP!")
        ans = input("Хотите очистить их прямо сейчас для освобождения квоты? (y/n): ").strip().lower()
        if ans == 'y':
            for addr_id in stuck_ips:
                del_url = f"https://vpc.api.cloud.yandex.net/vpc/v1/addresses/{addr_id}"
                del_res = request_json(del_url, headers=headers, method="DELETE")
                if "error" in del_res:
                    print(f"  ❌ Ошибка удаления {addr_id}: {del_res['error']}")
                else:
                    print(f"  ✅ Удален зависший адрес {addr_id}")
        else:
            print("  Пропущено очищение адресов.")

    # 5. Тестирование сети
    print("\n[4/4] Тестирование доступности портов релеев прямо с вашего устройства...")
    if active_ips:
        for name, ip in active_ips:
            print(f"  Проверка {name} ({ip}):")
            # Проверяем порты 443 и 8081
            for port in [443, 8081]:
                ok = test_tcp_port(ip, port)
                status_str = "✅ ДОСТУПЕН (ТСПУ пропускает)" if ok else "❌ НЕ ДОСТУПЕН (Заблокирован или Xray не запущен)"
                print(f"    - Порт {port:<4}: {status_str}")
    else:
        print("  Нет активных IP для тестирования доступности.")

    print("\n=== Исследование сети завершено! ===")

if __name__ == "__main__":
    main()
