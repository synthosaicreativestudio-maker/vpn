#!/bin/bash
# ══════════════════════════════════════════════════════════════
# Скрипт миграции VPN: Marzban → Своя панель
# Запуск: bash deploy.sh
# ══════════════════════════════════════════════════════════════
set -e

SERVER="root@37.1.212.51"
REMOTE_DIR="/opt/vpn"
PASSWORD="LEJ6U5chSK"

echo "🚀 Начинаю миграцию VPN на собственную панель..."

# ── 1. Остановка Marzban ──────────────────────────────────────
echo "⏹  Останавливаю Marzban..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "cd /opt/marzban && docker compose down 2>/dev/null || true; \
     pkill -9 -f 'python.*bot' 2>/dev/null || true"

# ── 2. Подготовка директории на сервере ───────────────────────
echo "📁 Подготавливаю директорию $REMOTE_DIR..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "mkdir -p $REMOTE_DIR"

# ── 3. Синхронизация кода ─────────────────────────────────────
echo "📦 Копирую код на сервер..."
sshpass -p "$PASSWORD" rsync -avz --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.ruff_cache' \
    --exclude '.DS_Store' \
    --exclude '_archive' \
    --exclude '_backup_configs' \
    --exclude 'ALL_CREDENTIALS.md' \
    --exclude 'YANDEX_VM_CREDENTIALS.md' \
    -e "ssh -o StrictHostKeyChecking=no" \
    ./ "$SERVER:$REMOTE_DIR/"

# ── 4. Копируем docker-compose.server.yml как основной ────────
echo "📋 Устанавливаю docker-compose..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "cp $REMOTE_DIR/docker-compose.server.yml $REMOTE_DIR/docker-compose.yml"

# ── 5. Собираем и запускаем ───────────────────────────────────
echo "🔨 Собираю и запускаю контейнеры..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "cd $REMOTE_DIR && docker compose build --no-cache && docker compose up -d"

# ── 6. Ждём запуска ──────────────────────────────────────────
echo "⏳ Жду 10 секунд для запуска сервисов..."
sleep 10

# ── 7. Проверка здоровья ──────────────────────────────────────
echo "🏥 Проверяю здоровье сервисов..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'HEALTHCHECK'
echo "--- Docker containers ---"
docker ps --format "{{.Names}}: {{.Status}}"

echo ""
echo "--- VPN Ports ---"
ss -tlnp | grep -E "443|8443|2053|2083|8085|10085"

echo ""
echo "--- Panel health ---"
curl -sf http://127.0.0.1:8085/health 2>/dev/null && echo "" || echo "❌ Panel not responding"

echo ""
echo "--- Bot log ---"
docker logs vpn-bot --tail 5 2>/dev/null || echo "❌ Bot container not found"
HEALTHCHECK

echo ""
echo "✅ Миграция завершена!"
echo "📱 Проверьте бота в Telegram и обновите подписку в Hiddify."
