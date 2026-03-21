#!/bin/bash
set -e
echo "Синхронизация файлов..."
rsync -avz --delete \
    --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
    --exclude '.ruff_cache' --exclude '.DS_Store' --exclude '_archive' \
    --exclude '_backup_configs' --exclude 'ALL_CREDENTIALS.md' \
    --exclude 'YANDEX_VM_CREDENTIALS.md' \
    -e "ssh -o StrictHostKeyChecking=no" \
    ./ root@37.1.212.51:/opt/vpn/

echo "Перезапуск сервисов..."
ssh -o StrictHostKeyChecking=no root@37.1.212.51 << 'EOF'
cd /opt/vpn
cp docker-compose.server.yml docker-compose.yml
docker compose down || true
docker compose build --no-cache
docker compose up -d
ufw allow 8086/tcp || ufw allow 8086 || true
EOF
echo "Деплой успешно завершен!"
