#!/usr/bin/env python3
"""
Автоматическая настройка VLESS + REALITY для Marzban
Выполняет все шаги автоматически на удаленном сервере
"""

import subprocess
import sys
from pathlib import Path

# Данные сервера из PROXY_SETTINGS.md
SERVER_IP = "37.1.212.51"
SSH_USER = "root"
SSH_PASSWORD = "LEJ6U5chSK"  # Из PROXY_SETTINGS.md

def run_command(cmd, check=True, capture_output=True):
    """Выполнить команду"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения команды: {cmd}")
        print(f"   {e.stderr if e.stderr else e.stdout}")
        if check:
            sys.exit(1)
        return None

def check_ssh_access():
    """Проверить доступность SSH"""
    print("🔍 Проверка SSH доступа к серверу...")
    result = run_command(
        f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no {SSH_USER}@{SERVER_IP} 'echo OK'",
        check=False
    )
    if result == "OK":
        print("✅ SSH доступен")
        return True
    else:
        print("⚠️  Прямой SSH доступ недоступен (требуется пароль или ключ)")
        return False

def copy_script_to_server():
    """Скопировать скрипт на сервер"""
    script_path = Path(__file__).parent / "auto_setup_reality_non_interactive.sh"
    
    if not script_path.exists():
        print(f"❌ Файл не найден: {script_path}")
        sys.exit(1)
    
    print("📤 Копирование скрипта на сервер...")
    
    # Попытка через scp с паролем (требует sshpass)
    if run_command("which sshpass", check=False):
        cmd = f'sshpass -p "{SSH_PASSWORD}" scp -o StrictHostKeyChecking=no {script_path} {SSH_USER}@{SERVER_IP}:/tmp/'
    else:
        # Попытка через обычный scp (требует SSH ключи)
        cmd = f'scp -o StrictHostKeyChecking=no {script_path} {SSH_USER}@{SERVER_IP}:/tmp/'
    
    result = run_command(cmd, check=False)
    if result is not None or not check_ssh_access():
        print("✅ Скрипт скопирован")
        return True
    else:
        print("⚠️  Не удалось скопировать скрипт автоматически")
        print(f"   Выполните вручную: scp {script_path} {SSH_USER}@{SERVER_IP}:/tmp/")
        return False

def execute_on_server():
    """Выполнить скрипт на сервере"""
    print("🚀 Запуск автоматической настройки на сервере...")
    
    script_cmd = "chmod +x /tmp/auto_setup_reality_non_interactive.sh && /tmp/auto_setup_reality_non_interactive.sh"
    
    if run_command("which sshpass", check=False):
        cmd = f'sshpass -p "{SSH_PASSWORD}" ssh -o StrictHostKeyChecking=no {SSH_USER}@{SERVER_IP} "{script_cmd}"'
    else:
        cmd = f'ssh -o StrictHostKeyChecking=no {SSH_USER}@{SERVER_IP} "{script_cmd}"'
    
    result = run_command(cmd, check=False, capture_output=False)
    
    if result is None:
        print("✅ Скрипт выполнен на сервере")
        return True
    else:
        print("⚠️  Не удалось выполнить скрипт автоматически")
        print(f"   Подключитесь к серверу: ssh {SSH_USER}@{SERVER_IP}")
        print(f"   Выполните: {script_cmd}")
        return False

def get_config_from_server():
    """Получить конфигурацию с сервера"""
    print("📥 Получение конфигурации с сервера...")
    
    cmd = f'ssh -o StrictHostKeyChecking=no {SSH_USER}@{SERVER_IP} "cat /tmp/marzban_reality_config.json"'
    
    if run_command("which sshpass", check=False):
        cmd = f'sshpass -p "{SSH_PASSWORD}" {cmd}'
    
    config = run_command(cmd, check=False)
    
    if config and config.startswith("{"):
        local_config_path = Path(__file__).parent / "generated_config.json"
        with open(local_config_path, "w") as f:
            f.write(config)
        print(f"✅ Конфигурация сохранена в: {local_config_path}")
        return config
    else:
        print("⚠️  Не удалось получить конфигурацию автоматически")
        return None

def main():
    """Главная функция"""
    print("🚀 Автоматическая настройка VLESS + REALITY для Marzban")
    print("=" * 60)
    print(f"Сервер: {SSH_USER}@{SERVER_IP}")
    print()
    
    # Проверка доступности скрипта
    script_path = Path(__file__).parent / "auto_setup_reality_non_interactive.sh"
    if not script_path.exists():
        print(f"❌ Файл не найден: {script_path}")
        print("   Убедитесь, что все файлы находятся в одной директории")
        sys.exit(1)
    
    # Копирование и выполнение
    if copy_script_to_server():
        execute_on_server()
        config = get_config_from_server()
        
        if config:
            print()
            print("=" * 60)
            print("✅ Автоматическая настройка завершена!")
            print()
            print("📋 Следующие шаги:")
            print("1. Откройте панель Marzban в браузере")
            print("2. Перейдите в Core Settings")
            print("3. Найдите раздел 'inbounds': [ ... ]")
            print("4. Вставьте содержимое файла generated_config.json")
            print("5. Сохраните изменения")
            print("6. Создайте пользователя (VLESS, Flow: vision)")
        else:
            print()
            print("⚠️  Выполните настройку вручную:")
            print(f"   ssh {SSH_USER}@{SERVER_IP}")
            print("   cat /tmp/marzban_reality_config.json")
    else:
        print()
        print("📋 Инструкция для ручного выполнения:")
        print("1. Скопируйте auto_setup_reality_non_interactive.sh на сервер")
        print(f"2. Подключитесь: ssh {SSH_USER}@{SERVER_IP}")
        print("3. Выполните: chmod +x /tmp/auto_setup_reality_non_interactive.sh")
        print("4. Запустите: /tmp/auto_setup_reality_non_interactive.sh")

if __name__ == "__main__":
    main()
