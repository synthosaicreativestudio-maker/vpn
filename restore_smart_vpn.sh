#!/bin/bash
# Скрипт восстановления Smart-VPN с маскировкой под Yandex
# Дата: 21.01.2026

set -e

SERVER_IP="37.1.212.51"
SSH_USER="root"
SSH_PASS="LEJ6U5chSK"

echo "🔧 Восстановление Smart-VPN (Reality + Yandex Masking)"
echo "=================================================="

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для выполнения команд на сервере
run_remote() {
    sshpass -p "$SSH_PASS" ssh -T -o StrictHostKeyChecking=no "${SSH_USER}@${SERVER_IP}" "$1"
}

# Функция для копирования файлов на сервер
copy_to_server() {
    sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no "$1" "${SSH_USER}@${SERVER_IP}:$2"
}

echo -e "${YELLOW}Шаг 1: Проверка состояния Marzban...${NC}"
if run_remote "docker ps | grep -q marzban"; then
    echo -e "${GREEN}✅ Marzban контейнер работает${NC}"
else
    echo -e "${RED}❌ Marzban контейнер не найден${NC}"
    exit 1
fi

echo -e "${YELLOW}Шаг 2: Проверка конфигурации Xray...${NC}"
CURRENT_DEST=$(run_remote "cat /var/lib/marzban/xray_config.json | python3 -m json.tool | grep -A 5 'realitySettings' | grep 'dest' | head -1 | cut -d'\"' -f4")
if [ "$CURRENT_DEST" = "taxi.yandex.ru:443" ]; then
    echo -e "${GREEN}✅ Конфигурация Xray уже использует taxi.yandex.ru:443${NC}"
else
    echo -e "${YELLOW}⚠️  Текущий dest: $CURRENT_DEST${NC}"
    echo -e "${YELLOW}   Конфигурация будет обновлена${NC}"
fi

echo -e "${YELLOW}Шаг 3: Создание директории для шаблонов...${NC}"
run_remote "mkdir -p /var/lib/marzban/templates/clash"

echo -e "${YELLOW}Шаг 4: Загрузка шаблона подписки для Happ...${NC}"
copy_to_server "marzban_clash_template_happ.yaml" "/var/lib/marzban/templates/clash/smart-routing.yml"
echo -e "${GREEN}✅ Шаблон загружен${NC}"

echo -e "${YELLOW}Шаг 5: Обновление конфигурации .env...${NC}"
run_remote "cat >> /opt/marzban/.env << 'EOF'

# Smart-VPN Subscription Settings (Restored 21.01.2026)
CUSTOM_TEMPLATES_DIRECTORY=/var/lib/marzban/templates/
CLASH_SUBSCRIPTION_TEMPLATE=clash/smart-routing.yml
XRAY_SUBSCRIPTION_URL_PREFIX=https://37.1.212.51.sslip.io
SUB_PROFILE_TITLE=Smart VPN
SUB_UPDATE_INTERVAL=12
EOF"
echo -e "${GREEN}✅ Настройки .env обновлены${NC}"

echo -e "${YELLOW}Шаг 6: Обновление конфигурации Nginx...${NC}"
copy_to_server "nginx_marzban_happ.conf" "/tmp/nginx_marzban_happ.conf"
run_remote "cp /tmp/nginx_marzban_happ.conf /etc/nginx/sites-available/marzban && nginx -t && systemctl reload nginx"
echo -e "${GREEN}✅ Nginx конфигурация обновлена${NC}"

echo -e "${YELLOW}Шаг 7: Перезапуск Marzban...${NC}"
run_remote "cd /opt/marzban && docker compose restart"
sleep 5
echo -e "${GREEN}✅ Marzban перезапущен${NC}"

echo -e "${YELLOW}Шаг 8: Проверка работоспособности...${NC}"
if run_remote "docker ps | grep -q marzban"; then
    echo -e "${GREEN}✅ Marzban работает${NC}"
else
    echo -e "${RED}❌ Ошибка при запуске Marzban${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=================================================="
echo "✅ Восстановление завершено успешно!"
echo "==================================================${NC}"
echo ""
echo "📋 Проверка подписки:"
echo "curl -H 'User-Agent: Happ' https://37.1.212.51.sslip.io/sub/dmVyYSwxNzY4OTgzNjg4ehy8JKshw7/clash"
echo ""
echo "🔗 Параметры подключения:"
echo "  - Protocol: VLESS"
echo "  - Flow: xtls-rprx-vision"
echo "  - SNI: taxi.yandex.ru"
echo "  - Port: 443"
echo ""
