#!/bin/bash

# Скрипт для генерации ключей REALITY для Marzban
# Использование: ./generate_keys.sh

echo "🔑 Генерация ключей REALITY для Marzban..."
echo ""

# Проверка, запущен ли контейнер Marzban
if ! docker ps | grep -q marzban; then
    echo "❌ Ошибка: Контейнер Marzban не найден или не запущен"
    echo "Проверьте имя контейнера командой: docker ps"
    exit 1
fi

# Получение имени контейнера Marzban
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -i marzban | head -n 1)

if [ -z "$CONTAINER_NAME" ]; then
    echo "❌ Ошибка: Не удалось найти контейнер Marzban"
    echo "Доступные контейнеры:"
    docker ps --format "{{.Names}}"
    exit 1
fi

echo "📦 Найден контейнер: $CONTAINER_NAME"
echo ""
echo "🔐 Генерирую ключи..."
echo ""

# Генерация ключей
docker exec -it "$CONTAINER_NAME" xray x25519

echo ""
echo "✅ Ключи сгенерированы!"
echo ""
echo "📝 Инструкция:"
echo "1. Скопируйте Private Key и Public Key из вывода выше"
echo "2. Откройте файл marzban_reality_config.json"
echo "3. Замените 'ЗАМЕНИТЕ_НА_PRIVATE_KEY_ИЗ_КОМАНДЫ_xray_x25519' на Private Key"
echo "4. Замените 'ЗАМЕНИТЕ_НА_PUBLIC_KEY_ИЗ_КОМАНДЫ_xray_x25519' на Public Key"
echo "5. Вставьте JSON в раздел 'inbounds' в Marzban -> Core Settings"
echo ""
