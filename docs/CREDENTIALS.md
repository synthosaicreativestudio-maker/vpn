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

## API Ключи и Токены
- **Telegram Bot Token**: `8232668997:AAH1oMWo7ZqnwjVX2GH3avEjPrCTNK2kVmc` (Username: `@SintaMarketingBot`)
- **Gemini API Key**: `AIzaSyD5WGVM1AqIjhszcGEprqOo-PwrldExmQs`
- **Gemini Server Key**: `AIzaSyBu1hTc7tJ87h-4otHp3j36Hs4LDSvyFl4` (установлен локально на сервере US)
- **Anthropic (Claude) Key**: `sk-ant-api03-***`

## Google Sheets & Drive IDs
- **Авторизация (список)**: `1_SB04LMuGB7ba3aog2xxN6N3g99ZfOboT-vdWXxrh_8`
- **Обращения**: `15XxSIpD_gMZaSOIrqDVCNI2EqBzphEGiG0ZNJ3HR8hI`
- **Акции**: `1V3-cPRq_SmbCbIzn1-CWSqD8pdpDqraq_GJ7LjMmwf8`
- **Аналитика**: `1Xq6bcxaDV2AEVWGqhaLlFcr6-hTNv0L5frXgPY-z7fU`
- **Google Drive (KB)**: `1JKjzWs3or3hn5ioCIqPBGHkZmgIN-OFf`

## Relay RU (обход белых списков ТСПУ) — VLESS Reality Bridge
- IP: `111.88.145.206` SSH: `ubuntu` (ключ ed25519 через US)
- Yandex Cloud, зона ru-central1-b, VM: epdmhc1f3rhjgkt36n95
- Xray VLESS Reality bridge → US 37.1.212.51:8443 (xHTTP)
- Порты: 443 (Vision), 2053 (gRPC), 8443 (xHTTP)
- UUID клиентский: `57ca4aae-dcb3-4fdd-9e14-f9afb42b703c`
- Reality: pbk=t4Icv6qrpPcxWOp9uxyLbL2cWJ5_QRcXcC1gJ06To1g sid=abcdef0123456789
- Private Key: `MF55pnfDEDvTYSeSuae0woG9LLlwyl6uWMLrESKeQkg`
- SNI: ozon.ru (+ www.ozon.ru, wildberries.ru, www.wildberries.ru)
- relay-bridge user на US: UUID eb4a1cf2-4235-4b0a-83b2-0e5a298389ed
- Outbound: VLESS xHTTP Reality к US:8443 (без flow)

## Важно
- При перезагрузке xray: systemctl restart vpn-panel.service
- BBR включён на обоих серверах

## Т-Банк Интернет-эквайринг (ИП Марченко Р.)
- **Terminal Key (тест)**: `1778844937330DEMO`
- **Пароль (тест)**: `oBDLqS9c34ydSNdZ`
- Магазин ID: 905483
- API: https://securepay.tinkoff.ru/v2/
- Документация: https://www.tbank.ru/kassa/dev/payments/
