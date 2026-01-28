#!/bin/bash

# Полностью автоматический скрипт настройки VLESS + REALITY
# Использование: ./run_setup.sh
# Этот скрипт выполнит все действия автоматически

set -e

SERVER_IP="37.1.212.51"
SSH_USER="root"
SSH_PASSWORD="LEJ6U5chSK"  # Из PROXY_SETTINGS.md

echo "🚀 Автоматическая настройка VLESS + REALITY для Marzban"
echo "=================================================="
echo "Сервер: $SSH_USER@$SERVER_IP"
echo ""

# Проверка наличия sshpass
if ! command -v sshpass &> /dev/null; then
    echo "📦 Установка sshpass..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass 2>/dev/null || echo "⚠️  Не удалось установить sshpass автоматически"
        else
            echo "❌ brew не установлен. Установите sshpass вручную:"
            echo "   brew install hudochenkov/sshpass/sshpass"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y sshpass 2>/dev/null || \
        sudo yum install -y sshpass 2>/dev/null || \
        echo "⚠️  Не удалось установить sshpass автоматически"
    fi
fi

# Копирование скрипта на сервер
echo "📤 Копирование скрипта на сервер..."
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/auto_setup_reality_non_interactive.sh"

if [ -f "$SCRIPT_PATH" ]; then
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
            "$SCRIPT_PATH" "$SSH_USER@$SERVER_IP:/tmp/" 2>/dev/null
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
            "$SCRIPT_PATH" "$SSH_USER@$SERVER_IP:/tmp/" 2>/dev/null
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ Скрипт скопирован на сервер"
    else
        echo "⚠️  Не удалось скопировать скрипт автоматически"
        echo "   Выполните вручную: scp $SCRIPT_PATH $SSH_USER@$SERVER_IP:/tmp/"
        exit 1
    fi
else
    echo "❌ Файл не найден: $SCRIPT_PATH"
    exit 1
fi

# Выполнение скрипта на сервере
echo "🚀 Запуск автоматической настройки на сервере..."
REMOTE_CMD="chmod +x /tmp/auto_setup_reality_non_interactive.sh && /tmp/auto_setup_reality_non_interactive.sh"

if command -v sshpass &> /dev/null; then
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "$SSH_USER@$SERVER_IP" "$REMOTE_CMD" 2>&1
else
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "$SSH_USER@$SERVER_IP" "$REMOTE_CMD" 2>&1
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Настройка выполнена на сервере!"
    echo ""
    
    # Получение конфигурации
    echo "📥 Получение конфигурации с сервера..."
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no \
            "$SSH_USER@$SERVER_IP:/tmp/marzban_reality_config.json" \
            "./generated_config.json" 2>/dev/null
    else
        scp -o StrictHostKeyChecking=no \
            "$SSH_USER@$SERVER_IP:/tmp/marzban_reality_config.json" \
            "./generated_config.json" 2>/dev/null
    fi
    
    if [ -f "./generated_config.json" ]; then
        echo "✅ Конфигурация сохранена в: ./generated_config.json"
        echo ""
        echo "📋 Следующие шаги:"
        echo "1. Откройте панель Marzban в браузере"
        echo "2. Перейдите в Core Settings"
        echo "3. Найдите раздел 'inbounds': [ ... ]"
        echo "4. Вставьте содержимое файла generated_config.json"
        echo "5. Сохраните изменения"
        echo "6. Создайте пользователя (VLESS, Flow: vision)"
        echo ""
        echo "📄 Содержимое generated_config.json:"
        cat ./generated_config.json
    else
        echo "⚠️  Не удалось получить конфигурацию автоматически"
        echo "   Выполните вручную:"
        echo "   ssh $SSH_USER@$SERVER_IP"
        echo "   cat /tmp/marzban_reality_config.json"
    fi
else
    echo ""
    echo "⚠️  Не удалось выполнить настройку автоматически"
    echo ""
    echo "📋 Выполните вручную:"
    echo "1. Подключитесь к серверу: ssh $SSH_USER@$SERVER_IP"
    echo "2. Скопируйте скрипт: scp $SCRIPT_PATH $SSH_USER@$SERVER_IP:/tmp/"
    echo "3. Выполните: chmod +x /tmp/auto_setup_reality_non_interactive.sh"
    echo "4. Запустите: /tmp/auto_setup_reality_non_interactive.sh"
fi
