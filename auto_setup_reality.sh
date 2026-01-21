#!/bin/bash

# Автоматическая настройка VLESS + REALITY для Marzban
# Использование: ./auto_setup_reality.sh
# Запускать на VPS сервере, где установлен Marzban

set -e

echo "🚀 Автоматическая настройка VLESS + REALITY для Marzban"
echo "=================================================="
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Данные сервера из PROXY_SETTINGS.md
SERVER_IP="37.1.212.51"
TINYPROXY_PORT="8080"
VLESS_PORT="443"
SNI_DOMAIN="www.microsoft.com"

echo "📋 Параметры сервера:"
echo "   IP: $SERVER_IP"
echo "   TinyProxy порт: $TINYPROXY_PORT (не трогаем)"
echo "   VLESS порт: $VLESS_PORT"
echo "   SNI домен: $SNI_DOMAIN"
echo ""

# Шаг 1: Поиск контейнера Marzban
echo "🔍 Шаг 1: Поиск контейнера Marzban..."
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -i marzban | head -n 1)

if [ -z "$CONTAINER_NAME" ]; then
    echo -e "${RED}❌ Ошибка: Контейнер Marzban не найден${NC}"
    echo "Доступные контейнеры:"
    docker ps --format "{{.Names}}"
    exit 1
fi

echo -e "${GREEN}✅ Найден контейнер: $CONTAINER_NAME${NC}"
echo ""

# Шаг 2: Генерация ключей REALITY
echo "🔑 Шаг 2: Генерация ключей REALITY..."
KEYS_OUTPUT=$(docker exec "$CONTAINER_NAME" xray x25519)

# Извлечение ключей из вывода
PRIVATE_KEY=$(echo "$KEYS_OUTPUT" | grep -i "Private:" | awk '{print $2}')
PUBLIC_KEY=$(echo "$KEYS_OUTPUT" | grep -i "Public:" | awk '{print $2}')

if [ -z "$PRIVATE_KEY" ] || [ -z "$PUBLIC_KEY" ]; then
    echo -e "${RED}❌ Ошибка: Не удалось извлечь ключи${NC}"
    echo "Вывод команды:"
    echo "$KEYS_OUTPUT"
    exit 1
fi

echo -e "${GREEN}✅ Ключи сгенерированы:${NC}"
echo "   Private Key: ${PRIVATE_KEY:0:20}..."
echo "   Public Key:  ${PUBLIC_KEY:0:20}..."
echo ""

# Шаг 3: Создание JSON конфигурации
echo "📝 Шаг 3: Создание JSON конфигурации..."

CONFIG_FILE="/tmp/marzban_reality_config.json"

cat > "$CONFIG_FILE" <<EOF
{
  "tag": "VLESS-Reality-Microsoft",
  "protocol": "vless",
  "listen": "0.0.0.0",
  "port": $VLESS_PORT,
  "settings": {
    "clients": [],
    "decryption": "none"
  },
  "streamSettings": {
    "network": "tcp",
    "security": "reality",
    "realitySettings": {
      "show": false,
      "dest": "$SNI_DOMAIN:443",
      "xver": 0,
      "serverNames": [
        "$SNI_DOMAIN",
        "microsoft.com"
      ],
      "privateKey": "$PRIVATE_KEY",
      "shortIds": [
        ""
      ],
      "minClientVer": "",
      "maxClientVer": "",
      "maxTimeDiff": 0,
      "publicKey": "$PUBLIC_KEY"
    },
    "tcpSettings": {
      "acceptProxyProtocol": false,
      "header": {
        "type": "none"
      }
    }
  },
  "sniffing": {
    "enabled": true,
    "destOverride": [
      "http",
      "tls"
    ]
  }
}
EOF

echo -e "${GREEN}✅ Конфигурация создана: $CONFIG_FILE${NC}"
echo ""

# Шаг 4: Сохранение ключей в файл для справки
KEYS_FILE="/tmp/reality_keys.txt"
cat > "$KEYS_FILE" <<EOF
# Ключи REALITY для Marzban
# Сгенерировано: $(date)

Private Key: $PRIVATE_KEY
Public Key:  $PUBLIC_KEY

SNI Domain:  $SNI_DOMAIN
Port:        $VLESS_PORT
Server IP:   $SERVER_IP
EOF

echo -e "${GREEN}✅ Ключи сохранены в: $KEYS_FILE${NC}"
echo ""

# Шаг 5: Проверка порта 443
echo "🔍 Шаг 5: Проверка порта $VLESS_PORT..."
if lsof -Pi :$VLESS_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Внимание: Порт $VLESS_PORT уже занят${NC}"
    echo "   Проверьте, не используется ли он другим сервисом"
    lsof -i :$VLESS_PORT
    echo ""
    read -p "Продолжить? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ Порт $VLESS_PORT свободен${NC}"
fi
echo ""

# Шаг 6: Проверка файрвола
echo "🔍 Шаг 6: Проверка файрвола..."
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "$VLESS_PORT"; then
        echo -e "${GREEN}✅ Порт $VLESS_PORT уже открыт в UFW${NC}"
    else
        echo -e "${YELLOW}⚠️  Порт $VLESS_PORT не открыт в UFW${NC}"
        read -p "Открыть порт $VLESS_PORT в UFW? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo ufw allow $VLESS_PORT/tcp
            echo -e "${GREEN}✅ Порт $VLESS_PORT открыт${NC}"
        fi
    fi
elif command -v firewall-cmd &> /dev/null; then
    if sudo firewall-cmd --list-ports | grep -q "$VLESS_PORT"; then
        echo -e "${GREEN}✅ Порт $VLESS_PORT уже открыт в firewalld${NC}"
    else
        echo -e "${YELLOW}⚠️  Порт $VLESS_PORT не открыт в firewalld${NC}"
        read -p "Открыть порт $VLESS_PORT в firewalld? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo firewall-cmd --add-port=$VLESS_PORT/tcp --permanent
            sudo firewall-cmd --reload
            echo -e "${GREEN}✅ Порт $VLESS_PORT открыт${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Файрвол не найден (UFW или firewalld)${NC}"
    echo "   Убедитесь, что порт $VLESS_PORT открыт вручную"
fi
echo ""

# Итоговая информация
echo "=================================================="
echo -e "${GREEN}✅ Настройка завершена!${NC}"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1. Откройте панель Marzban в браузере"
echo "2. Перейдите в Core Settings"
echo "3. Найдите раздел 'inbounds': [ ... ]"
echo "4. Вставьте содержимое файла: $CONFIG_FILE"
echo ""
echo "   Или скопируйте JSON ниже:"
echo ""
cat "$CONFIG_FILE"
echo ""
echo "5. Сохраните изменения в Marzban"
echo "6. Создайте пользователя:"
echo "   - Protocol: VLESS"
echo "   - Flow: vision (xtls-rprx-vision)"
echo "   - Inbound: VLESS-Reality-Microsoft"
echo ""
echo "7. Скопируйте ссылку vless:// из Marzban"
echo "8. Подключитесь через Amnezia VPN"
echo ""
echo "📝 Ключи сохранены в: $KEYS_FILE"
echo "📝 Конфигурация в: $CONFIG_FILE"
echo ""
echo "🔗 Формат ссылки vless:// будет примерно таким:"
echo "vless://UUID@$SERVER_IP:$VLESS_PORT?type=tcp&security=reality&sni=$SNI_DOMAIN&pbk=$PUBLIC_KEY&fp=chrome&flow=xtls-rprx-vision#VLESS-Reality"
echo ""
echo -e "${GREEN}Готово! 🚀${NC}"
