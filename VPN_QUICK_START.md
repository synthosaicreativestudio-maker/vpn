# VPN Quick Start

## Что использовать сейчас

- Основной вариант: `configs_2026_03_20/raw_sub.txt`
- Альтернатива: `configs_2026_03_20/sub.txt`
- Для Hiddify: `configs_2026_03_20/hiddify_ALL_IN_ONE.json`
- Для Amnezia / Xray-подобных клиентов:
  - `_backup_configs/client_config_global.json`
  - `_backup_configs/client_config_smart_routing_ru.json`
- Для QR по простому VLESS: `configs_2026_03_20/qr_amnezia_vless.png`

## Коротко по клиентам

- Hiddify: используйте HTTP ссылку-подписку из бота
- Amnezia: используйте `client_config_global.json` или `client_config_smart_routing_ru.json`
- Happ: используйте HTTPS Base64 ссылку-подписку из бота

## Что не считать активным

- `XHTTP`
- `Shadow-TLS`
- `Shadowsocks-2022` как отдельный резервный канал
- `AmneziaWG` как часть текущего активного пакета

## Проверка

- Откройте любой сайт и проверьте IP
- Если нужен только простой старт, используйте `VLESS tcp` из `raw_sub.txt`
