FROM python:3.11-slim-bookworm@sha256:a83ba18aef0f865b1a4a611c2cf460fe446f2795673bbb9fe43be570439e3b39

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY . .
RUN mkdir -p app/static/uploads && chown -R 1000:1000 app/static/uploads

USER 1000:1000

EXPOSE 8039

# Uses the Python standard library, so no extra runtime package is required.
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=6 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8039/health', timeout=2).read()"]

# Fail closed if migrations or admin bootstrap fail. No silent error suppression.
CMD ["sh", "-ec", "alembic upgrade head && python create_admin.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8039} --no-proxy-headers"]
