#!/bin/bash
# ──────────────────────────────────────────────────────────────
# Установка и настройка Hysteria2 сервера
# Запускать на VPS: bash hysteria2_install.sh
# ──────────────────────────────────────────────────────────────

set -euo pipefail

echo "🚀 Установка Hysteria2..."

# 1. Скачать официальный бинарник
bash <(curl -fsSL https://get.hy2.sh/)

# 2. Создать директорию конфигов
mkdir -p /etc/hysteria

# 3. Сгенерировать самоподписанный TLS-сертификат
openssl req -x509 -nodes -newkey ec:<(openssl ecparam -name prime256v1) \
    -keyout /etc/hysteria/server.key \
    -out /etc/hysteria/server.crt \
    -subj "/CN=www.microsoft.com" \
    -days 3650
chmod 600 /etc/hysteria/server.key

# 4. Скопировать конфиг
cat > /etc/hysteria/config.yaml << 'EOF'
listen: :10443

tls:
  cert: /etc/hysteria/server.crt
  key: /etc/hysteria/server.key

auth:
  type: password
  password: HysteriaPassword2026

masquerade:
  type: proxy
  proxy:
    url: https://www.microsoft.com
    rewriteHost: true

bandwidth:
  up: 500 mbps
  down: 500 mbps

quic:
  initStreamReceiveWindow: 8388608
  maxStreamReceiveWindow: 8388608
  initConnReceiveWindow: 20971520
  maxConnReceiveWindow: 20971520
EOF

# 5. Создать systemd-сервис
cat > /etc/systemd/system/hysteria2.service << 'EOF'
[Unit]
Description=Hysteria2 VPN Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/hysteria server -c /etc/hysteria/config.yaml
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

# 6. Открыть UDP порт
ufw allow 10443/udp comment "Hysteria2"

# 7. Запустить
systemctl daemon-reload
systemctl enable hysteria2
systemctl start hysteria2

echo ""
echo "✅ Hysteria2 установлен и запущен!"
echo "   Порт: 10443/UDP"
echo "   Пароль: HysteriaPassword2026"
echo ""
echo "Проверка статуса: systemctl status hysteria2"
echo "Логи: journalctl -u hysteria2 -f"
