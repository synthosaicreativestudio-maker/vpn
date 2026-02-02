#!/bin/bash
# Автоматический скрипт для исправления ситуации с сервером
# Использование: ./auto_fix_server.sh YOUR_IP_ADDRESS

set -e  # Остановить при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка аргументов
if [ -z "$1" ]; then
    echo -e "${RED}❌ Ошибка: Не указан IP адрес${NC}"
    echo "Использование: $0 YOUR_IP_ADDRESS"
    echo "Пример: $0 123.45.67.89"
    exit 1
fi

USER_IP=$1
SERVER_IP="37.1.212.51"
SERVER_USER="root"
SERVER_PASS="LEJ6U5chSK"

echo -e "${GREEN}🚀 Начинаем исправление ситуации с сервером${NC}"
echo "IP пользователя: $USER_IP"
echo "IP сервера: $SERVER_IP"
echo ""

# Функция для выполнения команд на сервере
execute_remote() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "$SERVER_USER@$SERVER_IP" "$1"
}

# Функция для проверки подключения
check_connection() {
    echo -e "${YELLOW}🔍 Проверка подключения к серверу...${NC}"
    if execute_remote "echo 'Connection OK'" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Подключение успешно${NC}"
        return 0
    else
        echo -e "${RED}❌ Не удалось подключиться к серверу${NC}"
        return 1
    fi
}

# ШАГ 2: Резервная копия
step2_backup() {
    echo -e "${YELLOW}📦 ШАГ 2: Создание резервной копии...${NC}"
    execute_remote "cp /etc/tinyproxy/tinyproxy.conf /etc/tinyproxy/tinyproxy.conf.backup.\$(date +%Y%m%d) && echo 'Backup created'"
    echo -e "${GREEN}✅ Резервная копия создана${NC}"
}

# ШАГ 3: Закрыть доступ
step3_close_access() {
    echo -e "${YELLOW}🔒 ШАГ 3: Закрытие доступа к прокси...${NC}"
    
    # Разрешить доступ только для пользователя
    execute_remote "ufw allow from $USER_IP to any port 8080 proto tcp comment 'TinyProxy access'"
    
    # Заблокировать всех остальных
    execute_remote "ufw deny 8080/tcp"
    
    # Применить правила
    execute_remote "ufw reload"
    
    echo -e "${GREEN}✅ Доступ закрыт для всех, кроме $USER_IP${NC}"
}

# ШАГ 4: Ограничить подключения
step4_limit_connections() {
    echo -e "${YELLOW}🔢 ШАГ 4: Ограничение подключений до 20...${NC}"
    
    # Проверить и установить MaxClients
    execute_remote "
        if grep -q '^MaxClients' /etc/tinyproxy/tinyproxy.conf; then
            sed -i 's/^MaxClients.*/MaxClients 20/' /etc/tinyproxy/tinyproxy.conf
        else
            echo 'MaxClients 20' >> /etc/tinyproxy/tinyproxy.conf
        fi
    "
    
    # Перезапустить TinyProxy
    execute_remote "systemctl restart tinyproxy"
    
    echo -e "${GREEN}✅ Максимум подключений установлен: 20${NC}"
}

# ШАГ 5: Установить fail2ban
step5_install_fail2ban() {
    echo -e "${YELLOW}🛡️  ШАГ 5: Установка fail2ban...${NC}"
    
    # Обновить пакеты
    execute_remote "apt-get update -qq"
    
    # Установить fail2ban
    execute_remote "apt-get install -y fail2ban > /dev/null 2>&1"
    
    # Создать конфиг для TinyProxy
    execute_remote "cat > /etc/fail2ban/jail.d/tinyproxy.conf << 'EOF'
[tinyproxy]
enabled = true
port = 8080
filter = tinyproxy
logpath = /var/log/tinyproxy/tinyproxy.log
maxretry = 3
bantime = 3600
findtime = 600
EOF
"
    
    # Создать фильтр
    execute_remote "cat > /etc/fail2ban/filter.d/tinyproxy.conf << 'EOF'
[Definition]
failregex = ^.*\[WARNING\].*Connection from <HOST> refused.*$
            ^.*\[ERROR\].*Connection from <HOST> failed.*$
ignoreregex =
EOF
"
    
    # Перезапустить fail2ban
    execute_remote "systemctl restart fail2ban && systemctl enable fail2ban"
    
    echo -e "${GREEN}✅ fail2ban установлен и настроен${NC}"
}

# ШАГ 6: Ограничить память
step6_limit_memory() {
    echo -e "${YELLOW}💾 ШАГ 6: Ограничение памяти до 512 МБ...${NC}"
    
    # Создать override для systemd
    execute_remote "mkdir -p /etc/systemd/system/tinyproxy.service.d"
    execute_remote "cat > /etc/systemd/system/tinyproxy.service.d/override.conf << 'EOF'
[Service]
MemoryLimit=512M
CPUQuota=50%
TasksMax=50
EOF
"
    
    # Применить изменения
    execute_remote "systemctl daemon-reload && systemctl restart tinyproxy"
    
    echo -e "${GREEN}✅ Память ограничена до 512 МБ${NC}"
}

