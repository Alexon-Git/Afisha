FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директории для статических файлов
RUN mkdir -p app/static/uploads

# Создание директории для Alembic миграций
RUN mkdir -p alembic/versions

# Открытие порта
EXPOSE 8000

# Создание скрипта запуска
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Ожидание готовности базы данных (если используется PostgreSQL)\n\
if [ "$DATABASE_URL" != "sqlite:///./afisha.db" ]; then\n\
    echo "Ожидание готовности базы данных..."\n\
    until python -c "import psycopg2; psycopg2.connect(\"$DATABASE_URL\")" 2>/dev/null; do\n\
        echo "База данных недоступна - ожидание..."\n\
        sleep 2\n\
    done\n\
    echo "База данных готова!"\n\
fi\n\
\n\
# Запуск миграций Alembic\n\
echo "Запуск миграций базы данных..."\n\
alembic upgrade head\n\
\n\
# Создание администратора\n\
echo "Создание администратора..."\n\
python create_admin.py\n\
\n\
# Запуск приложения\n\
echo "Запуск FastAPI приложения..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 8000\n\
' > /app/start.sh && chmod +x /app/start.sh

# Команда запуска
CMD ["/app/start.sh"]
