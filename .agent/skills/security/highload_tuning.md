---
name: High-Load Performance Tuning
description: System optimization, sysctl parameters, BBR congestion control, TCP/UDP tuning, file limits
version: 1.0.0
---

# ⚡ High-Load Performance Tuning

Этот skill содержит инструкции и команды для оптимизации операционной системы сервера VPN с целью обработки большого количества одновременных подключений.

## 🎛 Настройки ядра (Sysctl Tuning)

Рекомендуемые параметры для внесения в `/etc/sysctl.d/99-vpn-tuning.conf` или `/etc/sysctl.conf`:

```ini
# Максимальное число открытых файлов и сокетов
fs.file-max = 2097152

# Оптимизация очередей сетевых интерфейсов
net.core.netdev_max_backlog = 16384
net.core.somaxconn = 32768

# Размеры буферов для TCP (минимальный, дефолтный, максимальный в байтах)
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Тюнинг обработки TCP соединений
net.ipv4.tcp_max_syn_backlog = 16384
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15

# Использование TCP Fast Open (значение 3 включает и на входящие, и на исходящие)
net.ipv4.tcp_fastopen = 3

# Отключение медленного старта TCP после простоя
net.ipv4.tcp_slow_start_after_idle = 0

# Лимиты трекинга соединений (для предотвращения переполнения таблицы conntrack)
net.netfilter.nf_conntrack_max = 262144
net.netfilter.nf_conntrack_tcp_timeout_established = 600
```

Применить изменения:
```bash
sudo sysctl --system
```

---

## 🏎 Включение алгоритма BBR

Сетевой контроль перегрузок BBR (Bottleneck Bandwidth and RTT) кардинально улучшает скорость и снижает потери пакетов.

```bash
# Проверить текущий алгоритм
sysctl net.ipv4.tcp_congestion_control

# Включить fq и bbr (если не включены)
sudo sysctl -w net.core.default_qdisc=fq
sudo sysctl -w net.ipv4.tcp_congestion_control=bbr

# Добавить автозапуск в /etc/sysctl.conf:
# net.core.default_qdisc = fq
# net.ipv4.tcp_congestion_control = bbr
```

---

## 📂 Лимиты файловых дескрипторов (Limits.conf)

Каждое подключение к прокси-серверу использует файловые дескрипторы. По умолчанию лимиты могут быть низкими (1024), что вызовет ошибку `Too many open files`.

Рекомендуемые лимиты в `/etc/security/limits.conf`:
```text
root             soft    nofile          1048576
root             hard    nofile          1048576
*                soft    nofile          1048576
*                hard    nofile          1048576
```

Для systemd-сервисов (например, `/etc/systemd/system/xray.service`):
```ini
[Service]
LimitNOFILE=1048576
```
После изменения сервиса выполнить `systemctl daemon-reload && systemctl restart xray`.

---

## 📈 Мониторинг ресурсов под нагрузкой
```bash
# Просмотр активных соединений и их буферов
ss -s
ss -tlnp

# Мониторинг загрузки процессора и диска
htop
vmstat 1 10
iostat -x 1 5
```
