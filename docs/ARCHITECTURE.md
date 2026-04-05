# 🏗️ Архитектура VPN-инфраструктуры

> **Обновлено:** 05.04.2026  
> **⚠️ AI-агенты: этот документ обязателен к прочтению перед работой с проектом**

---

## Общая схема

```
┌──────────────┐     ┌──────────────────────────────┐
│  📱 Клиент   │────▶│  🇺🇸 US Server                │
│  Hiddify/Happ│     │  37.1.212.51                 │
│              │     │  Xray + Panel + Bot + WARP   │
└──────────────┘     └──────────────────────────────┘
       Прямое подключение
  (Vision/xHTTP/gRPC/WS/Hysteria2)
```

---

## US Server (37.1.212.51)

### Активные сервисы

| Сервис | Systemd unit | Порт | Описание |
|--------|-------------|------|----------|
| **Xray Core** | `xray.service` | 443, 8443, 2053, 2083, 2087 | Основной VPN: Vision, xHTTP, gRPC, WS, H2 |
| **Hysteria2** | `hysteria2.service` | 10443/UDP | UDP/QUIC VPN протокол |
| **VPN Panel** | `vpn-panel.service` | 8085 | Панель управления подписками |
| **Caddy** | `caddy.service` | 8086 | HTTPS reverse proxy (sslip.io SSL) |
| **VPN Bot** | `vpn-bot.service` | — | Telegram бот управления |
| **WARP** | `warp-svc.service` | wg0 | Cloudflare WARP (Google/YouTube routing) |
| **Galina Proxy** | `galina_proxy.service` | 8888 | Gemini AI proxy |
| **Nginx** | `nginx.service` | 9443 | Reverse proxy к Gemini API |
| **Cloudflared** | `cloudflared-tunnel.service` | — | Cloudflare Tunnel |

### Xray Inbounds (подробно)

| Tag | Порт | Транспорт | Security | SNI |
|-----|------|-----------|----------|-----|
| VLESS-Reality-Vision | 443 | tcp + xtls-rprx-vision | reality | www.microsoft.com |
| VLESS-Reality-XHTTP | 8443 | xhttp (stream-up) | reality | www.microsoft.com |
| VLESS-Reality-gRPC | 2053 | grpc | reality | www.microsoft.com |
| VLESS-WS | 2083 | websocket | none | — |
| VLESS-H2 | 2087 | h2 | reality | www.microsoft.com |

### Xray Routing

- **Google/YouTube/Gemini** → WARP (wg0, IPv4: 162.159.192.1:2408)
- **Приватные IP** → BLOCK
- **Всё остальное** → DIRECT

### Ключевые пути

| Путь | Содержание |
|------|-----------|
| `/root/vpn/` | Основной проект (panel, bot) — `vpn-panel` и `vpn-bot` работают отсюда |
| `/opt/openclaw/` | AI-бот OpenClaw + galina_proxy.py |
| `/etc/xray/config.json` | Конфиг основного Xray |
| `/etc/hysteria/` | Конфиг + сертификаты Hysteria2 |

---

## Подписки

| Тип | URL шаблон |
|-----|-----------|
| Hiddify / V2Ray | `http://37.1.212.51:8085/sub/hiddify/{TOKEN}` |
| Happ (iOS) | `https://37.1.212.51.sslip.io:8086/sub/happ/{TOKEN}` |

### Что содержит подписка:
- VLESS+Reality+Vision (443)
- VLESS+Reality+xHTTP (8443)
- VLESS+Reality+gRPC (2053) — только Hiddify
- VLESS+WS (2083)
- Hysteria2 (10443/UDP)

---

## Ключи и UUID

| Параметр | Значение |
|----------|---------|
| UUID | `eb4a1cf2-4235-4b0a-83b2-0e5a298389ed` (admin) |
| Reality Public Key | `n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4` |
| Reality Short ID | `0123456789abcdef` |
| SNI | `www.microsoft.com` |
| Hysteria2 Password | `HysteriaPassword2026` |

---

## Важные процедуры

### При перезапуске Xray:
```bash
systemctl restart xray
systemctl restart vpn-panel  # ОБЯЗАТЕЛЬНО — синхронизация пользователей
```

### При проблемах с Google/YouTube:
Проверить WARP: `curl --interface wg0 https://www.youtube.com`
