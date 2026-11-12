# Afisha backend

FastAPI, SQLAlchemy, PostgreSQL (SQLite for local development),
Alembic migrations and JWT administrator authentication.

### Local startup
```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# set secure SECRET_KEY and ADMIN_PASSWORD values in .env
python start.py
```

The startup runs migrations, then creates an admin if absent, then starts
Uvicorn at http://127.0.0.1:8039. It does not seed demo events.

### Docker Compose
```bash
cd backend
cp env.compose.example .env
# configure DATABASE_URL, POSTGRES_PASSWORD and secure secrets
docker compose up --build
```

API: http://127.0.0.1:8039. The compose stack does not include frontend.

### Existing databases
Read [MIGRATIONS.md](MIGRATIONS.md) before starting a preexisting database.
The initial revision intentionally refuses to modify unversioned legacy tables.

### Smoke tests
```bash
pip install -r requirements-dev.txt
pytest -q
```

Public endpoints: `GET /health`, `GET /events/`, `GET /categories/`.
Protected by admin JWT: create/update/delete events/categories,
image uploads and `POST /auth/register`.
