# 🛡️ Актуальные настройки VPN (21.03.2026)

Этот файл содержит всё необходимое для подключения. Все протоколы поддерживают автоматическое переключение и разблокировку Google Gemini.

## 🔗 1. Универсальная подписка (Hiddify / Happ)
**Самый простой и надежный способ.** Скопируйте ссылку и добавьте её в приложение:

`http://37.1.212.51/configs/sub.txt`

---

## 📋 2. Прямые ссылки (Manual)
Для ручного добавления или старых приложений:

### 🚀 VLESS-Main (Wi-Fi)
`vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#🚀-VLESS-Main`

### 🛡️ VLESS-XHTTP (Mobile)
`vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:8444?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&sid=00&type=xhttp&path=/secretpath2026&mode=packet-up#🛡️-VLESS-XHTTP-Mobile`

### 📡 VLESS-gRPC (Backup)
`vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:18443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&sid=00&type=grpc&serviceName=grpc#📡-VLESS-gRPC`

### ⚡ Hysteria2 (Fallback)
`hysteria2://HysteriaPassword2026@37.1.212.51:10443?sni=ya.ru&insecure=1#⚡-Hysteria2-Fast`

---

## 📂 Описание файлов в папке configs_2026_03_20:
*   `hy_pack.json` — Полный конфиг для **Hiddify**.
*   `happ_config.json` — Полный конфиг для **Happ**.
*   `amnezia_config.json` — Конфиг для **Amnezia**.
*   `xray_config_yandex.json` — Конфиг для **Сервера**.
*   `sub.txt` — Файл подписки (Base64), который грузится в приложение.
*   `raw_sub.txt` — Исходный список ссылок (то же, что и выше).
