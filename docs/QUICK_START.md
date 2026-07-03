# 🚀 Быстрый запуск и управление VPN

Инфраструктура разделена на 3 сервера. Подписки генерируются панелью на `37.1.212.51` и выдаются через Telegram-бота.

---

## 📱 Как получить конфигурацию (пользователю)

1. **Через Telegram-бота:** `@SintaMarketingBot`
2. **Через Admin UI:** `https://37.1.212.51.sslip.io:8086/admin/ui`
3. **Формат ссылок подписки:**
   - **Happ (iOS):** `http://sub.synthosai.ru/sub/happ/{TOKEN}`
   - **Hiddify:** `http://sub.synthosai.ru/sub/hiddify/{TOKEN}`

---

## 🛠️ Управление сервисами

### Сервер подписок (37.1.212.51)

```bash
ssh root@37.1.212.51

# Перезапуск панели
systemctl restart vpn-panel vpn-bot

# Проверка статуса
systemctl is-active vpn-panel vpn-bot caddy vpn-relay-tunnel

# Проверка здоровья
curl http://127.0.0.1:8085/health
```

### VPN-сервер (38.180.81.181)

```bash
ssh root@38.180.81.181

# Перезапуск Xray
systemctl restart xray
# ⚠️ После рестарта Xray — обязательно перезапустить панель!
ssh root@37.1.212.51 "systemctl restart vpn-panel"

# Проверка статуса
systemctl is-active xray caddy vpn-relay-tunnel
```

### РФ-Релей (185.4.67.223)

```bash
# Доступ только через jump host (VPN-сервер или панельный)
ssh root@38.180.81.181
ssh -i /root/.ssh/id_ed25519 ubuntu@185.4.67.223

# Перезапуск Xray на релее
sudo systemctl restart xray

# После рестарта — перезапустить SSH-туннели
exit  # вернуться на VPN-сервер
systemctl restart vpn-relay-tunnel
ssh root@37.1.212.51 "systemctl restart vpn-relay-tunnel vpn-panel"
```

---

## 🔍 Диагностика

```bash
# Проверка подписки через панель
curl -s http://37.1.212.51:8085/sub/happ/{TOKEN} | base64 -d

# Проверка через релей
curl -s http://185.4.67.223/health

# Проверка VPN через Caddy
curl -s http://38.180.81.181/health

# Число протоколов в Happ-подписке (должно быть 3)
curl -s http://37.1.212.51:8085/sub/happ/{TOKEN} | base64 -d | wc -l
```

---

## ⚠️ Важно

- **Панель работает ТОЛЬКО на `37.1.212.51`** — никогда не запускать на VPN-сервере
- При изменении кода панели → SCP файлы на `37.1.212.51:/root/vpn/panel/` → restart
- DNS `sub.synthosai.ru` указывает на релей `185.4.67.223`
- Happ подписка содержит строго 3 протокола (Vision Relay, gRPC Relay, Vision Direct)
