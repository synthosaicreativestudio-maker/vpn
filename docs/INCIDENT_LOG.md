# 📋 Лог инцидентов и решений

> Документ фиксирует все значимые проблемы, их диагностику и принятые решения.  
> **Новые записи добавлять в начало файла (самые свежие сверху).**

---

## 2026-05-30 — VPN отключается в Happ после подключения домена

### Симптомы
- VPN в Happ (iOS) самопроизвольно отключается
- Проблема появилась после подключения домена `sub.synthosai.ru`
- Ранее гипотеза связывала с утечками в xHTTP

### Диагностика
1. **Xray v26.3.27** содержал подтверждённый баг утечки памяти в xHTTP `stream-up/stream-one` (GitHub PR [#6095](https://github.com/XTLS/Xray-core/pull/6095)):
   - HTTP body не закрывался при обрыве соединения
   - Outbound считал upstream ещё живым → зависал
   - Горутины утекали → Xray деградировал → VPN отваливался
2. **DnsHosts в Happ-профиле** не содержал записи для `sub.synthosai.ru`:
   - При обновлении подписки DNS мог пойти через VPN-туннель → петля маршрутизации → обрыв
3. Дополнительно найден баг [#6204](https://github.com/XTLS/Xray-core/issues/6204) — core crash при malformed DNS FQDN >255 символов, тоже исправлен после v26.5.9

### Решение
| # | Действие | Детали |
|---|----------|--------|
| 1 | **Обновление Xray** до v26.5.9 на US (37.1.212.51) | Был v26.3.27. Backup: `/usr/local/bin/xray.backup.v26.3.27` |
| 2 | **Обновление Xray** до v26.5.9 на Relay (111.88.145.206) | Был v26.3.27. Backup: `/usr/local/bin/xray.backup.v26.3.27` |
| 3 | **Добавление DnsHosts** `sub.synthosai.ru → 111.88.145.206` | В `panel/app.py`, `_HAPP_ROUTING_PROFILE` |
| 4 | Перезапуск всех сервисов | xray, vpn-panel, vpn-bot |

### Верификация
- [x] US Xray v26.5.9 — active
- [x] Relay Xray v26.5.9 — active
- [x] vpn-panel — active, xray_connected: true
- [x] vpn-bot — active
- [x] `https://sub.synthosai.ru:8086/health` → HTTP 200
- [ ] Мониторинг стабильности VPN в Happ в течение 24-48 часов

### Коммит
- `5809552` — fix: add sub.synthosai.ru to Happ DnsHosts

### Источники
- [PR #6095: Fix potential memory leak in stream-up/one](https://github.com/XTLS/Xray-core/pull/6095)
- [Issue #6204: core stop randomly](https://github.com/XTLS/Xray-core/issues/6204)
- [Issue #5944: iOS high memory usage](https://github.com/XTLS/Xray-core/issues/5944) — открыт, мониторим

---

## Шаблон для новых записей

<!--
## ГГГГ-ММ-ДД — Краткое описание

### Симптомы
- Что наблюдалось

### Диагностика
1. Что было найдено

### Решение
| # | Действие | Детали |
|---|----------|--------|

### Верификация
- [ ] Проверка 1

### Коммит
- `hash` — описание
-->
