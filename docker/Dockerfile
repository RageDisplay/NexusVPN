FROM python:3.11-slim

WORKDIR /app

# Установить зависимости системы
RUN apt-get update && apt-get install -y \
    iptables \
    iproute2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копировать requirements.txt
COPY requirements.txt .

# Установить Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копировать приложение
COPY backend/ backend/
COPY shared/ shared/
COPY docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Expose порт
EXPOSE 443 80 1194

# Запустить сервер
ENTRYPOINT ["/entrypoint.sh"]
