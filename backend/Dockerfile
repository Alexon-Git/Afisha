FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p app/static/uploads

EXPOSE 8039

# Fail closed if migrations or admin bootstrap fail. No silent error suppression.
CMD ["sh", "-ec", "alembic upgrade head && python create_admin.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8039} --no-proxy-headers"]
