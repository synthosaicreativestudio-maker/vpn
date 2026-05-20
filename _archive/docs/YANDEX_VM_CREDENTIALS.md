# 🔐 ДАННЫЕ ДОСТУПА И СЕКРЕТЫ ПРОЕКТА (Yandex VM & US Proxy)

Этот документ содержит все актуальные ключи, IP-адреса и учетные данные, собранные из истории проекта и конфигурационных файлов.

---

## 🖥️ 1. Yandex Cloud VM (Основной сервер в РФ)
Бот и основная логика работают здесь.

| Параметр | Значение |
|----------|----------|
| **Публичный IP** | `213.165.208.217` |
| **Пользователь** | `marketing` |
| **Рабочая директория** | `/home/marketing/marketingbot` |
| **SSH Ключ (локально)** | `~/.ssh/yc_marketing_new` |
| **SSH Ключ (в проекте)** | `ssh-key-1770366966512/ssh-key-1770366966512` |

**Команда для подключения:**
```bash
ssh marketing@89.169.176.108 -i ssh-key-1770366966512/ssh-key-1770366966512
```

---

## 🇺🇸 2. US Proxy Server (Прокси для Gemini API)
Используется для обхода блокировок Google Gemini в РФ.

| Параметр | Значение |
|----------|----------|
| **IP-адрес** | `37.1.212.51` |
| **Пользователь** | `root` |
| **Пароль** | `LEJ6U5chSK` |
| **SSH Порт** | `22` |
| **TinyProxy (HTTP)** | `http://root:LEJ6U5chSK@37.1.212.51:8080` |
| **Reverse Proxy (URL)** | `http://37.1.212.51:8443` |

**Команда для подключения:**
```bash
ssh root@37.1.212.51
# Пароль: LEJ6U5chSK
```

---

## 🤖 3. API Ключи и Токены (Секреты)

| Сервис | Ключ / Токен |
|--------|--------------|
| **Telegram Bot Token** | `8232668997:AAH1oMWo7ZqnwjVX2GH3avEjPrCTNK2kVmc` (Username: `@SintaMarketingBot`) |
| **Gemini API Key** | `AIzaSyD5WGVM1AqIjhszcGEprqOo-PwrldExmQs` |
| **Anthropic (Claude) Key** | `sk-ant-api03-***` |
| **Gemini Server Key** | `AIzaSyBu1hTc7tJ87h-4otHp3j36Hs4LDSvyFl4` (Ключ, установленный прямо на прокси-сервере) |

---

## 📊 4. Google Sheets & Drive IDs

| Ресурс | ID (Sheet ID) |
|---------|----------|
| **Авторизация (список)** | `1_SB04LMuGB7ba3aog2xxN6N3g99ZfOboT-vdWXxrh_8` |
| **Обращения** | `15XxSIpD_gMZaSOIrqDVCNI2EqBzphEGiG0ZNJ3HR8hI` |
| **Акции** | `1V3-cPRq_SmbCbIzn1-CWSqD8pdpDqraq_GJ7LjMmwf8` |
| **Аналитика** | `1Xq6bcxaDV2AEVWGqhaLlFcr6-hTNv0L5frXgPY-z7fU` |
| **Google Drive (KB)** | `1JKjzWs3or3hn5ioCIqPBGHkZmgIN-OFf` |

---

## 🔗 5. Полезные ссылки

- **Web App URL:** `https://synthosaicreativestudio-maker.github.io/marketing/`
- **VPN Subscription (Caddy HTTPS):** `https://37.1.212.51.sslip.io:8086/sub/dmVyYSwxNzY4OTgzNjg4ehy8JKshw7`

---

## ✅ Инструкция по обновлению
1. При смене IP или ключей обязательно обновите соответствующие поля в `scripts/yandex_vm_config.sh`.
2. Все секреты в приложении подгружаются из `.env` файла на сервере (`/root/vpn/.env`).
3. **ВАЖНО для VPN:** Marzban больше не используется. Работает самописная `vpn-panel.service`. Если Xray был перезапущен и VLESS-каналы перестали работать (Timeout), обязательно выполните на US сервере: `systemctl restart vpn-panel.service`.
4. Документ защищен `.gitignore` (в теории), но будьте осторожны при передаче третьим лицам.
