#!/bin/bash

# Полностью автоматическая настройка VLESS + REALITY на удаленном сервере
# Использование: ./remote_setup.sh [SSH_USER] [SSH_HOST] [SSH_PASSWORD]
# Или: ./remote_setup.sh root@37.1.212.51

set -e

# Параметры подключения
if [ $# -eq 1 ]; then
    # Формат: user@host
    SSH_TARGET="$1"
elif [ $# -eq 3 ]; then
    SSH_USER="$1"
    SSH_HOST="$2"
    SSH_PASSWORD="$3"
    SSH_TARGET="${SSH_USER}@${SSH_HOST}"
else
    echo "Использование: $0 [user@host]"
    echo "Или: $0 [user] [host] [password]"
    echo "Пример: $0 root@37.1.212.51"
    exit 1
fi

echo "🚀 Автоматическая настройка VLESS + REALITY на удаленном сервере"
echo "=================================================="
echo "Сервер: $SSH_TARGET"
echo ""

# Проверка наличия sshpass для автоматического ввода пароля
if [ -n "$SSH_PASSWORD" ] && ! command -v sshpass &> /dev/null; then
    echo "⚠️  sshpass не установлен. Установка..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass
        else
            echo "❌ Ошибка: brew не установлен. Установите sshpass вручную или используйте SSH ключи"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y sshpass || sudo yum install -y sshpass
    fi
fi

# Копирование скрипта на сервер
echo "📤 Копирование скрипта на сервер..."
if [ -n "$SSH_PASSWORD" ]; then
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no auto_setup_reality.sh "$SSH_TARGET:/tmp/"
else
    scp -o StrictHostKeyChecking=no auto_setup_reality.sh "$SSH_TARGET:/tmp/"
fi

echo "✅ Скрипт скопирован"
echo ""

# Запуск скрипта на сервере
echo "🚀 Запуск автоматической настройки на сервере..."
if [ -n "$SSH_PASSWORD" ]; then
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_TARGET" << 'ENDSSH'
chmod +x /tmp/auto_setup_reality.sh
/tmp/auto_setup_reality.sh
ENDSSH
else
    ssh -o StrictHostKeyChecking=no "$SSH_TARGET" << 'ENDSSH'
chmod +x /tmp/auto_setup_reality.sh
/tmp/auto_setup_reality.sh
ENDSSH
fi

echo ""
echo "✅ Настройка завершена на сервере!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Подключитесь к серверу: ssh $SSH_TARGET"
echo "2. Просмотрите конфигурацию: cat /tmp/marzban_reality_config.json"
echo "3. Скопируйте JSON и вставьте в Marzban → Core Settings → inbounds"
echo "4. Создайте пользователя в Marzban (VLESS, Flow: vision)"
echo ""
