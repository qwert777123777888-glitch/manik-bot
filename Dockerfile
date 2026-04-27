FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY bot.py .
COPY config.py .

# Создаём папку для данных
RUN mkdir -p /app/data

# Тома для хранения данных
VOLUME ["/app/data"]

# Запускаем бота
CMD ["python", "bot.py"]