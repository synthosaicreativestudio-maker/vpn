# Все доступы (обновлено 03.07.2026)

## Серверы

| Роль | IP | ID | SSH | Описание |
|------|----|----|-----|----------|
| **Панель + Бот** | `37.1.212.51` | 351340 | `root / VrT2ApnS3J` | Подписки, Telegram бот, проекты |
| **VPN (только)** | `38.180.81.181` | 433343 | `root / VrT2ApnS3J` | Xray Core, все VPN-протоколы |
| **РФ-релей** | `185.4.67.223` | 433815 | `ubuntu` (ключ `id_ed25519` через панельный или VPN сервер) | VLESS Reality Bridge |

## VPN каналы на US-сервере (38.180.81.181)

| # | Протокол | Порт | SNI |
|---|----------|------|-----|
| 1 | VLESS+Reality+Vision | 443/TCP | dzen.ru |
| 2 | VLESS+Reality+xHTTP | 8443/TCP | dzen.ru |
| 3 | VLESS+Reality+gRPC | 2053/TCP | dzen.ru |
| 4 | VLESS+WS | 2083/TCP | — |

Reality: `pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4` `sid=0123456789abcdef`
UUID: `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed`

## Relay RU (185.4.67.223)

| Параметр | Значение |
|----------|---------|
| UUID клиентский | `57ca4aae-dcb3-4fdd-9e14-f9afb42b703c` |
| Reality pbk | `t4Icv6qrpPcxWOp9uxyLbL2cWJ5_QRcXcC1gJ06To1g` |
| Reality sid | `abcdef0123456789` |
| Private Key | `MF55pnfDEDvTYSeSuae0woG9LLlwyl6uWMLrESKeQkg` |
| SNI входящий | ozon.ru, wildberries.ru, yandex.ru, dzen.ru |
| VPN порты | 443 (Vision), 2053 (gRPC), 8443 (xHTTP) → US |
| Подписки порты | 80, 8086 (dokodemo-door) → Panel 37.1.212.51 |
| DNS | `sub.synthosai.ru` → `185.4.67.223` |

## Подписки (на сервере 37.1.212.51)

| Тип | URL |
|-----|-----|
| Панель (Admin UI) | `https://37.1.212.51.sslip.io:8086/admin/ui` |
| Happ (iOS) | `http://sub.synthosai.ru/sub/happ/{TOKEN}` |
| Hiddify | `http://sub.synthosai.ru/sub/hiddify/{TOKEN}` |
| API Key | `b534ef20bdea908d3b9b4f5388467d525ba88f7abaddcc5ca8b4c159b75335c3` |

## API Ключи и Токены

- **Telegram Bot Token**: `8232668997:AAH1oMWo7ZqnwjVX2GH3avEjPrCTNK2kVmc` (Username: `@SintaMarketingBot`)
- **Gemini API Key**: `AIzaSyD5WGVM1AqIjhszcGEprqOo-PwrldExmQs`
- **Gemini Server Key**: `AIzaSyBu1hTc7tJ87h-4otHp3j36Hs4LDSvyFl4` (установлен на VPN-сервере)
- **Anthropic (Claude) Key**: `sk-ant-api03-***`

## Google Sheets & Drive IDs
- **Авторизация (список)**: `1_SB04LMuGB7ba3aog2xxN6N3g99ZfOboT-vdWXxrh_8`
- **Обращения**: `15XxSIpD_gMZaSOIrqDVCNI2EqBzphEGiG0ZNJ3HR8hI`
- **Акции**: `1V3-cPRq_SmbCbIzn1-CWSqD8pdpDqraq_GJ7LjMmwf8`
- **Аналитика**: `1Xq6bcxaDV2AEVWGqhaLlFcr6-hTNv0L5frXgPY-z7fU`
- **Google Drive (KB)**: `1JKjzWs3or3hn5ioCIqPBGHkZmgIN-OFf`

## Т-Банк Интернет-эквайринг (ИП Марченко Р.)
- **Terminal Key (тест)**: `1778844937330DEMO`
- **Пароль (тест)**: `oBDLqS9c34ydSNdZ`
- Магазин ID: 905483
- API: https://securepay.tinkoff.ru/v2/
- Документация: https://www.tbank.ru/kassa/dev/payments/

## Важные правила

- При перезагрузке Xray на VPN-сервере → перезапустить панель на `37.1.212.51`
- При перезагрузке Xray на релее → перезапустить SSH-туннели на обоих серверах
- BBR включён на всех серверах
