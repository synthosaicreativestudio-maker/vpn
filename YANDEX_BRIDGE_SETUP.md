# 🌉 Yandex Bridge VPN — Полная документация

> **Статус:** ✅ Работает  
> **Последнее обновление:** 22.03.2026  
> **Ссылка для Hiddify:**
> ```
> vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@213.165.208.217:8880?encryption=none&security=none&type=xhttp&host=37.1.212.51.sslip.io&path=/ya-bridge#Yandex-VM-Bridge
> ```

---

## 📐 Архитектура

```
┌─────────────┐     ┌───────────────────┐     ┌──────────────────────┐     ┌──────────┐
│  📱 Телефон │────▶│  🇷🇺 Yandex VM     │────▶│  🇺🇸 US Server        │────▶│ Интернет │
│  (Hiddify)  │     │  213.165.208.217  │     │  37.1.212.51         │     │          │
│             │     │  socat :8880      │     │  xray-bridge :8880   │     │          │
└─────────────┘     └───────────────────┘     └──────────────────────┘     └──────────┘
     VLESS+xHTTP         TCP-форвард              VLESS→DIRECT
```

**Принцип работы «Матрёшка»:**

1. **Телефон** подключается к российскому IP Яндекс VM (`213.165.208.217:8880`) по протоколу VLESS+xHTTP
2. **Yandex VM** (socat) прозрачно перебрасывает TCP-пакеты на US сервер (`37.1.212.51:8880`)
3. **US сервер** (Docker: `xray-yandex-bridge`) принимает VLESS, расшифровывает и отправляет трафик в интернет напрямую (outbound: `DIRECT`)

**Для мобильного оператора** это выглядит как обычное соединение с российским сервером Яндекса — не блокируется.

---

## 🖥️ Компонент 1: US сервер (37.1.212.51)

### Docker-контейнер `xray-yandex-bridge`

**Расположение конфига:** `/opt/yandex-bridge/config.json`  
**Docker Compose:** `/opt/yandex-bridge/docker-compose.yml`  
**Порт:** `8880` (TCP)  
**Режим сети:** `host` (контейнер использует сеть хоста)

#### Конфигурация Xray (`config.json`):

```json
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "tag": "VLESS-Yandex-Bridge",
      "protocol": "vless",
      "listen": "0.0.0.0",
      "port": 8880,
      "settings": {
        "clients": [
          {
            "id": "eb4a1cf2-4235-4b0a-83b2-0e5a298389ed",
            "email": "admin-yandex-bridge"
          }
        ],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "xhttp",
        "xhttpSettings": { "path": "/ya-bridge" }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls"]
      }
    }
  ],
  "outbounds": [
    { "protocol": "freedom", "tag": "DIRECT" }
  ]
}
```

#### Docker Compose (`docker-compose.yml`):

```yaml
version: "3"
services:
  xray-yandex-bridge:
    image: ghcr.io/xtls/xray-core:latest
    container_name: xray-yandex-bridge
    network_mode: host
    restart: unless-stopped
    volumes:
      - ./config.json:/etc/xray/config.json:ro
```

#### Управление:

```bash
# Статус
docker ps | grep bridge

# Логи
docker logs --tail 50 xray-yandex-bridge

# Перезапуск
docker restart xray-yandex-bridge

# Полная пересборка
cd /opt/yandex-bridge && docker compose up -d
```

---

### Caddy (reverse proxy для CDN)

**Файл:** `/etc/caddy/Caddyfile`

```caddyfile
37.1.212.51.sslip.io:8086 {
    reverse_proxy 127.0.0.1:8085
}

:80 {
    handle /ya-bridge* {
        reverse_proxy 127.0.0.1:8880
    }
    handle {
        respond "OK" 200
    }
}
```

> ⚠️ **КРИТИЧЕСКИ ВАЖНО:** Блок `:80` с маршрутом `/ya-bridge` необходим для работы Yandex CDN. Если Caddyfile перезаписать без этого блока — мост сломается!

#### Управление:

```bash
# Перезагрузка конфига
systemctl reload caddy

# Проверка
curl -I http://127.0.0.1:80/ya-bridge
# Ожидаемый ответ: 404 Not Found (это нормально — Xray отвечает)
```

---

## 🖥️ Компонент 2: Yandex VM (213.165.208.217)

### TCP-форвардер `socat`

**Задача:** Прозрачно перебрасывать весь TCP-трафик с порта 8880 на US сервер.

```bash
# Запуск
sudo nohup socat TCP-LISTEN:8880,fork,reuseaddr TCP:37.1.212.51:8880 &>/dev/null &

# Проверка
ps aux | grep socat | grep -v grep
sudo ss -tlnp | grep 8880

# Остановка
sudo pkill -9 socat
```

> ⚠️ **НЕ использовать `redir`!** Он создаёт тысячи форков и нестабилен. Только `socat`.

#### Автозапуск (systemd сервис):

Для надёжности рекомендуется создать systemd-сервис:

