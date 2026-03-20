# 📱 Клиентские конфигурации VPN

## 📋 Обзор

Архив сведен к одной простой схеме:
- **IP сервера:** 37.1.212.51
- **Протокол:** VLESS + REALITY
- **Порт:** 443
- **Маскировка:** www.microsoft.com

Есть только два рабочих варианта:
- `client_config_global.json` - весь трафик через VPN
- `client_config_smart_routing_ru.json` - российские сервисы напрямую, остальное через VPN

## 🎯 Вариант 1: Global VPN

**Файл:** `client_config_global.json`

Используйте, если нужен самый простой режим без разделения трафика.

### Как подключить
- Amnezia VPN: `File with connection settings`
- v2rayNG: импорт из файла или из ссылки
- v2rayN: импорт из файла или из буфера обмена
- V2rayU: импорт из файла

## 🧠 Вариант 2: Smart Routing

**Файл:** `client_config_smart_routing_ru.json`

Используйте, если российские сайты должны открываться напрямую, а зарубежные идти через VPN.

### Что идет напрямую
- Банки
- Госуслуги
- Yandex
- VK
- Mail.ru
- Telegram
- Все `.ru` и `.рф`

### Что идет через VPN
- Google
- YouTube
- Instagram
- Остальные зарубежные сайты

## 🔧 Технические детали

- **UUID:** `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed`
- **Public Key:** `n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4`
- **SNI:** `www.microsoft.com`
- **Flow:** `xtls-rprx-vision`
- **Fingerprint:** `chrome`

## ✅ Проверка

1. Откройте любой сайт
2. Проверьте IP
3. Если нужен быстрый тест, используйте `vless://` из `vless_connection_link.txt`

## 🆘 Если не работает

- Проверьте UUID и Public Key
- Проверьте, что порт `443` открыт
- Проверьте, что выбран правильный файл

## 📝 Дополнительная информация

- `routing_rules_explained.md`
- `SERVER_CONFIGURATION_REPORT.md`
- `QUICK_REFERENCE.md`
