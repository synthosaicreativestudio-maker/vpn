#!/bin/bash

# ФИНАЛЬНЫЙ АВТОМАТИЧЕСКИЙ СКРИПТ
# Запустите этот скрипт для полной автоматизации
# Использование: ./DO_IT_NOW.sh

set -e

SERVER_IP="37.1.212.51"
SSH_USER="root"
SSH_PASSWORD="LEJ6U5chSK"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="auto_setup_reality_non_interactive.sh"

echo "🚀 АВТОМАТИЧЕСКАЯ НАСТРОЙКА VLESS + REALITY"
echo "=================================================="
echo "Сервер: $SSH_USER@$SERVER_IP"
echo ""

# Проверка наличия необходимых инструментов
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ $1 не установлен"
        return 1
    fi
    return 0
}

# Установка sshpass если нужно
if ! check_tool sshpass; then
    echo "📦 Попытка установки sshpass..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install hudochenkov/sshpass/sshpass 2>/dev/null || true
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y sshpass 2>/dev/null || \
        sudo yum install -y sshpass 2>/dev/null || true
    fi
fi

# Функция для выполнения команд с паролем
run_ssh() {
    local cmd="$1"
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$SSH_USER@$SERVER_IP" "$cmd" 2>&1
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$SSH_USER@$SERVER_IP" "$cmd" 2>&1
    fi
}

run_scp() {
    local src="$1"
    local dst="$2"
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$src" "$dst" 2>&1
    else
        scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$src" "$dst" 2>&1
    fi
}

# Шаг 1: Копирование скрипта
echo "📤 Шаг 1: Копирование скрипта на сервер..."
if run_scp "$SCRIPT_DIR/$SCRIPT_NAME" "$SSH_USER@$SERVER_IP:/tmp/" > /dev/null 2>&1; then
    echo "✅ Скрипт скопирован"
else
    echo "❌ Не удалось скопировать скрипт"
    echo "   Выполните вручную:"
    echo "   scp $SCRIPT_DIR/$SCRIPT_NAME $SSH_USER@$SERVER_IP:/tmp/"
    exit 1
fi

# Шаг 2: Выполнение скрипта на сервере
echo "🚀 Шаг 2: Запуск настройки на сервере..."
REMOTE_CMD="chmod +x /tmp/$SCRIPT_NAME && /tmp/$SCRIPT_NAME"

if run_ssh "$REMOTE_CMD"; then
    echo "✅ Настройка выполнена на сервере"
else
    echo "⚠️  Возможны ошибки при выполнении"
    echo "   Проверьте подключение и выполните вручную:"
    echo "   ssh $SSH_USER@$SERVER_IP"
    echo "   $REMOTE_CMD"
fi

# Шаг 3: Получение конфигурации
echo "📥 Шаг 3: Получение конфигурации..."
if run_scp "$SSH_USER@$SERVER_IP:/tmp/marzban_reality_config.json" "$SCRIPT_DIR/generated_config.json" > /dev/null 2>&1; then
    if [ -f "$SCRIPT_DIR/generated_config.json" ]; then
        echo "✅ Конфигурация сохранена в generated_config.json"
        echo ""
        echo "📋 JSON конфигурация:"
        echo "===================="
        cat "$SCRIPT_DIR/generated_config.json"
        echo ""
        echo "===================="
        echo ""
        echo "📋 СЛЕДУЮЩИЕ ШАГИ:"
        echo "1. Откройте панель Marzban: http://$SERVER_IP:62050"
        echo "2. Перейдите в Core Settings"
        echo "3. Найдите раздел 'inbounds': [ ... ]"
        echo "4. Вставьте JSON из generated_config.json выше"
        echo "5. Сохраните изменения"
        echo "6. Создайте пользователя:"
        echo "   - Protocol: VLESS"
        echo "   - Flow: vision"
        echo "   - Inbound: VLESS-Reality-Microsoft"
        echo "7. Скопируйте ссылку vless://..."
        echo "8. Подключитесь через Amnezia VPN"
    else
        echo "⚠️  Файл не был создан"
    fi
else
    echo "⚠️  Не удалось получить конфигурацию автоматически"
    echo "   Выполните вручную:"
    echo "   scp $SSH_USER@$SERVER_IP:/tmp/marzban_reality_config.json $SCRIPT_DIR/generated_config.json"
    echo ""
    echo "   Или подключитесь к серверу:"
    echo "   ssh $SSH_USER@$SERVER_IP"
    echo "   cat /tmp/marzban_reality_config.json"
fi

echo ""
echo "✅ Готово!"
