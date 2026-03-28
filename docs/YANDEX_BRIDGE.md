# 🌉 Yandex Bridge VPN — Документация

> **Статус:** ✅ Работает  
> **Последнее обновление:** 28.03.2026  
> **Транспорт на Yandex VM:** nginx stream (заменён socat)

---

## 📐 Архитектура

```
┌─────────────┐     ┌───────────────────┐     ┌──────────────────────┐     ┌──────────┐
│  📱 Телефон │────▶│  🇷🇺 Yandex VM     │────▶│  🇺🇸 US Server        │────▶│ Интернет │
│  (Hiddify)  │     │  213.165.208.217  │     │  37.1.212.51         │     │          │
│             │     │  nginx stream     │     │  xray-bridge :8880   │     │          │
└─────────────┘     └───────────────────┘     └──────────────────────┘     └──────────┘
     VLESS+xHTTP      TCP-форвард (nginx)        VLESS→DIRECT/WARP
```

**Принцип работы «Матрёшка»:**

1. **Телефон** подключается к российскому IP Яндекс VM (`213.165.208.217:8880`) по протоколу VLESS+xHTTP
2. **Yandex VM** (nginx stream) прозрачно перебрасывает TCP-пакеты на US сервер (`37.1.212.51:8880`)
3. **US сервер** (Docker: `xray-yandex-bridge`) принимает VLESS, расшифровывает и отправляет трафик в интернет

**Для мобильного оператора** это выглядит как обычное соединение с российским сервером Яндекса — не блокируется.

---

## 🖥️ Компонент 1: US сервер (37.1.212.51)

### Docker-контейнер `xray-yandex-bridge`

**Расположение конфига:** `/opt/yandex-bridge/config.json`  
**Docker Compose:** `/opt/yandex-bridge/docker-compose.yml`  
**Порты:** `8880` (xHTTP), `8881` (WebSocket)  
**Режим сети:** `host`

#### Управление:

```bash
# Статус
docker ps | grep bridge

# Логи
docker logs --tail 50 xray-yandex-bridge

# Перезапуск
docker restart xray-yandex-bridge
```

---

## 🖥️ Компонент 2: Yandex VM (213.165.208.217)

### TCP-форвардер: nginx stream (замена socat)

**Конфиг:** В `/etc/nginx/nginx.conf` → блок `stream {}`

```nginx
stream {
    # ... SNI routing для порта 443 ...

    # VPN Bridge TCP forwarding
    upstream us_bridge_xhttp {
        server 37.1.212.51:8880;
    }
    upstream us_bridge_ws {
        server 37.1.212.51:8881;
    }
    server {
        listen 8880;
        proxy_pass us_bridge_xhttp;
        proxy_timeout 300s;
        proxy_connect_timeout 10s;
    }
    server {
        listen 8881;
        proxy_pass us_bridge_ws;
        proxy_timeout 300s;
        proxy_connect_timeout 10s;
    }
}
```

#### Управление:

```bash
# Проверка конфига
sudo nginx -t

# Перезагрузка
sudo systemctl reload nginx

# Проверка портов
sudo ss -tlnp | grep -E '888[01]'
# Должен быть nginx на обоих портах
```

> ⚠️ **socat и redir больше НЕ используются.** Они удалены. Весь TCP-форвардинг через nginx stream.

### SSH подключение к Yandex VM

```bash
ssh marketing@213.165.208.217 -i ssh-key-1770366966512/ssh-key-1770366966512
```

### UFW (Firewall)

```
22/tcp    — SSH
80/tcp    — Nginx HTTP
443/tcp   — Nginx HTTPS + SNI routing
8880/tcp  — VPN Bridge xHTTP
8881/tcp  — VPN Bridge WS
```

---

## 📱 Подписки (обновляются автоматически)

### Ссылки подписок (автообновление каждые 12 часов):

| Клиент | URL подписки |
|--------|-------------|
| **Hiddify** | `http://37.1.212.51:8085/sub/hiddify/{TOKEN}` |
| **Happ** | `http://37.1.212.51:8085/sub/happ/{TOKEN}` |
| **Универсальная** | `http://37.1.212.51:8085/sub/{TOKEN}` |

### Что получает каждый клиент:

| Протокол | Hiddify | Happ |
|----------|---------|------|
| VLESS+Reality+Vision (443) | ✅ | ✅ |
| VLESS+Reality+xHTTP (8443) | ✅ | ✅ |
| VLESS+Reality+gRPC (2053) | ✅ | ❌ (не поддерживает) |
| VLESS+WS (2083) | ✅ | ✅ |
| Hysteria2 (10443) | ✅ | ✅ |
| **Yandex Bridge xHTTP (8880)** | ✅ | ✅ |
| **Yandex Bridge WS (8881)** | ✅ | ✅ |

---

## 🔧 Устранение неполадок

### Bridge не работает

1. **Проверить nginx stream на Yandex VM:**
   ```bash
   ssh marketing@213.165.208.217
   sudo ss -tlnp | grep -E '888[01]'
   # Должен быть nginx
   ```

2. **Проверить Docker-мост на US сервере:**
   ```bash
   ssh root@37.1.212.51
   docker logs --tail 10 xray-yandex-bridge
   ```

3. **Проверить маршрут:**
   ```bash
   curl -s -o /dev/null -w '%{http_code}' http://213.165.208.217:8880/ya-bridge
   # 404 = нормально (Xray отвечает)
   # Connection refused = nginx не слушает
   ```

---

## 🏗️ Связь с другими компонентами

| Компонент | Порт | Влияние на мост |
|-----------|------|----------------|
| Основной Xray | 443, 8443, 2053, 2083 | ❌ Не влияет |
| Hysteria2 | 10443 | ❌ Не влияет |
| VPN Panel | 8085 (HTTP), 8086 (HTTPS) | ❌ Не влияет |
| Gemini API Proxy | 9443 (nginx) | ❌ Не влияет |
| **Nginx stream** | **8880, 8881** | **✅ Основной компонент bridge** |

---

## ✅ Оптимизации (март 2026)

- **BBR** включён на обоих серверах (ускорение TCP)
- **nginx stream** вместо socat (стабильнее, нет fork-бомб)
- **UFW** включён на Yandex VM
- **redir удалён** (apt remove)
- **xray-relay отключён** (мёртвый компонент)
