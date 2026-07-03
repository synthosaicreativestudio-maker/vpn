#!/bin/bash
# Скрипт автоматического отката Xray на релее (Blue-Green Failover)
# Размещается на сервере 185.4.67.223 в /usr/local/bin/relay-failover.sh

BOT_TOKEN="8784903598:AAFbs2HJtgVlkcQGX2V6D5V5SAlCXtlvd10"
CHAT_ID="284355186"
SERVER_NAME="Relay-RU (185.4.67.223)"

send_telegram() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "parse_mode=HTML" \
        -d "text=${message}" > /dev/null 2>&1
}

trigger_rollback=false
ROLLBACK_REASON=""

# 1. Проверка статуса службы xray
XRAY_STATUS=$(systemctl is-active xray 2>/dev/null)
if [ "$XRAY_STATUS" != "active" ]; then
    echo "[$(date)] Xray relay is NOT active (status: $XRAY_STATUS)"
    ROLLBACK_REASON="Служба Xray (relay) не активна (статус: $XRAY_STATUS)"
    trigger_rollback=true
fi

# 2. Проверка ключевых портов (443 Vision, 2053 gRPC, 8443 xHTTP)
if [ "$trigger_rollback" != "true" ]; then
    for port in 443 2053 8443; do
        if ! ss -tlnp | grep -q ":$port "; then
            echo "[$(date)] Relay port $port is NOT listening."
            ROLLBACK_REASON="Порт $port не прослушивается на релее"
            trigger_rollback=true
            break
        fi
    done
fi

# 3. Откат при необходимости
if [ "$trigger_rollback" = "true" ]; then
    send_telegram "⚠️ <b>[${SERVER_NAME}]</b> Обнаружен сбой релея!
<b>Причина:</b> ${ROLLBACK_REASON}
Запуск автоматического отката..."

    if [ -f "/usr/local/etc/xray/config.json.stable" ]; then
        cp /usr/local/etc/xray/config.json.stable /usr/local/etc/xray/config.json
        echo "[$(date)] Restored relay config from config.json.stable"
    fi

    if [ -f "/usr/local/bin/xray.stable" ]; then
        cp /usr/local/bin/xray.stable /usr/local/bin/xray
        chmod +x /usr/local/bin/xray
        echo "[$(date)] Restored relay xray binary from xray.stable"
    fi

    systemctl daemon-reload
    systemctl restart xray
    sleep 3

    NEW_STATUS=$(systemctl is-active xray)
    if [ "$NEW_STATUS" = "active" ]; then
        send_telegram "✅ <b>[${SERVER_NAME}]</b> Автоматический откат релея завершен! Релей восстановлен."
        echo "[$(date)] Relay rollback successful."
    else
        send_telegram "🚨 <b>[${SERVER_NAME}]</b> КРИТИЧЕСКАЯ ОШИБКА: Откат релея не помог!"
        echo "[$(date)] Relay rollback FAILED."
    fi
else
    echo "[$(date)] Relay health check passed successfully."
fi
