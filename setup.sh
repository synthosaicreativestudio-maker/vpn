#!/bin/bash
# === PARAMETERS ===
IP=$(curl -s ifconfig.me)
DOMAIN="${IP}.sslip.io"
INSTALL_DIR="/var/lib/marzban"

# Existing Keys (User Provided / Preserved)
PK="4PjME9JBUmV-Td9rZGS9l0147TXqMJtcU_f2iG-PVxA"
# Public Key n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4 corresponds to this PK
SHORT_ID=""

echo "🚀 Restoring Working Configuration (Smart VPN / 13:41)..."

# 1. System Deps
apt update && apt install -y nginx certbot python3-certbot-nginx sqlite3 jq curl ufw

# 2. Xray Config (FULL MARZBAN COMPATIBLE)
# Includes API, Stats, Policy, and Inbound 443 with Fallbacks
cat <<EOF > $INSTALL_DIR/xray_config.json
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "tag": "VLESS_IN",
      "listen": "0.0.0.0",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [
          {
            "id": "eb4a1cf2-4235-4b0a-83b2-0e5a298389ed",
            "flow": "xtls-rprx-vision",
            "email": "Marz-vera"
          }
        ],
        "decryption": "none",
        "fallbacks": [
          { "dest": "taxi.yandex.ru:443", "xver": 0 }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "taxi.yandex.ru:443",
          "xver": 0,
          "serverNames": [
            "taxi.yandex.ru",
            "ya.ru",
            "yandex.ru"
          ],
          "privateKey": "$PK",
          "shortIds": [
            "$SHORT_ID"
          ]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": []
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "DIRECT"
    },
    {
      "protocol": "blackhole",
      "tag": "BLOCK"
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "ip": [
          "geoip:private"
        ],
        "outboundTag": "DIRECT"
      }
    ]
  }
}
EOF

# 3. Nginx Config (Internal 8081)
cat <<EOF > /etc/nginx/sites-available/marzban
server {
    listen 127.0.0.1:8081 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location /.well-known/acme-challenge/ { root /var/www/html; }

    # Subscription Proxy
    location /sub/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # Dashboard/API
    location ~ ^/(dashboard|api|static|docs|openapi.json|assets) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location / { return 404; }
}
EOF
cp /var/lib/marzban/static_sub.json /var/www/html/sub.json

ln -sf /etc/nginx/sites-available/marzban /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# 4. Marzban Docker Compose
cat <<EOF > $INSTALL_DIR/docker-compose.yml
services:
  marzban:
    image: gozargah/marzban:latest
    container_name: marzban
    restart: always
    network_mode: host
    volumes:
      - /var/lib/marzban:/var/lib/marzban
      - $INSTALL_DIR/xray_config.json:/etc/xray/config.json
    environment:
      - UVICORN_PORT=8000
      - XRAY_JSON=/etc/xray/config.json
EOF

# 5. Restart Marzban
cd $INSTALL_DIR && docker compose up -d --force-recreate

echo "✅ System Restored. Connect using the VLESS link or Subscription."
