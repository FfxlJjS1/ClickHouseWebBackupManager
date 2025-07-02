FROM python:3.10-alpine

WORKDIR /app

# Установка минимальных зависимостей
RUN apk add --no-cache curl tar gzip

# Установка clickhouse-backup из указанного URL
RUN curl -sLO https://github.com/Altinity/clickhouse-backup/releases/download/v2.6.23/clickhouse-backup-linux-amd64.tar.gz \
    && tar -xzf clickhouse-backup-linux-amd64.tar.gz \
    && mv ./build/linux/amd64/clickhouse-backup /usr/local/bin/ \
    && chmod +x /usr/local/bin/clickhouse-backup \
    && rm clickhouse-backup-linux-amd64.tar.gz \
    && rm -rf build

# Проверка установки
RUN clickhouse-backup --version

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]