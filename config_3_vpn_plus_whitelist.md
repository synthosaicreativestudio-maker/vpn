# Конфиг 3: VPN + Обход белых списков

**Протокол:** VLESS + XHTTP через Cloudflare CDN + Smart-маршрутизация  
**Когда использовать:** Мобильный интернет в центре + нужны заблокированные сайты

## Ссылка для подключения (Hiddify / v2rayNG)
```
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@sapphire-wash-pieces-rangers.trycloudflare.com:443?type=xhttp&security=tls&sni=sapphire-wash-pieces-rangers.trycloudflare.com&fp=chrome&path=/secretpath2026&mode=auto#VPN-Bypass-Whitelist
```

## Что делает
- ✅ Работает при белых списках ТСПУ (трафик через Cloudflare CDN)
- ✅ Заблокированные сайты (YouTube, Instagram, Google) — через VPN
- ✅ Российские сайты — через VPN (но с IP VPS)
- ✅ Полный доступ ко всему интернету

## Как подключить
1. Скопируйте ссылку выше
2. Hiddify/v2rayNG → Добавить сервер → Из буфера обмена
3. Подключитесь

## Примечание
> Конфиги 2 и 3 используют одну и ту же серверную инфраструктуру.
> Разница в smart-маршрутизации будет настроена на сервере.
> URL `trycloudflare.com` может меняться при перезапуске сервера.
