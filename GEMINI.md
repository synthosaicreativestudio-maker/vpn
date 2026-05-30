# VPN Project Configuration

## ⚠️ Обязательное чтение перед работой

AI-агент **ОБЯЗАН** прочитать следующие документы перед любыми изменениями:

1. **`docs/INCIDENT_LOG.md`** — ⚡ лог проблем и решений (ЧИТАТЬ ПЕРВЫМ! Содержит историю багов, фиксов и уроков)
2. **`docs/ARCHITECTURE.md`** — полная схема инфраструктуры, порты, сервисы, маршрутизация
3. **`docs/CREDENTIALS.md`** — актуальные доступы и ключи
4. **`docs/QUICK_START.md`** — процедуры запуска/остановки

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
- [highload_tuning](.agent/skills/security/highload_tuning.md) — Оптимизация под высокие нагрузки (sysctl, BBR, limits)
- [billing_security](.agent/skills/security/billing_security.md) — Безопасность биллинга и токенов подписок
- [traffic_obfuscation](.agent/skills/security/traffic_obfuscation.md) — Обфускация трафика (Hysteria2, AmneziaWG, Reality)
- [client_setup](.agent/skills/security/client_setup.md) — Настройка клиентских приложений и ссылки
- [backup_recovery](.agent/skills/security/backup_recovery.md) — Резервное копирование и восстановление
- [monitoring_alerts](.agent/skills/security/monitoring_alerts.md) — Автоматический мониторинг здоровья сервера и алерты
- [censorship_diagnostics](.agent/skills/security/censorship_diagnostics.md) — Диагностика точечных блокировок IP и TLS-handshake

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
8. **Режим диалога (КРИТИЧЕСКИ ВАЖНО):** Сначала агент задает вопросы, подробно изучает видение и проблематику пользователя, и только после взаимного согласования приступает к программированию или изменению кода.
9. **Лог инцидентов (ОБЯЗАТЕЛЬНО):** После любого исправления бага, решения проблемы или значимого изменения инфраструктуры — агент **ОБЯЗАН** добавить запись в `docs/INCIDENT_LOG.md` с датой, симптомами, диагностикой, решением и верификацией. Перед диагностикой новой проблемы — **СНАЧАЛА проверить INCIDENT_LOG.md** на наличие похожих инцидентов.


## Ключевые файлы

- `docs/INCIDENT_LOG.md` — ⚡ Лог проблем и решений (читать первым!)
- `docs/CREDENTIALS.md` — Все пароли и доступы
- `docs/ARCHITECTURE.md` — Архитектура инфраструктуры