```bash
sudo cat > /etc/systemd/system/socat-bridge.service << 'EOF'
[Unit]
Description=Socat Bridge to US VPN
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:8880,fork,reuseaddr TCP:37.1.212.51:8880
Restart=always
RestartSec=3
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable socat-bridge
sudo systemctl start socat-bridge
```

### Firewall (UFW)

```bash
# Порт 8880 должен быть открыт
sudo ufw allow 8880/tcp
sudo ufw allow 8880/udp
```

---

## ☁️ Компонент 3: Yandex Cloud CDN (опционально)

**Статус:** Создан, но **не активирован** (DNS CNAME не прописан).

| Параметр | Значение |
|----------|----------|
| ID ресурса | `bc8rsopxtjygp4sayoai` |
| Группа источников | `common-37-1-212-51-sslip-io` |
| Домен | `cdn.my-test-vpn.ru` |
| Протокол | HTTP |
| Host заголовок | `37.1.212.51.sslip.io` |
| CNAME | `7c58b852939393e5.topology.gslb.yccdn.ru` |

**Для активации CDN нужно:**
1. Зарегистрировать реальный домен
2. Прописать CNAME-запись в DNS
3. В группе источников указать порт `8880`
4. Включить POST-методы в настройках HTTP-методов

> Без CDN мост работает напрямую через `socat` — CDN не обязателен.

---

## 📱 Настройка клиента (Hiddify)

### Ссылка для подключения:

```
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@213.165.208.217:8880?encryption=none&security=none&type=xhttp&host=37.1.212.51.sslip.io&path=/ya-bridge#Yandex-VM-Bridge
```

### Параметры вручную:

| Параметр | Значение |
|----------|----------|
| Протокол | VLESS |
| Адрес | `213.165.208.217` |
| Порт | `8880` |
| UUID | `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed` |
| Шифрование | none |
| Безопасность (TLS) | none |
| Транспорт | xhttp |
| Host | `37.1.212.51.sslip.io` |
| Path | `/ya-bridge` |

---

## 🔧 Устранение неполадок

### «Пинг есть, связи нет»

1. **Проверить socat на Yandex VM:**
   ```bash
   ssh marketing@213.165.208.217
   ps aux | grep socat | grep -v grep
   # Если нет процессов → перезапустить:
   sudo systemctl restart socat-bridge
   ```

2. **Проверить Docker-мост на US сервере:**
   ```bash
   ssh root@37.1.212.51
   docker logs --tail 10 xray-yandex-bridge
   # Должны быть строки "accepted" с IP Яндекс VM (213.165.208.217)
   ```

3. **Проверить маршрут в Caddy:**
   ```bash
   curl -I http://127.0.0.1:80/ya-bridge
   # Ответ 404 = норма (Xray отвечает)
   # Ответ 308 = ПРОБЛЕМА: Caddy потерял маршрут /ya-bridge!
   ```

### Caddy потерял маршрут `/ya-bridge`

Это самая частая причина поломки. Если кто-то перезаписал `/etc/caddy/Caddyfile` без блока `:80`:

```bash
# Восстановить Caddyfile (см. секцию Caddy выше)
systemctl reload caddy
```

### Docker-контейнер не запускается

```bash
docker logs xray-yandex-bridge
# Если ошибка "VLESS deprecated" — это предупреждение, не ошибка
# Если "config error" — проверить /opt/yandex-bridge/config.json
```

---

## 🔄 Точки восстановления

| Сервер | Путь |
|--------|------|
| US | `/root/recovery_20260322_235027.tar.gz` |
| Yandex VM | `/home/marketing/recovery_20260322_185036.tar.gz` |

```bash
# Откат US сервера:
ssh root@37.1.212.51
cd / && tar xzf /root/recovery_20260322_235027.tar.gz
systemctl restart xray caddy
docker restart xray-yandex-bridge

# Откат Yandex VM:
ssh marketing@213.165.208.217
cd / && sudo tar xzf /home/marketing/recovery_20260322_185036.tar.gz
sudo systemctl restart socat-bridge
```

---

## 🏗️ Связь с другими компонентами

| Компонент | Порт | Влияние на мост |
|-----------|------|----------------|
| Основной Xray | 443, 8443, 2053, 2083 | ❌ Не влияет (изолирован) |
| Hysteria2 | 10443 | ❌ Не влияет |
| VPN Panel | 8085 (HTTP), 8086 (HTTPS) | ❌ Не влияет |
| Telegram Bot | — | ❌ Не влияет |
| **Caddy** | **80, 8086** | **⚠️ ВЛИЯЕТ** — маршрут `/ya-bridge` |
| **Yandex Bridge** | **8880** | **✅ Основной компонент** |

> 🔑 **Главное правило:** Мост полностью изолирован от остальной инфраструктуры. Единственное слабое место — Caddyfile. При любых изменениях Caddy **обязательно** сохранять блок `:80 { handle /ya-bridge }`.
