# 🛡️ Инструкция для Amnezia App

Для этого приложения используется протокол **AmneziaWG**, который лучше всего обходит глубокий анализ трафика (DPI).

## Как подключиться:
1. Скопируйте весь JSON-код ниже.
2. В приложении Amnezia нажмите **«Добавить через JSON»** (Add from JSON).
3. Вставьте код и нажмите «Подключиться».

## JSON Конфигурация:
```json
{
  "containers": [
    {
      "container": "amnezia-awg",
      "port": "30443",
      "protocol": "awg",
      "settings": {
        "address": "10.0.0.2",
        "h1": "1", "h2": "2", "h3": "3", "h4": "4",
        "jc": "4", "jmax": "70", "jmin": "40",
        "mtu": "1280",
        "private_key": "EJNiKCiAmXsQ8kzfhg48uzRaYE5axjzRo0i+MNi5FUY=",
        "public_key": "Y/YojY7CIdrhjuQck100y08DeRf/YdI/TvuyL21uYVY=",
        "s1": "5", "s2": "10"
      }
    }
  ],
  "host": "37.1.212.51"
}
```
