# 📖 API Reference — Subscription Manager

Все запросы к административным эндпоинтам должны содержать заголовок `X-API-KEY`.

## 🛡️ Безопасность
- **Base URL**: `http://<server-ip>:8085`
- **Auth**: `X-API-KEY: <ваш_ключ>`
- **Rate Limit**: 10 запросов/минута (запись), 30 запросов/минута (чтение).

---

## 👥 Управление пользователями

### 1. Создать пользователя
`POST /users`

**Request Body:**
```json
{
  "email": "user@example.com",
  "uuid": "eb4a1cf2-4235-4b0a-83b2-0e5a298389ed",
  "ip_limit": 2,
  "expire_days": 30,
  "description": "Premium user"
}
```

**Response (201 Created):**
```json
{
  "email": "user@example.com",
  "uuid": "...",
  "ip_limit": 2,
  "created_at": "2026-03-21T...",
  "expires_at": "2026-04-20T...",
  "is_active": true,
  "sub_token": "..."
}
```

### 2. Список пользователей
`GET /users`

**Response:**
```json
{
  "users": [...],
  "count": 5
}
```

### 3. Удалить пользователя
`DELETE /users/{email}`

---

## 🔗 Подписки и ссылки

### 4. Получить ссылки пользователя
`GET /users/{email}/links`

**Response:**
```json
{
  "email": "user@example.com",
  "vless_reality": "vless://...",
  "vless_xhttp": "vless://...",
  "vless_grpc": "vless://...",
  "shadow_tls": "shadow-tls://...",
  "tuic": "tuic://...",
  "hysteria2": "hysteria2://...",
  "all_links": ["...", "..."]
}
```

### 5. Публичный эндпоинт подписки (БЕЗ API KEY)
`GET /sub/{token}`

Используется в Hiddify для авто-обновления. Возвращает текстовый список всех ссылок в открытом виде (HTTP).

### 5.1. Подписка для Apple/Sing-Box (БЕЗ API KEY)
`GET /sub/happ/{token}`

Используется для строгих iOS-клиентов (например, Happ). Возвращает список всех ссылок, закодированный в Base64.
Обычно работает через HTTPS Caddy-прокси (`https://....sslip.io:8086/sub/happ/{token}`).

---

## 📊 Мониторинг и диагностика

### 6. Статистика
`GET /stats`

### 7. Здоровье сервиса
`GET /health`

### 8. Активные IP пользователя
`GET /users/{email}/ips`
Позволяет увидеть, с каких IP сейчас подключен пользователь и не превышен ли лимит.
