# VPN Project Configuration

## ⚠️ Обязательное чтение перед работой

AI-агент **ОБЯЗАН** прочитать следующие документы перед любыми изменениями:

1. **`docs/ARCHITECTURE.md`** — полная схема инфраструктуры, порты, сервисы, маршрутизация
2. **`docs/CREDENTIALS.md`** — актуальные доступы и ключи
3. **`docs/QUICK_START.md`** — процедуры запуска/остановки

## Структура проекта

```
vpn/
├── docs/                # 📚 Вся документация (ОБЯЗАТЕЛЬНО к прочтению)
├── panel/               # Панель управления подписками (FastAPI)
├── bot/                 # Telegram бот
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
2. **UUID сервера:** `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed`
3. **US сервер:** `37.1.212.51`
4. **При перезапуске Xray** — всегда перезапускать `vpn-panel` (синхронизация пользователей)
5. **При диагностике VPN** — использовать команды из `network_diagnostics.md`
6. **При проблемах с блокировками** — использовать `censorship_evasion.md`
7. **Google/YouTube** маршрутизируются через WARP (wg0)

## Ключевые файлы

- `docs/CREDENTIALS.md` — Все пароли и доступы
- `docs/ARCHITECTURE.md` — Архитектура инфраструктуры

