#!/bin/bash

echo "🚀 Начинаем обновление конфигурации Xray на сервере 37.1.212.51..."

# Определяем путь к локальному конфигу
LOCAL_CONFIG="configs_2026_03_20/xray_config_yandex.json"

if [ ! -f "$LOCAL_CONFIG" ]; then
    echo "❌ Ошибка: Локальный файл $LOCAL_CONFIG не найден."
    exit 1
fi

echo "📦 Копируем $LOCAL_CONFIG на сервер..."
# Используем scp для копирования файла на сервер. Он запросит пароль: LEJ6U5chSK
scp "$LOCAL_CONFIG" root@37.1.212.51:/tmp/xray_config_yandex.json

if [ $? -ne 0 ]; then
    echo "❌ Ошибка копирования. Проверьте сеть или пароль."
    exit 1
fi

echo "🔄 Переносим конфиг в нужную папку и перезапускаем Marzban..."
# Перенос конфига на сервере и рестарт Marzban (в двух возможных локациях)
ssh root@37.1.212.51 << 'EOF'
    # Ищем, где установлен Marzban, чтобы положить туда xray_config.json
    if [ -d "/var/lib/marzban" ]; then
        mv /tmp/xray_config_yandex.json /var/lib/marzban/xray_config.json
    elif [ -d "/opt/marzban" ]; then
        mv /tmp/xray_config_yandex.json /opt/marzban/xray_config.json
    else
        echo "⚠️ Папка marzban не найдена. Оставляем конфиг в /tmp/"
    fi
    
    # Перезапускаем сервер
    if command -v marzban >/dev/null 2>&1; then
        marzban restart
    elif [ -d "/opt/marzban" ]; then
        cd /opt/marzban && docker compose restart marzban
    else
        echo "⚠️ Не удалось выполнить перезапуск автоматически. Перезапустите контейнер вручную."
    fi
EOF

echo "✅ Обновление сервера завершено! Теперь Hiddify и Amnezia смогут подключиться по gRPC-ссылкам."
