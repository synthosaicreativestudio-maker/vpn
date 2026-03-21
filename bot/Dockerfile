FROM python:3.12-slim

WORKDIR /app

# Зависимости бота
COPY bot/requirements.txt bot/requirements.txt
RUN pip install --no-cache-dir -r bot/requirements.txt

# Код бота
COPY bot/ bot/

# Создание директории для БД
RUN mkdir -p /app/bot/data

CMD ["python3", "-m", "bot.main"]
