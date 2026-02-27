# Конфиг 3: VPN + Обход белых списков

**Протокол:** VLESS + XHTTP через Cloudflare CDN + Smart-маршрутизация  
**Когда использовать:** Мобильный интернет в центре + нужны заблокированные сайты

## Ссылка для подключения (Hiddify / v2rayNG)
```
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@d5d0lho2jtj1prft4f03.aqkd4clz.apigw.yandexcloud.net:443?type=splithttp&security=tls&sni=d5d0lho2jtj1prft4f03.aqkd4clz.apigw.yandexcloud.net&fp=chrome&host=d5d0lho2jtj1prft4f03.aqkd4clz.apigw.yandexcloud.net&path=%2Fycpath2026#VPN-Yandex-API-Bypass
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
