# VPN Project Configuration

## ⚠️ Обязательное чтение перед работой

AI-агент **ОБЯЗАН** прочитать следующие документы перед любыми изменениями:

1. **`docs/ARCHITECTURE.md`** — полная схема инфраструктуры, порты, сервисы, маршрутизация
2. **`docs/CREDENTIALS.md`** — актуальные доступы и ключи
3. **`docs/YANDEX_BRIDGE.md`** — при работе с Bridge
4. **`docs/QUICK_START.md`** — процедуры запуска/остановки

## Структура проекта

```
vpn/
├── docs/                # 📚 Вся документация (ОБЯЗАТЕЛЬНО к прочтению)
├── panel/               # Панель управления подписками (FastAPI)
├── bot/                 # Telegram бот
├── ssh-key-*/           # SSH ключ для Yandex VM
├── Caddyfile            # Caddy HTTPS reverse proxy конфиг
└── _archive/            # Архив устаревших файлов (НЕ трогать)
```

## Skills

### Локальные Security Skills
- [vpn_protocols](.agent/skills/security/vpn_protocols.md) — VLESS, REALITY, WireGuard
- [network_diagnostics](.agent/skills/security/network_diagnostics.md) — Сетевая диагностика
- [censorship_evasion](.agent/skills/security/censorship_evasion.md) — Обход DPI и блокировок
- [osint_recon](.agent/skills/security/osint_recon.md) — OSINT и leak-тесты
- [server_hardening](.agent/skills/security/server_hardening.md) — Защита сервера

### Project Skill
- [project_context](.agent/skills/project/SKILL.md) — Контекст проекта и инфраструктуры

## Правила для этого проекта

1. **Reality SNI:** `www.microsoft.com` (для всех Reality inbounds)
2. **Yandex VM SNI routing:** `taxi.yandex.ru` → Reality на порту 443
3. **UUID сервера:** `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed`
4. **US сервер:** `37.1.212.51`
5. **Yandex VM:** `213.165.208.217`
6. **При перезапуске Xray** — всегда перезапускать `vpn-panel` (синхронизация пользователей)
7. **При диагностике VPN** — использовать команды из `network_diagnostics.md`
8. **При проблемах с блокировками** — использовать `censorship_evasion.md`
9. **Google/YouTube** маршрутизируются через WARP (wg0)

## Ключевые файлы

- `docs/CREDENTIALS.md` — Все пароли и доступы
- `docs/ARCHITECTURE.md` — Архитектура инфраструктуры
- `docs/YANDEX_BRIDGE.md` — Настройка Bridge
