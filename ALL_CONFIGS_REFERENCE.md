# 📋 VPN — Актуальная конфигурация

**Дата:** 15 марта 2026

---

## Основной VPN (VLESS + REALITY)

**Для чего:** Обход блокировок (YouTube, Instagram, Google, Telegram). Российские сайты идут напрямую.

**Приложения:** Hiddify, v2rayNG, Amnezia VPN

```
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?type=tcp&security=reality&sni=www.microsoft.com&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision&seed=happ-vpn-premium-2026#VPN-Smart-Main
```

**Цепочка:** Телефон → VPS (37.1.212.51, США) → Интернет  
**Маскировка:** REALITY — DPI видит TLS к www.microsoft.com  
**DNS:** Зашифрован (DNS-over-HTTPS через 1.1.1.1 + 8.8.8.8)  
**Smart-маршрутизация:**
- ✅ YouTube, Instagram, Google, Telegram — через VPN
- ✅ Яндекс, VK, Госуслуги, Сбербанк, Ozon, WB — напрямую (без VPN)

---

## Запасной VPN (AmneziaWG)

**Для чего:** Тот же VPN, но другой протокол. Используйте, если VLESS заблокируют.

**Приложение:** Amnezia VPN (уже настроен на Mac/iPhone)

**Примечание:** Конфиг хранится внутри приложения Amnezia. Для переноса на новое устройство используйте кнопку «Поделиться» в приложении.

---

## Серверная инфраструктура

| Компонент | Значение |
|-----------|----------|
| **Сервер** | 37.1.212.51 (США, Chicago) |
| **Порт** | 443 (стандартный HTTPS) |
| **Панель** | Marzban |
| **Xray версия** | 26.2.6 |
| **DNS** | DNS-over-HTTPS (1.1.1.1 + 8.8.8.8) |
| **SNI** | www.microsoft.com |
| **Flow** | xtls-rprx-vision + Seed |
| **WARP** | ❌ Отключён (экономия RAM) |

---

## Улучшения от 15.03.2026

1. ✅ **DNS-over-HTTPS** — сайты больше не определяют страну через утечку DNS
2. ✅ **SNI сменён** с taxi.yandex.ru на www.microsoft.com — меньше подозрений у DPI
3. ✅ **Seed + Padding** — рандомный шум в пакетах, труднее распознать VPN
4. ✅ **WARP отключён** — освобождено 146 MB RAM, сервер стабильнее
5. ✅ **Yandex VM relay** — убран (больше не используется)
