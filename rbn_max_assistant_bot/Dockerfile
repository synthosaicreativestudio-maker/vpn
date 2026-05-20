# Dockerfile для Max-бота РБН
FROM python:3.13-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Переменные окружения для отключения лишних сетевых запросов HF
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

# Запуск
CMD ["python", "main.py"]
