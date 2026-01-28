#!/bin/bash

# Финальный автоматический скрипт настройки
# Использует различные методы для подключения

set -e

SERVER_IP="37.1.212.51"
SSH_USER="root"
SSH_PASSWORD="LEJ6U5chSK"
SCRIPT_DIR="/Users/verakoroleva/Desktop/vpn"
SCRIPT_NAME="auto_setup_reality_non_interactive.sh"

echo "🚀 Автоматическая настройка VLESS + REALITY для Marzban"
echo "=================================================="
echo "Сервер: $SSH_USER@$SERVER_IP"
echo ""

# Функция для выполнения команды с паролем
execute_with_password() {
    local cmd="$1"
    
    # Попытка 1: sshpass
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" $cmd
        return $?
    fi
    
    # Попытка 2: expect
    if command -v expect &> /dev/null; then
        expect << EOF
set timeout 30
spawn $cmd
expect {
    "password:" { send "$SSH_PASSWORD\r"; exp_continue }
    "yes/no" { send "yes\r"; exp_continue }
    eof
}
EOF
        return $?
    fi
    
    # Попытка 3: обычный SSH (если настроены ключи)
    $cmd
    return $?
}

# Копирование скрипта
echo "📤 Копирование скрипта на сервер..."
if execute_with_password "scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 $SCRIPT_DIR/$SCRIPT_NAME $SSH_USER@$SERVER_IP:/tmp/" 2>/dev/null; then
    echo "✅ Скрипт скопирован"
else
    echo "⚠️  Автоматическое копирование не удалось"
    echo "   Выполните вручную:"
    echo "   scp $SCRIPT_DIR/$SCRIPT_NAME $SSH_USER@$SERVER_IP:/tmp/"
    exit 1
fi

# Выполнение скрипта на сервере
echo "🚀 Запуск настройки на сервере..."
REMOTE_CMD="chmod +x /tmp/$SCRIPT_NAME && /tmp/$SCRIPT_NAME"

if execute_with_password "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $SSH_USER@$SERVER_IP '$REMOTE_CMD'" 2>&1; then
    echo "✅ Настройка выполнена на сервере"
else
    echo "⚠️  Не удалось выполнить автоматически"
    echo "   Выполните вручную:"
    echo "   ssh $SSH_USER@$SERVER_IP"
    echo "   $REMOTE_CMD"
    exit 1
fi

# Получение конфигурации
echo "📥 Получение конфигурации..."
if execute_with_password "scp -o StrictHostKeyChecking=no $SSH_USER@$SERVER_IP:/tmp/marzban_reality_config.json $SCRIPT_DIR/generated_config.json" 2>/dev/null; then
    if [ -f "$SCRIPT_DIR/generated_config.json" ]; then
        echo "✅ Конфигурация сохранена в generated_config.json"
        echo ""
        echo "📋 JSON конфигурация:"
        cat "$SCRIPT_DIR/generated_config.json"
        echo ""
        echo "📋 Следующие шаги:"
        echo "1. Откройте панель Marzban: http://$SERVER_IP:62050"
        echo "2. Перейдите в Core Settings"
        echo "3. Найдите раздел 'inbounds': [ ... ]"
        echo "4. Вставьте JSON из generated_config.json"
        echo "5. Сохраните изменения"
        echo "6. Создайте пользователя (VLESS, Flow: vision)"
        echo "7. Подключитесь через Amnezia VPN"
    else
        echo "⚠️  Файл не был скопирован"
    fi
else
    echo "⚠️  Не удалось получить конфигурацию автоматически"
    echo "   Выполните вручную:"
    echo "   scp $SSH_USER@$SERVER_IP:/tmp/marzban_reality_config.json $SCRIPT_DIR/generated_config.json"
fi

echo ""
echo "✅ Готово!"
