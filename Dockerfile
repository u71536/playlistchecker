# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Gunicorn для продакшена
RUN pip install gunicorn

# Копируем код приложения
COPY . .

# Копируем и делаем исполняемым entrypoint скрипт
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Компилируем переводы перед переключением пользователя (на случай если нужно)
RUN pybabel compile -d translations || echo "Предупреждение: не удалось скомпилировать переводы"

# Создаем директорию для базы данных
RUN mkdir -p instance

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Используем entrypoint для компиляции переводов при запуске
ENTRYPOINT ["docker-entrypoint.sh"]

# Открываем порт
EXPOSE 5000

# Переменные окружения
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Команда запуска (будет выполнена после entrypoint)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
