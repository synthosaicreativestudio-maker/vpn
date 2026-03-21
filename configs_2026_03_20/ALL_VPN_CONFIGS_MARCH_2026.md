# 📖 Главная Книга Конфигураций (Март 2026) — ФИНАЛЬНАЯ СИНХРОНИЗАЦИЯ 🚀

В этом документе — результат глубокой отладки сети. Все порты разведены и проверены.

---

## 📱 Ссылки для Hiddify / Happ (Актуальные порты)

**1. Автоматическая подписка**
# 🗺 Карта VPN Конфигураций (Март 2026 — Финал)

Все службы переведены на **независимую (decoupled)** архитектуру для 100% стабильности.

## 🟢 Активные Протоколы

| Протокол | Порт | Маскировка (SNI) | Особенности |
| :--- | :--- | :--- | :--- |
| **Shadow-TLS v3** | 443 (TCP) | taxi.yandex.ru | Премиум маскировка (Pass: `SecureShadow2026V3`) |
| **VLESS-Vision** | 10443 (TCP) | taxi.yandex.ru | Прямое Reality соединение |
| **VLESS-xHTTP** | 10444 (TCP) | taxi.yandex.ru | Обход DPI (Path: `/secretpath2026`) |
| **VLESS-gRPC** | 18443 (TCP) | taxi.yandex.ru | Для мобильных сетей |
| **TUIC v5** | 30445 (UDP) | taxi.yandex.ru | Высокая скорость, низкий пинг |
| **Hysteria2** | 10443 (UDP) | microsoft.com | Протокол на базе QUIC |
| **AmneziaWG** | 30443 (UDP) | - | Кастомный WireGuard |

## 🔗 Основные Ссылки

### 📱 Hiddify / Happ
- **Подписка**: `http://37.1.212.51/configs/sub.txt`
- **Файл со списком**: [HIDDIFY_LINKS.txt](file:///Users/verakoroleva/Desktop/vpn/configs_2026_03_20/HIDDIFY_LINKS.txt)

---
*Статус: Проверено. Все порты LISTEN. Конфликты устранены.*
## 🛡️ Amnezia App Status
- **AmneziaWG**: Порт **30443** (UDP). Проверьте файл [AMNEZIA_CONFIG.txt](file:///Users/verakoroleva/Desktop/vpn/configs_2026_03_20/AMNEZIA_CONFIG.txt).
