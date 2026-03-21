FROM python:3.12-slim

# Безопасность: non-root user
RUN adduser --disabled-password --no-create-home panel

WORKDIR /app

# Зависимости (кэшируются отдельно)
COPY panel/requirements.txt panel/requirements.txt
RUN pip install --no-cache-dir -r panel/requirements.txt

# Код панели
COPY panel/ panel/

# Генерация gRPC stubs
RUN cd panel/proto && bash generate.sh

# Создание директории для БД
RUN mkdir -p /app/data && chown panel:panel /app/data

# Запуск от non-root
USER panel

EXPOSE 8085

CMD ["gunicorn", "panel.app:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8085", \
     "--access-logfile", "-"]
