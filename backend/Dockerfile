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
EXPOSE 8039

# Создание скрипта запуска
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Порт приложения (по умолчанию 8039)\n\
APP_PORT="${PORT:-8039}"\n\
\n\
# Ожидание готовности базы данных (если используется PostgreSQL)\n\
if [[ "$DATABASE_URL" != "sqlite:///./afisha.db" && -n "$DATABASE_URL" ]]; then\n\
  echo "Ожидание готовности базы данных..."\n\
  until python - <<PY\n\
import os\n\
import sys\n\
from urllib.parse import urlparse\n\
import psycopg2\n\
url = os.environ.get("DATABASE_URL")\n\
parsed = urlparse(url)\n\
conn = psycopg2.connect(url)\n\
conn.close()\n\
PY\n\
  do\n\
    echo "База данных недоступна - ожидание..."\n\
    sleep 2\n\
  done\n\
  echo "База данных готова!"\n\
fi\n\
\n\
# Запуск миграций Alembic (если настроен alembic.ini)\n\
if [ -f "/app/alembic.ini" ]; then\n\
  echo "Запуск миграций базы данных..."\n\
  alembic upgrade head || true\n\
fi\n\
\n\
# Создание администратора (идемпотентно, использует ADMIN_USERNAME/ADMIN_PASSWORD)\n\
echo "Создание администратора..."\n\
python create_admin.py || true\n\
\n\
# Запуск приложения\n\
echo "Запуск FastAPI приложения на порту ${APP_PORT}..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}\n\
' > /app/start.sh && chmod +x /app/start.sh

# Команда запуска
CMD ["/app/start.sh"]
