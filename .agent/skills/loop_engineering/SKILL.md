---
name: Loop Engineering
description: Автономный рабочий цикл агента — Discover→Plan→Execute→Verify→Iterate. Используй для задач требующих итеративного улучшения без ручного контроля каждого шага.
version: 1.0.0
---

# 🔄 Loop Engineering

Эволюция промпт-инжиниринга: вместо одного идеального запроса — **автономная система**, где агент сам ставит задачу, планирует, выполняет, проверяет и корректирует до достижения цели.

---

## Рабочий цикл (The Loop)

```
TRIGGER → DISCOVER → PLAN → EXECUTE → VERIFY
                               ↑           |
                               └── ITERATE ←┘ (при ошибке)
```

### 1. 🔍 Discover — Обнаружение
Определяет проблему, контекст и **exit condition** (критерий успеха).

Чеклист:
- Читать `INCIDENT_LOG.md` — была похожая проблема?
- Читать `ARCHITECTURE.md` — текущая схема
- Определить scope (какие файлы/сервисы затронуты)
- Сформулировать exit condition

**Триггеры:** ошибка пользователя / алерт мониторинга / `/goal` / провальный health-check

### 2. 📋 Plan — Планирование
Декомпозирует задачу на атомарные шаги с зависимостями.

Правила:
1. Каждый шаг — конкретное действие (команда, файл, API-вызов)
2. Шаги упорядочены по зависимостям
3. Для каждого шага есть критерий успеха
4. Есть rollback-план на случай сбоя

**Инструмент:** создай `task.md` с чеклистом `[ ]` / `[/]` / `[x]`

### 3. ⚡ Execute — Выполнение
Принципы:
- Один шаг за раз (не параллелить зависимые)
- Бэкап перед деструктивными операциями: `cp config.json config.json.pre.$(date +%s)`
- Коммитить атомарно (одна задача = один коммит)

### 4. ✅ Verify — Проверка
Тестирует результат против exit conditions.

Чеклист для VPN-проекта:
```bash
ruff check .
curl -s http://37.1.212.51:8085/health
ssh root@38.180.81.181 "systemctl is-active xray"
for port in 443 8443 2053; do nc -zv 38.180.81.181 $port 2>&1; done
ssh root@38.180.81.181 "warp-cli --accept-tos status"
```

Вердикты:
- ✅ PASS — все критерии выполнены, цикл завершён
- ❌ FAIL — есть ошибки, переход в Iterate
- ⚠️ PARTIAL — уточнить scope и повторить

### 5. 🔁 Iterate — Итерация
При FAIL — анализируй ошибку и возвращайся к Plan с новыми данными.

Принципы:
1. НЕ делать то же самое снова — всегда добавлять новую информацию
2. Уменьшать scope (изолировать причину)
3. Обновить `INCIDENT_LOG.md` с новыми данными
4. Max 3 итерации — если не решено, эскалировать

---

## Роль скиллов в Loop Engineering

| Скилл | Фаза | Что экономит |
|-------|------|--------------|
| `network_diagnostics.md` | Discover | Диагностические команды |
| `censorship_evasion.md` | Plan | Знания о DPI/ТСПУ |
| `client_setup.md` | Execute | Параметры клиентов |
| `monitoring_alerts.md` | Verify | Команды health-check |
| `backup_recovery.md` | Execute | Процедуры бэкапа |
| `project_context` | Всегда | Архитектура + credentials |

---

## Готовые петли (Playbooks)

### Петля: VPN упал
```
DISCOVER: Читать INCIDENT_LOG → проверить xray.service + порты 443/2053/8443
PLAN:
  → Порты не слушают → xray-failover.sh (откат)
  → WARP: warp-cli --accept-tos status + restart warp-svc
  → Релей: SSH-туннели + SNI совпадение (dzen.ru)
EXECUTE: Применить исправление
VERIFY: health endpoint + nc -zv ports + xray логи
ITERATE: Если всё ещё нет → reboot VPS через панель хостера
```

### Петля: Клиент не подключается
```
DISCOVER: ОС (iOS/Android/Windows), провайдер, протокол
PLAN:
  → Android + мобильный оператор → Relay (Vision Relay, gRPC Relay)
  → iOS + xHTTP → Vision (xHTTP несовместим с iOS background)
  → Россия → geoip:ru + geosite:category-ru в routing профиле
EXECUTE: Обновить подписку / дать новую ссылку
VERIFY: Пользователь подтверждает подключение
```

### Петля: Код изменился
```
DISCOVER: Scope (какие файлы, какие сервисы)
PLAN: ruff → scp → restart → verify → commit → push
EXECUTE: Деплой на 37.1.212.51
VERIFY: ruff check . + health endpoint
ITERATE: Откат через .stable файлы если что
```

---

## Anti-patterns

| ❌ Плохо | ✅ Хорошо |
|----------|----------|
| Менять несколько вещей сразу | Атомарные изменения по одному |
| Пропускать Verify | Верифицировать после каждого шага |
| Игнорировать INCIDENT_LOG | Читать лог ПЕРЕД диагностикой |
| Слепо доверять алертам | Ручная проверка при подозрительных алертах |
| `git push` без `ruff check` | ruff → commit → push |

---

## Активация

Этот скилл активируется при:
- `/goal` — длинная автономная задача
- `/learn` — итерация по обучению
- Любой задаче с неопределённым решением

**Всегда начинать с:** `INCIDENT_LOG.md` → `ARCHITECTURE.md` → exit condition