# ШАГ 7: Включить логирование
step7_enable_logging() {
    echo -e "${YELLOW}📝 ШАГ 7: Включение детального логирования...${NC}"
    
    # Убедиться что логирование включено
    execute_remote "
        if ! grep -q '^LogLevel Info' /etc/tinyproxy/tinyproxy.conf; then
            sed -i '/^#LogLevel/a LogLevel Info' /etc/tinyproxy/tinyproxy.conf
            sed -i 's/^#LogLevel/LogLevel/' /etc/tinyproxy/tinyproxy.conf
        fi
        if ! grep -q '^LogFile' /etc/tinyproxy/tinyproxy.conf; then
            echo 'LogFile /var/log/tinyproxy/tinyproxy.log' >> /etc/tinyproxy/tinyproxy.conf
        fi
    "
    
    # Перезапустить TinyProxy
    execute_remote "systemctl restart tinyproxy"
    
    echo -e "${GREEN}✅ Логирование включено${NC}"
}

# ШАГ 8: Проверка
step8_verify() {
    echo -e "${YELLOW}🔍 ШАГ 8: Проверка работы...${NC}"
    
    # Проверить подключения
    CONNECTIONS=$(execute_remote "ss -tn | grep :8080 | wc -l")
    echo "   Подключений к 8080: $CONNECTIONS"
    
    # Проверить память
    MEMORY=$(execute_remote "free -h | grep Mem | awk '{print \$3}'")
    echo "   Использование памяти: $MEMORY"
    
    # Проверить fail2ban
    FAIL2BAN_STATUS=$(execute_remote "fail2ban-client status tinyproxy 2>/dev/null | grep 'Status' | awk '{print \$4}' || echo 'not installed'")
    echo "   fail2ban: $FAIL2BAN_STATUS"
    
    # Проверить UFW правила
    UFW_RULES=$(execute_remote "ufw status | grep 8080 | wc -l")
    echo "   UFW правил для 8080: $UFW_RULES"
    
    echo -e "${GREEN}✅ Проверка завершена${NC}"
}

# ШАГ 9: Создать скрипт мониторинга
step9_create_monitoring_script() {
    echo -e "${YELLOW}📊 ШАГ 9: Создание скрипта мониторинга...${NC}"
    
    execute_remote "cat > /usr/local/bin/check-proxy-status.sh << 'EOFSCRIPT'
#!/bin/bash
echo \"==========================================\"
echo \"📊 Статус прокси-сервера\"
echo \"==========================================\"
echo \"\"
echo \"🔌 Подключения к порту 8080:\"
CONNECTIONS=\$(ss -tn | grep :8080 | wc -l)
echo \"   Всего: \$CONNECTIONS\"
if [ \$CONNECTIONS -lt 20 ]; then
    echo \"   ✅ Нормально (< 20)\"
elif [ \$CONNECTIONS -lt 50 ]; then
    echo \"   ⚠️  Много (20-50)\"
else
    echo \"   ❌ Слишком много (> 50)\"
fi
echo \"\"
echo \"🌐 Топ 5 IP по подключениям:\"
ss -tn | grep :8080 | awk '{print \$5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -5
echo \"\"
echo \"💾 Использование памяти:\"
free -h | grep Mem | awk '{printf \"   Использовано: %s / %s (%.0f%%)\\n\", \$3, \$2, \$3/\$2*100}'
echo \"\"
echo \"💿 Использование Swap:\"
free -h | grep Swap | awk '{printf \"   Использовано: %s\\n\", \$3}'
echo \"\"
echo \"🛡️  Статус fail2ban:\"
fail2ban-client status tinyproxy 2>/dev/null | grep -E \"(Status|Currently banned)\" || echo \"   fail2ban не установлен\"
echo \"\"
echo \"==========================================\"
EOFSCRIPT
"
    
    execute_remote "chmod +x /usr/local/bin/check-proxy-status.sh"
    
    echo -e "${GREEN}✅ Скрипт мониторинга создан${NC}"
    echo "   Использование: ssh root@$SERVER_IP 'check-proxy-status.sh'"
}

# Главная функция
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Исправление ситуации с сервером${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    # Проверка подключения
    if ! check_connection; then
        echo -e "${RED}❌ Не удалось подключиться. Проверьте:\n  1. Интернет соединение\n  2. IP адрес сервера\n  3. Пароль${NC}"
        exit 1
    fi
    
    # Выполнение шагов
    step2_backup
    step3_close_access
    step4_limit_connections
    step5_install_fail2ban
    step6_limit_memory
    step7_enable_logging
    step8_verify
    step9_create_monitoring_script
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✅ Все шаги выполнены успешно!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Проверьте статус:"
    echo "  ssh root@$SERVER_IP 'check-proxy-status.sh'"
}

# Запуск
main
