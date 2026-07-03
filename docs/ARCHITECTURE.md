# 🏗️ Архитектура VPN-инфраструктуры

> **Обновлено:** 03.07.2026  
> **⚠️ AI-агенты: этот документ обязателен к прочтению перед работой с проектом**

---

## Общая схема (3 сервера)

```
┌───────────────────────────────────────────────────────────┐
│  37.1.212.51 — Сервер подписок, бота и проектов (ID: 351340)  │
│                                                           │
│  Caddy :80/:8086 → Panel :8085                            │
│  vpn-panel.service   — Панель управления подписками       │
│  vpn-bot.service     — Telegram бот (@SintaMarketingBot)  │
│  rbn-max-bot.service — RBN Max Assistant Bot              │
│  vpn-relay-tunnel    — SSH-туннель gRPC к релею           │
│                                                           │
│  gRPC → 38.180.81.181:10085 (синхронизация юзеров с VPN)  │
│  gRPC → 127.0.0.1:10086 → relay (синхр. юзеров с релеем) │
└───────────────────────────────────────────────────────────┘
              ↕ gRPC (синхронизация юзеров)
┌───────────────────────────────────────────────────────────┐
│  38.180.81.181 — VPN-сервер (только VPN) (ID: 433343)     │
│                                                           │
│  Xray Core v26.5.9 — все VPN-протоколы                    │
│  gRPC API :10085   — для управления пользователями        │
│  Caddy :80/:8086   — проксирует /sub/* на 37.1.212.51     │
│                      (обратная совместимость старых ссылок)│
│  /ws-tunnel        — WebSocket VPN на :2083               │
│                                                           │
│  ⛔ НЕТ панели, НЕТ бота (только VPN + Caddy-прокси)      │
└───────────────────────────────────────────────────────────┘
              ↑ VPN-трафик от клиентов через релей
┌───────────────────────────────────────────────────────────┐
│  185.4.67.223 — РФ-релей (ID: 433815)                     │
│                                                           │
│  Xray VLESS Reality Bridge                                │
│  DNS: sub.synthosai.ru → 185.4.67.223                     │
│                                                           │
│  VPN-трафик (к 38.180.81.181):                            │
│    :443  (relay-vision) → US:443  (Vision TCP)            │
│    :2053 (relay-grpc)   → US:2053 (gRPC H2)               │
│    :8443 (relay-xhttp)  → US:8443 (xHTTP)                 │
│                                                           │
│  Подписки (к 37.1.212.51 — dokodemo-door):                │
│    :80   (relay-http-80)    → Panel:80                    │
│    :8086 (relay-https-8086) → Panel:8086                  │
│                                                           │
│  gRPC API :10085 — для синхронизации юзеров (через SSH)   │
└───────────────────────────────────────────────────────────┘
```

### Принцип разделения ролей

| Сервер | Роль | Что НЕ должно быть |
|--------|------|---------------------|
| `37.1.212.51` | Панель, бот, проекты | Xray VPN |
| `38.180.81.181` | Только VPN (Xray) | Панель, бот |
| `185.4.67.223` | Релей (мост в РФ) | Панель, бот |

---

## Сервер подписок (37.1.212.51)

### Активные сервисы

| Сервис | Systemd unit | Порт | Описание |
|--------|-------------|------|----------|
| **VPN Panel** | `vpn-panel.service` | 8085 | Панель управления подписками (FastAPI) |
| **Caddy** | `caddy.service` | 80 / 8086 | HTTP/HTTPS reverse proxy |
| **VPN Bot** | `vpn-bot.service` | — | Telegram-бот управления подписками |
| **RBN Bot** | `rbn-max-bot.service` | — | RBN Max Assistant Bot |
| **Relay Tunnel** | `vpn-relay-tunnel.service` | — | SSH-туннель к gRPC API релея |

### Ключевые переменные `.env`

