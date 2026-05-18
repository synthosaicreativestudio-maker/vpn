---
name: project_context
description: Контекст VPN-проекта — инфраструктура, серверы, протоколы, процедуры
---

# 🔑 Project Context Skill

Этот skill содержит ключевой контекст VPN-проекта для эффективной работы AI-агента.

## ⛔ ЖЕЛЕЗНЫЕ ПРАВИЛА (НАРУШЕНИЕ ЗАПРЕЩЕНО)

> **ПРАВИЛО №1: НИКОГДА НЕ ТРОГАТЬ РАБОТАЮЩИЕ КОНФИГИ**
> При добавлении нового функционала (протокол, порт, SNI и т.д.)
> ЗАПРЕЩЕНО модифицировать или заменять существующие работающие конфигурации.
> Новый функционал ВСЕГДА добавляется как НОВЫЙ конфиг / НОВЫЙ протокол / НОВЫЙ inbound РЯДОМ с существующими.
> Старые работающие конфиги остаются без изменений.

> **ПРАВИЛО №2: МОДУЛЬНОСТЬ**
> Подключение или отключение любого модуля не должно ломать
> существующий функционал. Каждый новый канал — отдельный toggle в config.py.

> **ПРАВИЛО №3: ОБЯЗАТЕЛЬНО ЧИТАТЬ СКИЛЛЫ**
> Перед началом работы AI-агент ОБЯЗАН прочитать этот файл и docs/ARCHITECTURE.md.

## Обязательные документы

Перед **любой** работой прочитай:

| Документ | Когда читать |
|----------|-------------|
| `docs/ARCHITECTURE.md` | **Всегда** — полная схема инфраструктуры |
| `docs/CREDENTIALS.md` | При SSH/API подключениях |
| `docs/QUICK_START.md` | При запуске/остановке сервисов |

## Быстрый справочник

### Серверы
- **US:** `37.1.212.51` (SSH: `root / LEJ6U5chSK`)
- **Yandex VM (Relay):** `46.21.244.161` (SSH: `ubuntu`, ключ по умолчанию)

### Активные каналы на Yandex VM (Relay)
| Канал | Порт | SNI | Fingerprint | Статус |
|-------|------|-----|-------------|--------|
| Relay RU | 443 | ozon.ru | chrome | ✅ Рабочий |
| Антизаглушка 4G | 8081 | ads.x5.ru | edge | ✅ Рабочий |

### Активные сервисы на US
| Сервис | Unit | Порт |
|--------|------|------|
| Xray | `xray.service` | 443, 8443, 2053, 2083, 2087 |
| Hysteria2 | `hysteria2.service` | 10443/UDP |
| Panel | `vpn-panel.service` | 8085 |
| Caddy (HTTPS) | `caddy.service` | 8086 |
| Bot | `vpn-bot.service` | — |
| WARP | `warp-svc.service` | wg0 |

### Критические правила
1. **После перезапуска Xray** → обязательно `systemctl restart vpn-panel`
2. **Google/YouTube** → маршрутизируются через WARP (wg0)
3. **Reality SNI (US)** → `www.microsoft.com`
4. **Проект работает из `/root/vpn/`** на US сервере
5. **Xray конфиг (Yandex)** → `/usr/local/etc/xray/config.json`
6. **Xray конфиг (US)** → `/etc/xray/config.json`

### Подписки (3 ссылки в каждой)
- Hiddify: `http://37.1.212.51:8085/sub/hiddify/{TOKEN}`
- Happ iOS: `https://37.1.212.51.sslip.io:8086/sub/happ/{TOKEN}`

Каждая подписка содержит:
1. 🔌 Vision — прямое подключение к US серверу
2. 📡 Relay RU — через Яндекс VM (порт 443, ozon.ru)
3. 📶 Антизаглушка 4G — через Яндекс VM (порт 8081, ads.x5.ru)

### Ключи шифрования
- UUID (US): `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed`
- Reality PBK (US): `n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4`
- Reality SID (US): `0123456789abcdef`
- UUID (Relay): `57ca4aae-dcb3-4fdd-9e14-f9afb42b703c`
- Reality PBK (Relay): `p2EEfvTbaG9Qca4xKM4AxHVX1wFOqFut0Z4TX6T1wUg`
- Reality SID (Relay): `791cd192259bb2b9`

## Структура проекта

```
vpn/
├── .agent/skills/  # 📖 AI-скиллы (ОБЯЗАТЕЛЬНО читать!)
├── docs/           # 📚 Документация
├── panel/          # FastAPI панель управления подписками
│   ├── app.py      # API endpoints
│   ├── link_generator.py  # Генерация VLESS/Hysteria ссылок
│   ├── config.py   # Конфиг (порты, ключи, toggles)
│   ├── models.py   # Pydantic модели
│   └── templates/  # UI (dashboard.html)
├── bot/            # Telegram бот
├── ssh-key-*/      # SSH ключ для Yandex VM
├── Caddyfile       # Caddy reverse proxy
├── GEMINI.md       # AI-агент конфигурация
└── _archive/       # Устаревшие файлы (НЕ трогать)
```
