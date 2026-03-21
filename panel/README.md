# 🛡️ Subscription Manager Panel — Documentation

Решение для управления VPN-подписками через Xray gRPC (Март 2026).

## 🚀 Обзор
Панель представляет собой независимый FastAPI-сервис, который взаимодействует с Xray-core через gRPC. Она позволяет создавать пользователей, генерировать ссылки для различных протоколов и ограничивать количество одновременных IP-подключений.

### Ключевые возможности:
- **6 протоколов**: VLESS (Reality, xHTTP, gRPC), Shadow-TLS v3, TUIC v5, Hysteria 2.
- **gRPC управление**: Добавление/удаление пользователей без перезагрузки Xray.
- **IP Limiter**: Фоновый мониторинг `access.log` и логирование нарушений лимитов.
- **Безопасность**: Middleware стек (Rate limit, CORS, Security Headers).
- **Hiddify Ready**: Совместимость со ссылками и форматом подписки Hiddify.

---

## 🏗️ Архитектура
Проект полностью автономен и не зависит от Telegram-бота.

```mermaid
graph TD
    User([Пользователь]) -- "HTTPS /sub/{token}" --> FastAPI[FastAPI App]
    Admin([Админ]) -- "X-API-KEY /users" --> FastAPI
    FastAPI -- "gRPC" --> Xray[Xray Core]
    FastAPI -- "CRUD" --> SQLite[(SQLite DB)]
    LogParser[IP Limiter] -- "Парсинг" --> AccessLog[/var/log/xray/access.log]
    LogParser -- "Запись" --> SQLite
```

---

## 🛠️ Установка и запуск

### 1. Подготовка
Убедитесь, что Xray запущен с включенным gRPC API на порту `10085`.

### 2. Настройка окружения
Cкопируйте шаблон и заполните его:
```bash
cp panel/.env.example panel/.env
# Обязательно сгенерируйте и установите собственный PANEL_API_KEY
```

### 3. Запуск через Docker (Рекомендуемо)
```bash
cd panel
docker build -t vpn-panel .
docker run -d --name vpn-panel -p 8085:8085 --network host vpn-panel
```

### 4. Локальный запуск
```bash
cd panel
pip install -r requirements.txt
cd proto && bash generate.sh
cd ..
uvicorn panel.app:app --host 0.0.0.0 --port 8085
```

---

## 🔒 Безопасность
Панель защищена на нескольких уровнях:

1.  **API Key**: Все админ-эндпоинты требуют заголовок `X-API-KEY`.
2.  **Rate Limiting**: Ограничение запросов через `slowapi` (защита от DDoS).
3.  **CORS**: Разрешены только доверенные домены.
4.  **Security Headers**: Включены заголовки `X-Frame-Options`, `X-Content-Type-Options` и др.
5.  **Isolation**: Процесс запущен от имени пользователя `panel` (non-root) в Docker.

---

## 📖 API Reference
Полное описание эндпоинтов доступно в [API.md](./API.md).
Инструкция по безопасности сервера в [SECURITY.md](./SECURITY.md).

---

## 🪵 Логи и отладка
- Логи панели: `docker logs vpn-panel`
- База данных: `panel/data/panel.db`
- Документация Swagger: `http://<server-ip>:8085/docs`
