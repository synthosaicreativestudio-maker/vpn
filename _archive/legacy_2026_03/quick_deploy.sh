#!/bin/bash
export SSHPASS="LEJ6U5chSK"
sshpass -e scp -o StrictHostKeyChecking=no bot/main.py root@37.1.212.51:/opt/vpn/bot/main.py
sshpass -e ssh -o StrictHostKeyChecking=no root@37.1.212.51 "cd /opt/vpn && docker compose restart bot"
sshpass -e scp -o StrictHostKeyChecking=no Caddyfile root@37.1.212.51:/etc/caddy/Caddyfile || echo "Caddyfile copy passed/failed"
sshpass -e ssh -o StrictHostKeyChecking=no root@37.1.212.51 "systemctl reload caddy || systemctl restart caddy || true"
sshpass -e ssh -o StrictHostKeyChecking=no root@37.1.212.51 "ufw allow 8086/tcp || true"
echo "Deployed successfully"
