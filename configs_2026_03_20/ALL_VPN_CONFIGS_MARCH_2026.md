# 🛡️ Итоговый список VPN конфигураций (21.03.2026)

Этот документ содержит все актуальные способы подключения к вашему серверу.

## 🟢 1. Универсальная подписка (Hiddify / Happ / V2Ray)
*Самый простой способ: вставьте ссылку в приложение и нажмите «Обновить».*
`http://37.1.212.51/configs/sub.txt`

---

## 🔐 2. Скрытные протоколы (Stealth - Порт 443)
*Рекомендуется для постоянного использования. Маскировка под системный трафик Apple/Yandex.*

**Shadow-TLS v3 + VLESS (Самый защищенный):**
`shadow-tls://ShadowPassword2026@37.1.212.51:443?sni=taxi.yandex.ru&version=3#🔐-ShadowTLS-v3`

**Hysteria2 (Быстрый UDP):**
`hysteria2://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?sni=taxi.yandex.ru&insecure=1#🚀-Hysteria2`

---

## ⚡ 3. Мобильные протоколы (Resilience)
*Лучшие для нестабильного 4G/5G и обхода жестких блокировок.*

**TUIC v5 (QUIC - порт 20443):**
`tuic://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed:eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:20443?congestion_control=bbr&sni=taxi.yandex.ru&alpn=h3&insecure=1#⚡-TUIC-v5`

**AmneziaWG (DPI-Resistant - порт 30443):**
`awg://EJNiKCiAmXsQ8kzfhg48uzRaYE5axjzRo0i+MNi5FUY=@37.1.212.51:30443?publickey=Y/YojY7CIdrhjuQck100y08DeRf/YdI/TvuyL21uYVY=&address=10.0.0.2/32&jc=4&jmin=40&jmax=70&s1=5&s2=10&h1=1&h2=2&h3=3&h4=4#🛡️-AmneziaWG`

---

## 🔌 4. Прямые VLESS-подключения (Reality)
*Надежная классика. Если другие протоколы не поддерживаются.*

**VLESS-Direct (Порт 10443):**
`vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:10443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#🔌-VLESS-Direct`

**VLESS-gRPC (Порт 18443):**
`vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:18443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&type=grpc&serviceName=grpc#📱-VLESS-gRPC`

**VLESS-XHTTP (Порт 443):**
`vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?encryption=none&security=reality&sni=taxi.yandex.ru&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&headerType=xhttp&type=xhttp&path=/secretpath2026&mode=packet-up#🌐-VLESS-XHTTP`

---

## 📱 5. Конфигурация для Amnezia App
*Скопируйте этот текст и вставьте в приложение Amnezia через «Add connection from JSON».*

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
        "public_key": "Y/YojY7CIdrhjuQck100y08DeRf/YdI/TvuyL21uYVY=",
        "s1": "5", "s2": "10"
      }
    }
  ],
  "host": "37.1.212.51"
}
```