```env
SERVER_IP=38.180.81.181          # IP VPN-сервера (для генерации ссылок)
XRAY_GRPC_HOST=38.180.81.181:10085  # gRPC API Xray на VPN-сервере
RELAY_ENABLED=True
RELAY_IP=185.4.67.223            # IP РФ-релея
RELAY_GRPC_ENABLED=True
RELAY_GRPC_HOST=127.0.0.1:10086  # gRPC релея через SSH-туннель
```

---

## VPN-сервер (38.180.81.181)

### Активные сервисы

| Сервис | Systemd unit | Порт | Описание |
|--------|-------------|------|----------|
| **Xray Core** | `xray.service` | 443, 8443, 2053, 2083, 2085 | VPN v26.5.9 |
| **Caddy** | `caddy.service` | 80 / 8086 | Проксирует /sub/* на `37.1.212.51:8085` |
| **Relay Tunnel** | `vpn-relay-tunnel.service` | — | SSH-туннель gRPC к релею |

### Xray Inbounds

| Tag | Порт | Транспорт | Security | SNI | Описание |
|-----|------|-----------|----------|-----|----------|
| VLESS-Reality-Vision | 443 | tcp + xtls-rprx-vision | reality | dzen.ru | Основной канал |
| VLESS-Reality-XHTTP | 8443 | xhttp (stream-up) | reality | dzen.ru | Резервный |
| VLESS-Reality-gRPC | 2053 | grpc | reality | dzen.ru | Мультиплексный |
| VLESS-WS | 2083 | websocket | none | — | Устаревший резерв |

> ⚠️ **SNI:** `dzen.ru` вместо `www.microsoft.com` — серверы Akamai (Microsoft) отдают несовместимые TLS-ответы на Xray v26.5.9.

---

## РФ-Релей (185.4.67.223)

| Параметр | Значение |
|----------|---------|
| DNS | `sub.synthosai.ru` → `185.4.67.223` |
| Xray | v26.5.9 |
| Роль | VLESS Reality Bridge → US + Dokodemo-door подписки → Panel |
| UUID клиентский | `57ca4aae-dcb3-4fdd-9e14-f9afb42b703c` |
| SNI (входящий) | ozon.ru, wildberries.ru, yandex.ru, dzen.ru |
| SSH доступ | `ubuntu@185.4.67.223` ключ `id_ed25519` (через VPN-сервер или панельный) |

### Маршрутизация на релее

| Входящий тег | Порт | Назначение | Протокол |
|-------------|------|-----------|----------|
| relay-vision | 443/TCP | → US:443 (VPN Vision) | VLESS Reality |
| relay-grpc | 2053/TCP | → US:2053 (VPN gRPC) | VLESS Reality |
| relay-xhttp | 8443/TCP | → US:8443 (VPN xHTTP) | VLESS Reality |
| relay-http-80 | 80/TCP | → Panel:80 (подписки HTTP) | dokodemo-door |
| relay-https-8086 | 8086/TCP | → Panel:8086 (подписки HTTPS) | dokodemo-door |

---

## Подписки

### Доступные URL
| Тип | URL шаблон |
|-----|-----------|
| Универсальная | `http://sub.synthosai.ru/sub/{TOKEN}` |
| Hiddify | `http://sub.synthosai.ru/sub/hiddify/{TOKEN}` |
| Happ (iOS) | `http://sub.synthosai.ru/sub/happ/{TOKEN}` |
| С маршрутизацией | Добавить `?routing=ru` |
| Admin UI | `https://37.1.212.51.sslip.io:8086/admin/ui` |

### Содержимое Happ-подписки (3 протокола)
1. `📡 @username (Relay RU new)` — Vision через релей (TCP, основной)
2. `📡 @username (gRPC Relay RU new)` — gRPC через релей (HTTP/2, резервный)
3. `🔌 @username (Vision)` — Прямой к US (аварийный, для WiFi без РФ-блокировок)

---

## Важные процедуры

### При перезапуске Xray на VPN-сервере (US):
```bash
ssh root@38.180.81.181
systemctl restart xray
# Панель на 37.1.212.51 автоматически пересинхронизирует юзеров при следующем запуске
ssh root@37.1.212.51 "systemctl restart vpn-panel"
```

### При перезапуске Xray на релее (RU):
```bash
# Через VPN-сервер (jump host):
ssh root@38.180.81.181
ssh -i /root/.ssh/id_ed25519 ubuntu@185.4.67.223
sudo systemctl restart xray
# Перезапустить SSH-туннели:
ssh root@38.180.81.181 "systemctl restart vpn-relay-tunnel"
ssh root@37.1.212.51 "systemctl restart vpn-relay-tunnel"
# Панель пересинхронизирует юзеров:
ssh root@37.1.212.51 "systemctl restart vpn-panel"
```

### Полный перезапуск:
```bash
# 1. VPN-сервер
ssh root@38.180.81.181 "systemctl restart xray caddy vpn-relay-tunnel"
# 2. Панельный сервер
ssh root@37.1.212.51 "systemctl restart vpn-panel vpn-bot caddy vpn-relay-tunnel"
# 3. Релей (через jump)
ssh root@38.180.81.181 "ssh -i /root/.ssh/id_ed25519 ubuntu@185.4.67.223 'sudo systemctl restart xray'"
```

---

## Оптимизация соединений

Для предотвращения зомби-сессий от мобильных клиентов:
1. **Таймаут простоя (`connIdle`):** 90 секунд (по умолчанию 300)
2. **TCP Keep-Alive (`tcpKeepAliveInterval`):** 15 секунд — ОС разрывает мёртвые сокеты

---

## Локальная раздача гео-файлов

GitHub заблокирован в РФ, поэтому файлы `geoip.dat` и `geosite.dat` раздаются с нашего сервера:
* `http://sub.synthosai.ru/sub/geo/geoip.dat`
* `http://sub.synthosai.ru/sub/geo/geosite.dat`

---

## 🛡️ Резервное копирование и автоматический откат (Blue-Green Failover)

Для обеспечения непрерывной работы инфраструктуры каждый из 3 серверов оснащен изолированной системой автоматического контроля работоспособности (Failover) и архивом стабильных сборок.

### Схема резервных копий по серверам

| Сервер | Компонент | Рабочая директория | Директория бэкапов | Стабильная копия (Rollback target) |
|---|---|---|---|---|
| **VPN (38.180.81.181)** | Xray Core | `/usr/local/bin/xray`<br>`/etc/xray/config.json` | `/usr/local/bin/builds/`<br>`/etc/xray/builds/` | `/usr/local/bin/xray.stable`<br>`/etc/xray/config.json.stable` |
| **Панель (37.1.212.51)** | FastAPI + Bot | `/root/vpn/panel/`<br>`/root/vpn/bot/` | `/etc/vpn-panel/builds/` | `/etc/vpn-panel/panel.stable/`<br>`/etc/vpn-panel/bot.stable/` |
| **Релей (185.4.67.223)** | Xray Bridge | `/usr/local/bin/xray`<br>`/usr/local/etc/xray/config.json` | `/usr/local/bin/builds/`<br>`/usr/local/etc/xray/builds/` | `/usr/local/bin/xray.stable`<br>`/usr/local/etc/xray/config.json.stable` |

### Принцип работы автоотката

На каждом сервере по планировщику `cron` каждую минуту запускается индивидуальный скрипт мониторинга (`xray-failover.sh`, `panel-failover.sh`, `relay-failover.sh`):

1. **Проверка жизнеспособности:** Скрипт проверяет активность соответствующей службы в systemd и доступность ее сетевых портов/эндпоинтов.
2. **Обнаружение сбоя:** Если служба неактивна или не отвечает на тестовые запросы, инициируется процедура автоматического отката.
3. **Восстановление:** Скрипт заменяет текущие исполняемые файлы и конфигурации стабильными копиями из директории `.stable` и перезапускает службу.
4. **Оповещение:** Отправляется лог-сообщение в Telegram-канал мониторинга с деталями инцидента.

