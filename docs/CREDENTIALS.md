# Все доступы (05.04.2026)

## Серверы
- US: `37.1.212.51` SSH: `root / LEJ6U5chSK`

## VPN каналы (5 шт)
1. VLESS+Reality+Vision — порт 443
2. VLESS+Reality+xHTTP — порт 8443
3. VLESS+Reality+gRPC — порт 2053
4. VLESS+WS — порт 2083
5. Hysteria2 — порт 10443 UDP

Reality: pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4 sid=0123456789abcdef
UUID: eb4a1cf2-4235-4b0a-83b2-0e5a298389ed

## Подписки
- Hiddify: http://37.1.212.51:8085/sub/hiddify/{TOKEN}
- Happ: http://37.1.212.51:8085/sub/happ/{TOKEN}
- Панель: http://37.1.212.51:8085/admin/ui
- API Key: b534ef20bdea908d3b9b4f5388467d525ba88f7abaddcc5ca8b4c159b75335c3

## Relay RU (обход белых списков ТСПУ)
- IP: `51.250.94.182` SSH: `ubuntu` (ключ ed25519)
- Yandex Cloud (AS200350), зона ru-central1-a
- Xray relay → US 37.1.212.51
- Порт: 443
- UUID: `57ca4aae-dcb3-4fdd-9e14-f9afb42b703c`
- Reality: pbk=p2EEfvTbaG9Qca4xKM4AxHVX1wFOqFut0Z4TX6T1wUg sid=791cd192259bb2b9
- Private Key: `6BsVfWmKPVpqNTMAZL2vW9Q2ROUMCQRhlrUhtlolUXc`
- SNI: ozon.ru (+ wildberries.ru, ads.x5.ru)
- relay-bridge user на US: UUID eb4a1cf2-4235-4b0a-83b2-0e5a298389ed

## Важно
- При перезагрузке xray: systemctl restart vpn-panel.service
- BBR включён на обоих серверах

## Т-Банк Интернет-эквайринг (ИП Марченко Р.)
- **Terminal Key (тест)**: `1778844937330DEMO`
- **Пароль (тест)**: `oBDLqS9c34ydSNdZ`
- Магазин ID: 905483
- API: https://securepay.tinkoff.ru/v2/
- Документация: https://www.tbank.ru/kassa/dev/payments/
