---
name: Backup & System Recovery
description: Automated backups, SQLite panel database backup, config recovery, server migration scripts
version: 1.0.0
---

# 💾 Backup & System Recovery

Этот skill содержит процедуры резервного копирования данных панели, конфигураций прокси-сервера и шаги по аварийному восстановлению (Disaster Recovery).

---

## 📂 Что подлежит бэкапу (Backup Scope)

1. **База данных пользователей:** `/root/vpn/panel/data/panel.db` (база SQLite со всеми токенами и пользователями).
2. **Конфигурационные файлы:**
   * `/etc/xray/config.json` (US) и `/usr/local/etc/xray/config.json` (Relay).
   * `/etc/caddy/Caddyfile` или `/root/vpn/Caddyfile`.
   * `/etc/hysteria/config.yaml` (если установлен отдельно).
3. **Системные файлы:** `/etc/sysctl.d/99-vpn.conf` (оптимизация сети).

---

## 📝 Скрипт автоматического бэкапа (`/root/vpn/backup.sh`)

Скрипт создает сжатый архив и может отправлять его в облачное хранилище или Telegram-канал.

```bash
#!/bin/bash
BACKUP_DIR="/root/vpn_backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)
ARCHIVE_NAME="vpn_backup_${DATE}.tar.gz"

mkdir -p "$BACKUP_DIR"

# Архивируем базу данных и все важные конфиги
tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" \
    /root/vpn/panel/data/panel.db \
    /etc/xray/config.json \
    /root/vpn/Caddyfile \
    /etc/sysctl.d/99-vpn.conf \
    2>/dev/null

# Удаляем архивы старше 14 дней
find "$BACKUP_DIR" -type f -name "vpn_backup_*.tar.gz" -mtime +14 -delete

echo "Backup created: ${BACKUP_DIR}/${ARCHIVE_NAME}"
```

**Добавление в cron (ежедневно в 03:00):**
```text
0 3 * * * /bin/bash /root/vpn/backup.sh >/dev/null 2>&1
```

---

## 🔄 Аварийное восстановление на чистом сервере (Recovery)

Если сервер заблокирован или уничтожен хостингом:

1. **Развернуть базовое окружение (Debian/Ubuntu):**
   ```bash
   apt update && apt install -y git python3 python3-pip curl screen jq
   ```
2. **Клонировать репозиторий проекта:**
   ```bash
   git clone https://github.com/synthosaicreativestudio-maker/vpn.git /root/vpn
   ```
3. **Распаковать резервную копию:**
   ```bash
   tar -xzf vpn_backup_YYYY-MM-DD.tar.gz -C /
   ```
4. **Установить Xray:**
   ```bash
   bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
   ```
5. **Запустить Panel и Bot:**
   ```bash
   cd /root/vpn
   pip3 install -r panel/requirements.txt # если требуется
   systemctl daemon-reload
   systemctl start xray vpn-panel vpn-bot
   ```
6. Настроить автозапуск служб: `systemctl enable xray vpn-panel vpn-bot`.
