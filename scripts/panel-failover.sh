#!/bin/bash
# Скрипт автоматического отката Panel + Bot (Blue-Green Failover)
# Размещается на сервере 37.1.212.51 в /usr/local/bin/panel-failover.sh

BOT_TOKEN="8784903598:AAFbs2HJtgVlkcQGX2V6D5V5SAlCXtlvd10"
CHAT_ID="284355186"
SERVER_NAME="Panel (37.1.212.51)"

send_telegram() {
    local message="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "parse_mode=HTML" \
        -d "text=${message}" > /dev/null 2>&1
}

trigger_rollback=false
ROLLBACK_REASON=""

# 1. Проверка статуса vpn-panel
PANEL_STATUS=$(systemctl is-active vpn-panel 2>/dev/null)
if [ "$PANEL_STATUS" != "active" ]; then
    echo "[$(date)] vpn-panel is NOT active (status: $PANEL_STATUS)"
    ROLLBACK_REASON="Служба vpn-panel не активна (статус: $PANEL_STATUS)"
    trigger_rollback=true
fi

# 2. Проверка health endpoint (только если служба активна)
if [ "$trigger_rollback" != "true" ]; then
    HEALTH=$(curl -sf --connect-timeout 5 http://127.0.0.1:8085/health 2>/dev/null)
    if [ -z "$HEALTH" ]; then
        echo "[$(date)] Panel health check failed (no response on :8085)"
        ROLLBACK_REASON="Panel health check: нет ответа на :8085"
        trigger_rollback=true
    fi
fi

# 3. Откат при необходимости
if [ "$trigger_rollback" = "true" ]; then
    send_telegram "⚠️ <b>[${SERVER_NAME}]</b> Обнаружен сбой панели!
<b>Причина:</b> ${ROLLBACK_REASON}
Запуск автоматического отката..."

    # Откат кода панели
    if [ -d "/etc/vpn-panel/panel.stable" ]; then
        rsync -a --delete /etc/vpn-panel/panel.stable/ /root/vpn/panel/ \
            --exclude 'data' --exclude '__pycache__' --exclude '.env'
        echo "[$(date)] Restored panel code from panel.stable"
    fi

    # Откат кода бота
    if [ -d "/etc/vpn-panel/bot.stable" ]; then
        rsync -a --delete /etc/vpn-panel/bot.stable/ /root/vpn/bot/ \
            --exclude '__pycache__'
        echo "[$(date)] Restored bot code from bot.stable"
    fi

    # Откат .env (если существует)
    if [ -f "/etc/vpn-panel/env.stable" ]; then
        cp /etc/vpn-panel/env.stable /root/vpn/panel/.env
        echo "[$(date)] Restored .env from env.stable"
    fi

    # Перезапуск служб
    systemctl restart vpn-panel
    sleep 3

    NEW_STATUS=$(systemctl is-active vpn-panel)
    NEW_HEALTH=$(curl -sf --connect-timeout 5 http://127.0.0.1:8085/health 2>/dev/null)

    if [ "$NEW_STATUS" = "active" ] && [ -n "$NEW_HEALTH" ]; then
        send_telegram "✅ <b>[${SERVER_NAME}]</b> Автоматический откат успешно завершен! Панель подписок восстановлена."
        echo "[$(date)] Rollback successful. Panel is active and healthy."
        # Перезапустить бота (он зависит от панели)
        systemctl restart vpn-bot
    else
        send_telegram "🚨 <b>[${SERVER_NAME}]</b> КРИТИЧЕСКАЯ ОШИБКА: Автоматический откат панели не помог!"
        echo "[$(date)] Rollback FAILED. Panel status: $NEW_STATUS"
    fi
else
    echo "[$(date)] Panel health check passed successfully."
fi
