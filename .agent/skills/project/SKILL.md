---
name: project_context
description: Контекст VPN-проекта — инфраструктура, серверы, протоколы, процедуры
---

# 🔑 Project Context Skill

Этот skill содержит ключевой контекст VPN-проекта для эффективной работы AI-агента.

## Обязательные документы

Перед **любой** работой прочитай:

| Документ | Когда читать |
|----------|-------------|
| `docs/ARCHITECTURE.md` | **Всегда** — полная схема инфраструктуры |
| `docs/CREDENTIALS.md` | При SSH/API подключениях |
| `docs/YANDEX_BRIDGE.md` | При работе с Bridge |
| `docs/QUICK_START.md` | При запуске/остановке сервисов |

## Быстрый справочник

### Серверы
- **US:** `37.1.212.51` (SSH: `root / LEJ6U5chSK`)
- **Yandex VM:** `213.165.208.217` (SSH: `marketing` + ключ `ssh-key-1770366966512`)

### Активные сервисы на US
| Сервис | Unit | Порт |
|--------|------|------|
| Xray | `xray.service` | 443, 8443, 2053, 2083, 2087 |
| Hysteria2 | `hysteria2.service` | 10443/UDP |
| Panel | `vpn-panel.service` | 8085 |
| Caddy (HTTPS) | `caddy.service` | 8086 |
| Bot | `vpn-bot.service` | — |
| WARP | `warp-svc.service` | wg0 |
| Bridge Docker | `xray-yandex-bridge` | 8880, 8881 |

### Критические правила
1. **После перезапуска Xray** → обязательно `systemctl restart vpn-panel`
2. **Google/YouTube** → маршрутизируются через WARP (wg0)
3. **Reality SNI** → `www.microsoft.com`
4. **Проект работает из `/root/vpn/`** на сервере

### Подписки
- Hiddify: `http://37.1.212.51:8085/sub/hiddify/{TOKEN}`
- Happ iOS: `https://37.1.212.51.sslip.io:8086/sub/happ/{TOKEN}`

### Ключи шифрования
- UUID: `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed`
- Reality PBK: `n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4`
- Reality SID: `0123456789abcdef`

## Структура проекта

```
vpn/
├── docs/           # 📚 Документация (обязательна к прочтению)
├── panel/          # FastAPI панель управления подписками
│   ├── app.py      # API endpoints
│   ├── link_generator.py  # Генерация VLESS/Hysteria ссылок
│   ├── config.py   # Конфиг (порты, ключи, пути)
│   ├── models.py   # Pydantic модели
│   └── templates/  # UI (dashboard.html)
├── bot/            # Telegram бот
├── ssh-key-*/      # SSH ключ для Yandex VM
├── Caddyfile       # Caddy reverse proxy
├── GEMINI.md       # AI-агент конфигурация
└── _archive/       # Устаревшие файлы (НЕ трогать)
```
