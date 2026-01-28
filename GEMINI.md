# VPN Project Configuration

## Skills

Этот проект использует следующие skills для автоматического применения best practices:

### Локальные Security Skills
- [vpn_protocols](.agent/skills/security/vpn_protocols.md) — VLESS, REALITY, WireGuard
- [network_diagnostics](.agent/skills/security/network_diagnostics.md) — Сетевая диагностика
- [censorship_evasion](.agent/skills/security/censorship_evasion.md) — Обход DPI и блокировок
- [osint_recon](.agent/skills/security/osint_recon.md) — OSINT и leak-тесты
- [server_hardening](.agent/skills/security/server_hardening.md) — Защита сервера

### Глобальные Skills (из ~/.agent/skills/)
- coding — Написание и отладка кода
- coding_debugging — Polyglot, рефакторинг, тесты
- communication — Форматирование, отчёты
- engineering_advanced — API Design, архитектура
- planning — Планирование задач

## Правила для этого проекта

1. **Всегда использовать SNI: taxi.yandex.ru** — это актуальная конфигурация
2. **UUID сервера:** eb4a1cf2-4235-4b0a-83b2-0e5a298389ed
3. **Сервер:** 37.1.212.51:443
4. **При диагностике VPN** — использовать команды из network_diagnostics.md
5. **При проблемах с блокировками** — использовать censorship_evasion.md
6. **При настройке сервера** — использовать server_hardening.md

## Ключевые файлы

- `ALL_CREDENTIALS.md` — Все пароли и доступы
- `vless_connection_link.txt` — Актуальная ссылка подключения
- `xray_config_yandex.json` — Эталонный серверный конфиг
