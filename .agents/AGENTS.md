# VPN Project Rules

## Деплой VPN-инфраструктуры

При деплое кода панели на сервер:
1. Панель (`vpn-panel`) деплоится ТОЛЬКО на `37.1.212.51` (SCP → restart)
2. VPN-сервер `38.180.81.181` — только Xray, Caddy-прокси, SSH-туннель
3. Релей `185.4.67.223` — только Xray bridge + dokodemo-door
4. После деплоя панели — ВСЕГДА проверять: `curl http://37.1.212.51:8085/health`
5. После изменения кода — ОБЯЗАТЕЛЬНО обновить код на сервере:
   ```
   scp panel/*.py root@37.1.212.51:/root/vpn/panel/
   ssh root@37.1.212.51 "systemctl restart vpn-panel vpn-bot"
   ```
6. НИКОГДА не запускать vpn-panel на VPN-сервере 38.180.81.181
