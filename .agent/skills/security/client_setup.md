---
name: Client Setup & UX Support
description: Client app configuration (Hiddify, Happ, FoXray, V2rayN), subscription format, client troubleshooting
version: 1.0.0
---

# 📱 Client Setup & UX Support

Этот skill содержит инструкции для быстрой настройки клиентских приложений и решения проблем пользователей (iOS, Android, Windows, macOS).

---

## 🔌 Рекомендуемые приложения (Clients)

| ОС | Рекомендуемые приложения | Протоколы | Особенности |
|----|--------------------------|-----------|-------------|
| **iOS** | Happ, FoXray, Shadowrocket, Streisand | VLESS-Reality, Hysteria2 | Happ/FoXray бесплатные, Shadowrocket платный, но стабильный |
| **Android** | Hiddify, v2rayNG, Nekobox | VLESS-Reality, Hysteria2 | Hiddify — самый простой интерфейс для пользователей |
| **Windows** | Hiddify, v2rayN, Nekoray | VLESS-Reality, Hysteria2 | Hiddify настраивает системный прокси автоматически |
| **macOS** | Hiddify, FoXray, V2rayXS | VLESS-Reality, Hysteria2 | Hiddify поддерживает работу в режиме TUN-интерфейса |

---

## 📝 Форматы ссылок для импорта подписок

1. **VLESS-Reality (содержит публичный ключ и SNI):**
   ```text
   vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?encryption=none&flow=xtls-r-vision&security=reality&sni=www.microsoft.com&fp=chrome&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&sid=0123456789abcdef#US-Reality-Direct
   ```
2. **Hysteria 2 (UDP-туннель):**
   ```text
   hysteria2://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:10443?insecure=1&sni=www.microsoft.com#US-Hysteria2
   ```

---

## 🛠 Устранение неполадок у пользователей (Troubleshooting)

### 1. Ошибка «Не удается подключиться к серверу» (Timeout)
* **Проверить провайдера:** Если у пользователя мобильный интернет (особенно МТС, Мегафон, Tele2), провайдер может блокировать UDP-порт Hysteria2. Предложите переключиться на профиль **Relay RU** или **Vision (TCP)**.
* **Синхронизация времени:** На клиентском устройстве системное время должно быть синхронизировано с точностью до 1 минуты. Если время сбито, TLS-рукопожатие Xray Reality будет отклонено сервером.

### 2. VPN подключен, но интернет не работает (DNS Leak / Routing)
* **Решение:** В настройках приложения (например, Hiddify) переключить режим работы DNS с «системного» на «1.1.1.1» или «8.8.8.8». 
* Включить режим **TUN (Туннелирование всего трафика)** вместо «Системного прокси».

### 3. Ошибка сертификата (в Hysteria2)
* **Решение:** Убедитесь, что в конфигурации Hysteria клиента включена опция `allowInsecure: true` (или параметр `insecure=1` в ссылке), если используется самоподписанный сертификат.
