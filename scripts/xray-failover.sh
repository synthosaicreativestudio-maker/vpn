#!/bin/bash
# Скрипт автоматического отката Xray VPN (Blue-Green Failover)
# Размещается на сервере 38.180.81.181 in /usr/local/bin/xray-failover.sh

BOT_TOKEN="8784903598:AAFbs2HJtgVlkcQGX2V6D5V5SAlCXtlvd10"
CHAT_ID="284355186"
SERVER_NAME="VPN-US (38.180.81.181)"

send_telegram() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "parse_mode=HTML" \
        -d "text=${message}" > /dev/null
}

# 1. Проверка статуса службы systemd
XRAY_STATUS=$(systemctl is-active xray)
if [ "$XRAY_STATUS" != "active" ]; then
    echo "[$(date)] Xray service is NOT active (status: $XRAY_STATUS). Initiating rollback..."
    ROLLBACK_REASON="Служба Xray не активна (статус: $XRAY_STATUS)"
    trigger_rollback=true
fi

# 2. Проверка прослушивания ключевых портов (443, 2053, 8443)
if [ "$trigger_rollback" != "true" ]; then
    for port in 443 2053 8443; do
        if ! ss -tlnp | grep -q ":$port "; then
            echo "[$(date)] Port $port is NOT listening. Initiating rollback..."
            ROLLBACK_REASON="Порт $port не прослушивается Xray"
            trigger_rollback=true
            break
        fi
    done
fi

# 3. Проверка работоспособности WARP (Cloudflare SOCKS5 на порту 40000)
# ВАЖНО: НЕ использовать google.com для проверки — Google банит shared WARP IP (302/429).
# Используем cloudflare.com/cdn-cgi/trace — всегда доступен через WARP и содержит warp=on.
if [ "$trigger_rollback" != "true" ]; then
    WARP_TRACE=$(curl -x socks5://127.0.0.1:40000 -s --connect-timeout 5 https://cloudflare.com/cdn-cgi/trace 2>&1)
    WARP_HTTP=$(curl -x socks5://127.0.0.1:40000 -s --connect-timeout 5 -o /dev/null -w "%{http_code}" https://cloudflare.com/cdn-cgi/trace)
    WARP_ON=$(echo "$WARP_TRACE" | grep -c "warp=on")

    if [ "$WARP_HTTP" != "200" ] || [ "$WARP_ON" -eq 0 ]; then
        echo "[$(date)] WARP check failed (HTTP: $WARP_HTTP, warp=on: $WARP_ON). Attempting to recover WARP..."
        
        # Попытка восстановления
        systemctl restart warp-svc
        sleep 3
        warp-cli --accept-tos connect > /dev/null 2>&1
        sleep 3
        
        # Перепроверка
        WARP_TRACE_AGAIN=$(curl -x socks5://127.0.0.1:40000 -s --connect-timeout 5 https://cloudflare.com/cdn-cgi/trace 2>&1)
        WARP_HTTP_AGAIN=$(curl -x socks5://127.0.0.1:40000 -s --connect-timeout 5 -o /dev/null -w "%{http_code}" https://cloudflare.com/cdn-cgi/trace)
        WARP_ON_AGAIN=$(echo "$WARP_TRACE_AGAIN" | grep -c "warp=on")

        if [ "$WARP_HTTP_AGAIN" != "200" ] || [ "$WARP_ON_AGAIN" -eq 0 ]; then
            echo "[$(date)] WARP recovery failed (HTTP: $WARP_HTTP_AGAIN, warp=on: $WARP_ON_AGAIN)."
            send_telegram "🚨 <b>[${SERVER_NAME}]</b> Сбой WARP! Попытка автоматического восстановления не удалась. Trace HTTP: ${WARP_HTTP_AGAIN}, warp=on: ${WARP_ON_AGAIN}."
        else
            echo "[$(date)] WARP recovered successfully."
            send_telegram "ℹ️ <b>[${SERVER_NAME}]</b> Было зафиксировано падение WARP. Автоматическое восстановление прошло успешно."
        fi
    fi
fi

# 4. Выполнение отката при необходимости
if [ "$trigger_rollback" = "true" ]; then
    send_telegram "⚠️ <b>[${SERVER_NAME}]</b> Обнаружен сбой VPN!
<b>Причина:</b> ${ROLLBACK_REASON}
Запуск процесса автоматического отката (Rollback)..."

    # Откат конфигурации
    if [ -f "/etc/xray/config.json.stable" ]; then
        cp /etc/xray/config.json.stable /etc/xray/config.json
        echo "[$(date)] Restored config.json from config.json.stable"
    else
        echo "[$(date)] Critical: config.json.stable not found!"
    fi

    # Откат бинарного файла
    if [ -f "/usr/local/bin/xray.stable" ]; then
        cp /usr/local/bin/xray.stable /usr/local/bin/xray
        chmod +x /usr/local/bin/xray
        echo "[$(date)] Restored xray binary from xray.stable"
    else
        echo "[$(date)] Critical: xray.stable not found!"
    fi

    # Перезапуск службы
    systemctl daemon-reload
    systemctl restart xray
    sleep 3

    NEW_STATUS=$(systemctl is-active xray)
    if [ "$NEW_STATUS" = "active" ]; then
        send_telegram "✅ <b>[${SERVER_NAME}]</b> Автоматический откат успешно завершен! VPN-сервер восстановлен и работает стабильно."
        echo "[$(date)] Rollback successful. Xray is now active."
    else
        send_telegram "🚨 <b>[${SERVER_NAME}]</b> КРИТИЧЕСКАЯ ОШИБКА: Автоматический откат не помог! VPN всё ещё не работает."
        echo "[$(date)] Rollback failed. Xray is still inactive."
    fi
else
    echo "[$(date)] Xray health check passed successfully."
fi
