# 📖 Главная Книга Конфигураций (Март 2026) — АКТУАЛЬНО 🚀

В этом документе собраны все финальные и проверенные ссылки для вашего мощного VPN.

---

## 📱 Ссылки для Hiddify / Happ (Лучший выбор)

**1. Автоматическая подписка (New Subscription)**
`http://37.1.212.51/configs/sub.txt`

**2. Резервные прямые ссылки (Добавить из буфера)**
- `shadow-tls://ShadowPassword2026@37.1.212.51:443?sni=taxi.yandex.ru&version=3#🔐-ShadowTLS-v3`
- `tuic://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed:eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:20443?congestion_control=bbr&sni=taxi.yandex.ru&alpn=h3&insecure=1#⚡-TUIC-v5`
- `hysteria2://HysteriaPassword2026@37.1.212.51:10443?sni=www.microsoft.com&insecure=1#🚀-Hysteria2`
- `vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:10443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#🔌-VLESS-Direct`
- `vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:8444?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&type=xhttp&mode=packet-up&path=/secretpath2026#🕵️-VLESS-xHTTP(Stealth)`
- `vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:18443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&type=grpc&serviceName=grpc#📡-VLESS-gRPC(Stealth)`

---

## 🛡️ Конфиги для Amnezia App

**1. Протокол AmneziaWG (через "Добавить через JSON")**
```json
{
  "containers": [
    {
      "container": "amnezia-awg",
      "port": "30443",
      "protocol": "awg",
      "settings": {
        "address": "10.0.0.2",
        "h1": "1", "h2": "2", "h3": "3", "h4": "4",
        "jc": "4", "jmax": "70", "jmin": "40",
        "mtu": "1280",
        "private_key": "EJNiKCiAmXsQ8kzfhg48uzRaYE5axjzRo0i+MNi5FUY=",
        "public_key": "+K1x0KsIzca4NniWr6wBqYZl6gCi+D4x989Sf7zP9AQ=",
        "s1": "5", "s2": "10"
      }
    }
  ],
  "host": "37.1.212.51"
}
```

**2. VLESS ссылки для Amnezia**
- `vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#🚀-Amnezia-VLESS-Reality`

---

## 🌐 Полезные ресурсы
- **CDN-Bridge (Cloudflare)**: [Инструкция в walkthrough.md](file:///Users/verakoroleva/.gemini/antigravity/brain/07f89542-f909-4444-af27-57fb61c56ba2/walkthrough.md)
- **Статус сервера**: `http://37.1.212.51:8080` (Marzban Dashboard)
