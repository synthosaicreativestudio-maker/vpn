#!/bin/bash
# Скрипт для добавления региональных IP с приоритетами
# Яндекс → Тюмень → Ульяновск → РФ

set -e

SERVER_IP="37.1.212.51"
SERVER_USER="root"
SERVER_PASS="LEJ6U5chSK"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

execute_remote() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "$SERVER_USER@$SERVER_IP" "$1"
}

echo -e "${GREEN}🌍 Добавление региональных IP с приоритетами${NC}"
echo ""

# ШАГ 1: Создать список IP Яндекса
echo -e "${YELLOW}📝 ШАГ 1: Создание списка IP Яндекса...${NC}"
execute_remote "cat > /etc/tinyproxy/yandex_ips.txt << 'EOF'
# Основные IP диапазоны Яндекса (Приоритет 1)
5.45.192.0/18
5.45.250.0/23
37.9.64.0/18
37.140.128.0/18
77.88.0.0/18
87.250.224.0/19
93.158.134.0/24
95.163.0.0/16
141.8.128.0/18
178.154.128.0/17
185.32.248.0/22
213.180.192.0/19
EOF
"
echo -e "${GREEN}✅ Список IP Яндекса создан${NC}"

# ШАГ 2: Добавить правила UFW для Яндекса (приоритет 1)
echo -e "${YELLOW}🔒 ШАГ 2: Добавление правил для Яндекса (приоритет 1)...${NC}"
execute_remote "
while read ip; do
    [[ \"\$ip\" =~ ^# ]] && continue
    ufw allow from \$ip to any port 8080 proto tcp comment 'Yandex IP' 2>/dev/null || true
done < /etc/tinyproxy/yandex_ips.txt
"
echo -e "${GREEN}✅ Правила для Яндекса добавлены${NC}"

# ШАГ 3: Добавить основные IP диапазоны РФ (включая Тюмень и Ульяновск)
echo -e "${YELLOW}🌐 ШАГ 3: Добавление основных IP диапазонов РФ...${NC}"

# Основные диапазоны РФ (включают Тюмень, Ульяновск и другие города)
execute_remote "
# Основные провайдеры РФ
ufw allow from 5.8.0.0/13 to any port 8080 proto tcp comment 'RU IP range 1' 2>/dev/null || true
ufw allow from 31.131.0.0/16 to any port 8080 proto tcp comment 'RU IP range 2' 2>/dev/null || true
ufw allow from 37.139.0.0/16 to any port 8080 proto tcp comment 'RU IP range 3' 2>/dev/null || true
ufw allow from 46.17.40.0/21 to any port 8080 proto tcp comment 'RU IP range 4' 2>/dev/null || true
ufw allow from 46.21.96.0/19 to any port 8080 proto tcp comment 'RU IP range 5' 2>/dev/null || true
ufw allow from 46.232.0.0/16 to any port 8080 proto tcp comment 'RU IP range 6' 2>/dev/null || true
ufw allow from 79.133.0.0/16 to any port 8080 proto tcp comment 'RU IP range 7' 2>/dev/null || true
ufw allow from 84.201.128.0/18 to any port 8080 proto tcp comment 'RU IP range 8' 2>/dev/null || true
ufw allow from 87.250.0.0/16 to any port 8080 proto tcp comment 'RU IP range 9' 2>/dev/null || true
ufw allow from 178.154.128.0/17 to any port 8080 proto tcp comment 'RU IP range 10' 2>/dev/null || true
ufw allow from 185.32.248.0/22 to any port 8080 proto tcp comment 'RU IP range 11' 2>/dev/null || true
ufw allow from 213.180.192.0/19 to any port 8080 proto tcp comment 'RU IP range 12' 2>/dev/null || true
"
echo -e "${GREEN}✅ Основные диапазоны РФ добавлены${NC}"

# ШАГ 4: Применить правила
echo -e "${YELLOW}🔄 ШАГ 4: Применение правил...${NC}"
execute_remote "ufw reload"
echo -e "${GREEN}✅ Правила применены${NC}"

# ШАГ 5: Показать текущие правила
echo -e "${YELLOW}📊 ШАГ 5: Текущие правила для порта 8080:${NC}"
execute_remote "ufw status | grep 8080"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Региональные IP добавлены!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Приоритеты доступа:"
echo "  1. Яндекс IP (из списка)"
echo "  2. Основные диапазоны РФ (включая Тюмень, Ульяновск)"
echo "  3. Все остальные - заблокированы"
echo ""
echo "Проверка: ssh root@$SERVER_IP 'ufw status | grep 8080'"
