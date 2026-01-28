#!/bin/bash

TEMPLATE_FILE="/var/lib/marzban/templates/clash/smart-routing.yml"

echo "🛠 Updating Subscription Template at $TEMPLATE_FILE..."

# We will overwrite the template with a dual-proxy configuration
# This ensures that even if Marzban DB doesn't know about port 2096, 
# the subscription will still deliver it to clients.

cat <<EOF > $TEMPLATE_FILE
port: 7890
socks-port: 7891
allow-lan: false
mode: rule
log-level: info
dns:
  enable: true
  enhanced-mode: fake-ip
  nameserver:
    - 8.8.8.8
    - 1.1.1.1
  fallback-filter:
    geoip: true
    geoip-code: RU

proxies:
  # V1: Main Channel (Yandex/TCP)
  - name: "🚀 Smart-VPN-Yandex"
    type: vless
    server: 37.1.212.51
    port: 443
    uuid: eb4a1cf2-4235-4b0a-83b2-0e5a298389ed
    tls: true
    udp: true
    flow: xtls-rprx-vision
    servername: taxi.yandex.ru
    client-fingerprint: chrome
    reality-opts:
      public-key: n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4
      short-id: ""

  # V2: Backup Channel (Google/gRPC) - HARDCODED FIX
  - name: "🛡️ Smart-Backup-Google"
    type: vless
    server: 37.1.212.51
    port: 2096
    uuid: eb4a1cf2-4235-4b0a-83b2-0e5a298389ed
    tls: true
    udp: true
    servername: dl.google.com
    client-fingerprint: chrome
    network: grpc
    grpc-opts:
        grpc-service-name: grpc
    reality-opts:
      public-key: x_GPfa0J4Js_wngtYThTvO4fpBWIT9rH-NNQ-2dhYHg
      short-id: ""

proxy-groups:
  - name: "🚀 Smart VPN"
    type: select
    proxies:
      - "🚀 Smart-VPN-Yandex"
      - "🛡️ Smart-Backup-Google"
      - DIRECT

rules:
  - DOMAIN-SUFFIX,gosuslugi.ru,DIRECT
  - DOMAIN-SUFFIX,sberbank.ru,DIRECT
  - DOMAIN-SUFFIX,tinkoff.ru,DIRECT
  - DOMAIN-SUFFIX,ya.ru,DIRECT
  - DOMAIN-SUFFIX,yandex.ru,DIRECT
  - DOMAIN-SUFFIX,ru,DIRECT
  - GEOIP,RU,DIRECT
  - MATCH,🚀 Smart VPN
EOF

echo "✅ Template updated with Dual-Stack (Yandex + Google)."
echo "🔄 Restarting Marzban to clear caches..."
cd /var/lib/marzban && docker compose restart
