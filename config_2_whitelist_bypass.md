# Конфиг 2: Обход белых списков (без VPN)

**Протокол:** VLESS + XHTTP через Cloudflare CDN  
**Когда использовать:** Мобильный интернет в центре, где работают только 2ГИС и Яндекс Go

## Ссылка для подключения (Hiddify / v2rayNG)
```
vless://eb4a1cf2-4235-4b0a-83b2-0e5a298389ed@d5d0lho2jtj1prft4f03.aqkd4clz.apigw.yandexcloud.net:443?type=splithttp&security=tls&sni=d5d0lho2jtj1prft4f03.aqkd4clz.apigw.yandexcloud.net&fp=chrome&host=d5d0lho2jtj1prft4f03.aqkd4clz.apigw.yandexcloud.net&path=%2Fycpath2026#Yandex-API-Bypass
```

## Что делает
- ✅ Работает при белых списках ТСПУ (трафик через IP Cloudflare)
- ✅ Даёт доступ в интернет (все сайты)
- ⚠️ Заблокированные сайты видят IP VPS (37.1.212.51, США)
- ⚠️ Российские сайты тоже через VPS

## Как подключить
1. Скопируйте ссылку выше
2. Hiddify/v2rayNG → Добавить сервер → Из буфера обмена
3. Подключитесь

## Примечание
> URL `trycloudflare.com` может меняться при перезапуске сервера.
> В этом случае нужно обновить ссылку.
