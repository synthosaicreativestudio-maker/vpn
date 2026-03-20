#!/bin/bash

# Диагностика VPN сервера
SERVER_IP="37.1.212.51"
SSH_PASS="LEJ6U5chSK"

echo "=========================================="
echo "🔍 ДИАГНОСТИКА VPN СЕРВЕРА"
echo "=========================================="
echo ""

# 1. Проверка Docker контейнеров
echo "1️⃣  Проверка Docker контейнеров:"
echo "----------------------------------------"
sshpass -p "$SSH_PASS" ssh -n -o StrictHostKeyChecking=no root@$SERVER_IP "docker ps | grep marzban" || echo "❌ Контейнер не найден или не запущен"
echo ""

# 2. Проверка порта 443
echo "2️⃣  Проверка порта 443:"
echo "----------------------------------------"
sshpass -p "$SSH_PASS" ssh -n -o StrictHostKeyChecking=no root@$SERVER_IP "netstat -tlnp | grep 443" || echo "❌ Порт 443 не слушается"
echo ""

# 3. Проверка логов Marzban
echo "3️⃣  Последние логи Marzban (последние 50 строк):"
echo "----------------------------------------"
sshpass -p "$SSH_PASS" ssh -n -o StrictHostKeyChecking=no root@$SERVER_IP "docker logs marzban-marzban-1 --tail 50 2>&1" || echo "❌ Не удалось получить логи"
echo ""

# 4. Проверка файрвола
echo "4️⃣  Проверка файрвола (UFW):"
echo "----------------------------------------"
sshpass -p "$SSH_PASS" ssh -n -o StrictHostKeyChecking=no root@$SERVER_IP "ufw status | grep 443" || echo "⚠️  Порт 443 не найден в правилах UFW"
echo ""

# 5. Проверка конфигурации Xray
echo "5️⃣  Проверка конфигурации VLESS Reality:"
echo "----------------------------------------"
sshpass -p "$SSH_PASS" ssh -n -o StrictHostKeyChecking=no root@$SERVER_IP "cat /var/lib/marzban/xray_config.json 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -A 20 'VLESS-Reality' || echo '❌ Конфигурация не найдена или некорректна'"
echo ""

# 6. Проверка статуса Docker сервиса
echo "6️⃣  Статус Docker сервиса:"
echo "----------------------------------------"
sshpass -p "$SSH_PASS" ssh -n -o StrictHostKeyChecking=no root@$SERVER_IP "systemctl status docker --no-pager | head -10" || echo "❌ Docker не запущен"
echo ""

# 7. Проверка всех Docker контейнеров
echo "7️⃣  Все Docker контейнеры:"
echo "----------------------------------------"
sshpass -p "$SSH_PASS" ssh -n -o StrictHostKeyChecking=no root@$SERVER_IP "docker ps -a" || echo "❌ Не удалось получить список контейнеров"
echo ""

echo "=========================================="
echo "✅ Диагностика завершена"
echo "=========================================="
