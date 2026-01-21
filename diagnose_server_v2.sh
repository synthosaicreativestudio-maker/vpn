#!/bin/bash

# Диагностика VPN сервера (версия 2)
SERVER_IP="37.1.212.51"
SSH_PASS="LEJ6U5chSK"

echo "=========================================="
echo "🔍 ДИАГНОСТИКА VPN СЕРВЕРА"
echo "=========================================="
echo ""

# Функция для выполнения SSH команд
ssh_cmd() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes root@$SERVER_IP "$1" 2>&1
}

# 1. Проверка доступности сервера
echo "1️⃣  Проверка доступности сервера:"
echo "----------------------------------------"
if ping -c 2 -W 2 $SERVER_IP > /dev/null 2>&1; then
    echo "✅ Сервер доступен (ping)"
else
    echo "⚠️  Сервер не отвечает на ping (может быть отключен ICMP)"
fi

# Проверка SSH
if ssh_cmd "echo 'test'" | grep -q "test"; then
    echo "✅ SSH подключение работает"
else
    echo "❌ SSH подключение не работает"
    echo "Вывод: $(ssh_cmd 'echo test')"
fi
echo ""

# 2. Проверка Docker контейнеров
echo "2️⃣  Проверка Docker контейнеров:"
echo "----------------------------------------"
DOCKER_OUTPUT=$(ssh_cmd "docker ps 2>&1")
if echo "$DOCKER_OUTPUT" | grep -q "marzban"; then
    echo "$DOCKER_OUTPUT" | grep marzban
    echo "✅ Контейнер Marzban найден"
else
    echo "❌ Контейнер Marzban не найден"
    echo "Вывод Docker ps:"
    echo "$DOCKER_OUTPUT" | head -20
fi
echo ""

# 3. Проверка порта 443
echo "3️⃣  Проверка порта 443:"
echo "----------------------------------------"
PORT_OUTPUT=$(ssh_cmd "netstat -tlnp 2>&1 | grep 443 || ss -tlnp 2>&1 | grep 443")
if [ -n "$PORT_OUTPUT" ]; then
    echo "$PORT_OUTPUT"
    echo "✅ Порт 443 слушается"
else
    echo "❌ Порт 443 не слушается"
fi
echo ""

# 4. Проверка логов Marzban
echo "4️⃣  Последние логи Marzban:"
echo "----------------------------------------"
LOG_OUTPUT=$(ssh_cmd "docker logs marzban-marzban-1 --tail 30 2>&1")
if [ -n "$LOG_OUTPUT" ] && ! echo "$LOG_OUTPUT" | grep -q "No such container"; then
    echo "$LOG_OUTPUT"
else
    echo "❌ Не удалось получить логи или контейнер не существует"
    echo "Вывод: $LOG_OUTPUT"
fi
echo ""

# 5. Проверка файрвола
echo "5️⃣  Проверка файрвола (UFW):"
echo "----------------------------------------"
UFW_OUTPUT=$(ssh_cmd "ufw status 2>&1")
echo "$UFW_OUTPUT"
if echo "$UFW_OUTPUT" | grep -q "443"; then
    echo "✅ Порт 443 найден в правилах UFW"
else
    echo "⚠️  Порт 443 не найден в правилах UFW"
fi
echo ""

# 6. Проверка статуса Docker
echo "6️⃣  Статус Docker сервиса:"
echo "----------------------------------------"
DOCKER_STATUS=$(ssh_cmd "systemctl is-active docker 2>&1")
if [ "$DOCKER_STATUS" = "active" ]; then
    echo "✅ Docker активен"
else
    echo "❌ Docker не активен: $DOCKER_STATUS"
fi
echo ""

# 7. Проверка конфигурации
echo "7️⃣  Проверка конфигурации Xray:"
echo "----------------------------------------"
CONFIG_CHECK=$(ssh_cmd "test -f /var/lib/marzban/xray_config.json && echo 'exists' || echo 'not found'")
if [ "$CONFIG_CHECK" = "exists" ]; then
    echo "✅ Файл конфигурации существует"
    VLESS_CHECK=$(ssh_cmd "grep -q 'VLESS-Reality' /var/lib/marzban/xray_config.json && echo 'found' || echo 'not found'")
    if [ "$VLESS_CHECK" = "found" ]; then
        echo "✅ VLESS Reality конфигурация найдена"
    else
        echo "❌ VLESS Reality конфигурация не найдена в файле"
    fi
else
    echo "❌ Файл конфигурации не найден"
fi
echo ""

echo "=========================================="
echo "✅ Диагностика завершена"
echo "=========================================="
