---
name: Monitoring & Alerts
description: System health check, service monitoring (Xray, Panel), memory/disk alert script, Telegram notifications
version: 1.0.0
---

# 📊 Monitoring & Alerts

Этот skill описывает методы непрерывного контроля за состоянием серверов VPN и автоматического уведомления администратора в случае сбоев.

---

## 🔍 Быстрый ручной осмотр сервера (CLI Check)

```bash
# Проверить статус ключевых служб
systemctl status xray vpn-panel vpn-bot --no-pager

# Просмотр логов в реальном времени
journalctl -u xray -n 50 -f
journalctl -u vpn-panel -n 50 -f

# Проверка использования диска и памяти
df -h
free -h
```

---

## 🤖 Скрипт авто-мониторинга с алертом в Telegram

Скрипт проверяет состояние сервисов, использование диска (>90%) и свободной памяти (<100MB), после чего присылает сообщение в Telegram.

Создайте файл `/root/vpn/monitor.sh`:
```bash
#!/bin/bash

# Настройки Telegram бота (токен и chat_id берутся из docs/CREDENTIALS.md или конфига бота)
TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID="YOUR_ADMIN_CHAT_ID"

send_alert() {
    local message="⚠️ *VPN Alert:* $1"
    curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${message}" \
        -d "parse_mode=Markdown" >/dev/null
}

# 1. Проверка работоспособности сервисов
for service in xray vpn-panel vpn-bot; do
    if ! systemctl is-active --quiet "$service"; then
        send_alert "Служба *${service}* остановлена на сервере US! Попытка перезапуска..."
        systemctl restart "$service"
    fi
done

# 2. Проверка свободного диска
DISK_USAGE=$(df / | grep / | awk '{ print $5 }' | sed 's/%//g')
if [ "$DISK_USAGE" -gt 90 ]; then
    send_alert "Критическое заполнение диска: *${DISK_USAGE}%* используется!"
fi

# 3. Проверка свободной памяти
FREE_MEM=$(free -m | grep Mem | awk '{print $4}')
if [ "$FREE_MEM" -lt 100 ]; then
    send_alert "Критический недостаток оперативной памяти: осталось всего *${FREE_MEM}MB* RAM!"
fi
```

**Добавление в планировщик cron (выполнять каждые 5 минут):**
```text
*/5 * * * * /bin/bash /root/vpn/monitor.sh >/dev/null 2>&1
```
