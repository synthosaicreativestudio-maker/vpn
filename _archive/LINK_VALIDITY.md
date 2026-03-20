# 🔗 Валидность ссылки подключения

## ✅ Основная ссылка не требует обновления

Если не меняются сервер, UUID, ключи REALITY или порт, ссылка остается рабочей.

## Что считается стабильным

- UUID пользователя
- IP сервера
- Порт `443`
- Public Key REALITY
- SNI `www.microsoft.com`
- Flow `xtls-rprx-vision`

## Когда ссылку нужно менять

- Создан новый пользователь
- Поменялся IP сервера
- Поменялся порт
- Перегенерированы ключи REALITY
- Поменялся SNI или Flow

## Как проверить

- UUID: `cat /var/lib/marzban/xray_config.json | grep "id"`
- IP: `hostname -I`
- Порт: `netstat -tlnp | grep 443`
- Public Key: `cat /var/lib/marzban/xray_config.json | grep "publicKey"`
- SNI: `cat /var/lib/marzban/xray_config.json | grep "serverName"`
