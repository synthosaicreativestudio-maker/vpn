#!/usr/bin/env python3
"""
Полностью автоматическая настройка VLESS + REALITY
Использует paramiko для SSH подключения
"""

import sys
import subprocess
from pathlib import Path

SERVER_IP = "37.1.212.51"
SSH_USER = "root"
SSH_PASSWORD = "LEJ6U5chSK"
SCRIPT_DIR = Path(__file__).parent
SCRIPT_NAME = "auto_setup_reality_non_interactive.sh"

def install_paramiko():
    """Установить paramiko если нужно"""
    try:
        importlib_find = __import__('importlib.util').util.find_spec
        if importlib_find('paramiko'):
            return True
        raise ImportError
    except (ImportError, AttributeError):
        print("📦 Установка paramiko...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "paramiko", "-q"])
            return True
        except Exception:
            print("❌ Не удалось установить paramiko")
            return False

def execute_remote_command(ssh, command):
    """Выполнить команду на удаленном сервере"""
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    return exit_status, output, error

def main():
    print("🚀 Автоматическая настройка VLESS + REALITY для Marzban")
    print("=" * 60)
    print(f"Сервер: {SSH_USER}@{SERVER_IP}")
    print()
    
    # Установка paramiko
    if not install_paramiko():
        print("⚠️  Используйте ручной метод из EXECUTE_NOW.md")
        sys.exit(1)
    
    import paramiko
    
    # Подключение к серверу
    print("🔌 Подключение к серверу...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_IP, username=SSH_USER, password=SSH_PASSWORD, timeout=10)
        print("✅ Подключено")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        print("⚠️  Используйте ручной метод из EXECUTE_NOW.md")
        sys.exit(1)
    
    # Копирование скрипта
    print("📤 Копирование скрипта на сервер...")
    script_path = SCRIPT_DIR / SCRIPT_NAME
    
    if not script_path.exists():
        print(f"❌ Файл не найден: {script_path}")
        sys.exit(1)
    
    try:
        sftp = ssh.open_sftp()
        sftp.put(str(script_path), f"/tmp/{SCRIPT_NAME}")
        sftp.close()
        print("✅ Скрипт скопирован")
    except Exception as e:
        print(f"❌ Ошибка копирования: {e}")
        ssh.close()
        sys.exit(1)
    
    # Выполнение скрипта
    print("🚀 Запуск настройки на сервере...")
    remote_cmd = f"chmod +x /tmp/{SCRIPT_NAME} && /tmp/{SCRIPT_NAME}"
    
    try:
        exit_status, output, error = execute_remote_command(ssh, remote_cmd)
        
        # Вывод результатов
        if output:
            print(output)
        if error and exit_status != 0:
            print(f"⚠️  Ошибки: {error}")
        
        if exit_status == 0:
            print("✅ Настройка выполнена")
        else:
            print(f"⚠️  Скрипт завершился с кодом {exit_status}")
    except Exception as e:
        print(f"❌ Ошибка выполнения: {e}")
        ssh.close()
        sys.exit(1)
    
    # Получение конфигурации
    print("📥 Получение конфигурации...")
    try:
        sftp = ssh.open_sftp()
        local_config = SCRIPT_DIR / "generated_config.json"
        sftp.get("/tmp/marzban_reality_config.json", str(local_config))
        sftp.close()
        
        if local_config.exists():
            print(f"✅ Конфигурация сохранена в: {local_config}")
            print()
            print("📋 JSON конфигурация:")
            print(local_config.read_text())
            print()
            print("📋 Следующие шаги:")
            print("1. Откройте панель Marzban: http://37.1.212.51:62050")
            print("2. Перейдите в Core Settings")
            print("3. Найдите раздел 'inbounds': [ ... ]")
            print("4. Вставьте JSON из generated_config.json")
            print("5. Сохраните изменения")
            print("6. Создайте пользователя (VLESS, Flow: vision)")
            print("7. Подключитесь через Amnezia VPN")
        else:
            print("⚠️  Файл не был создан")
    except Exception as e:
        print(f"⚠️  Не удалось получить конфигурацию: {e}")
        print("   Выполните вручную:")
        print(f"   scp {SSH_USER}@{SERVER_IP}:/tmp/marzban_reality_config.json {SCRIPT_DIR}/generated_config.json")
    
    ssh.close()
    print()
    print("✅ Готово!")

if __name__ == "__main__":
    main()
