# 📋 Быстрая справка по серверу

## 🖥️ Основная информация

- **IP сервера:** 37.1.212.51
- **SSH:** root@37.1.212.51 (пароль: LEJ6U5chSK)
- **ОС:** Ubuntu 22.04.4 LTS

## 🔌 Порты (активные)

| Порт | Сервис | Процесс | Статус |
|------|--------|---------|--------|
| **22** | SSH | sshd (PID: 22125) | ✅ |
| **443** | VLESS + REALITY | xray (PID: 614977) | ✅ |
| **8080** | TinyProxy | tinyproxy (PID: 473255) | ✅ |
| **8000** | Marzban Web UI | Python/Uvicorn (PID: 614882) | ✅ localhost |
| **1080** | Shadowsocks | xray (PID: 614977) | ✅ |
| **44455** | Amnezia AWG | Docker | ✅ |
| **49576** | Amnezia WireGuard | Docker | ✅ |

## 🔐 VLESS + REALITY конфигурация

- **Порт:** 443
- **Протокол:** VLESS over TCP
- **Безопасность:** REALITY
- **Маскировка:** www.microsoft.com:443
- **Flow:** xtls-rprx-vision
- **UUID пользователя:** eb4a1cf2-4235-4b0a-83b2-0e5a298389ed
- **Public Key:** n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4

## 🔗 Ссылка подключения

```
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@37.1.212.51:443?type=tcp&security=reality&sni=www.microsoft.com&pbk=n5E8KcFHjef-ZC2mKjzkVldLJiLrsjfpE1Z-XmLfxH4&fp=chrome&flow=xtls-rprx-vision#VLESS-Reality
```

## 🐳 Docker контейнеры

- **marzban-marzban-1** - Marzban (VPN панель)
- **amnezia-wireguard** - WireGuard сервер
- **amnezia-awg** - AWG сервер

## 📁 Важные файлы на сервере

- `/var/lib/marzban/xray_config.json` - Конфигурация Xray
- `/opt/marzban/docker-compose.yml` - Docker конфигурация
- `/opt/marzban/.env` - Переменные окружения

## 🛠️ Полезные команды

```bash
# Статус контейнеров
docker ps

# Логи Marzban
docker logs marzban-marzban-1 -f

# Проверка портов
netstat -tlnp | grep 443

# Перезапуск Marzban
cd /opt/marzban && docker compose restart
```

## 📱 Клиентские файлы (на вашем компьютере)

- `vless_connection_link.txt` - Ссылка для подключения
- `amnezia_config.json` - JSON конфигурация
- `SERVER_CONFIGURATION_REPORT.md` - Полный отчет

---

**Полный отчет:** См. `SERVER_CONFIGURATION_REPORT.md`
