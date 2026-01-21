#!/usr/bin/expect -f

# Автоматическое выполнение настройки с вводом пароля
set timeout 30
set server "37.1.212.51"
set user "root"
set password "LEJ6U5chSK"
set script_path "/Users/verakoroleva/Desktop/vpn/auto_setup_reality_non_interactive.sh"

puts "🚀 Автоматическая настройка VLESS + REALITY"
puts "=================================================="

# Копирование скрипта на сервер
puts "📤 Копирование скрипта на сервер..."
spawn scp -o StrictHostKeyChecking=no $script_path ${user}@${server}:/tmp/
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "yes/no" {
        send "yes\r"
        exp_continue
    }
    eof
}

puts "✅ Скрипт скопирован"

# Выполнение скрипта на сервере
puts "🚀 Запуск настройки на сервере..."
spawn ssh -o StrictHostKeyChecking=no ${user}@${server} "chmod +x /tmp/auto_setup_reality_non_interactive.sh && /tmp/auto_setup_reality_non_interactive.sh"
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    "yes/no" {
        send "yes\r"
        exp_continue
    }
    eof
}

puts "✅ Настройка выполнена"

# Получение конфигурации
puts "📥 Получение конфигурации..."
spawn scp -o StrictHostKeyChecking=no ${user}@${server}:/tmp/marzban_reality_config.json /Users/verakoroleva/Desktop/vpn/generated_config.json
expect {
    "password:" {
        send "$password\r"
        exp_continue
    }
    eof
}

puts "✅ Конфигурация сохранена в generated_config.json"
puts ""
puts "📋 Следующие шаги:"
puts "1. Откройте generated_config.json"
puts "2. Вставьте JSON в Marzban → Core Settings → inbounds"
puts "3. Создайте пользователя (VLESS, Flow: vision)"
puts "4. Подключитесь через Amnezia VPN"
