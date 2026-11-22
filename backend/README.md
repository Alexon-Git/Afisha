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

#### Existing uploads when upgrading to the non-root image

Compose runs the backend with `BACKEND_UID`/`BACKEND_GID` (1000/1000 by
default). Before the first start of this image, an existing uploads directory
created by a root container must be made writable by that deployment user.
This is a one-time metadata change; it does not move or delete uploaded files.

1. Back up uploads and stop only the backend container. Do not remove volumes.
2. Set `BACKEND_UID` and `BACKEND_GID` in `backend/.env` to the deployment
   user's `id -u` and `id -g` values.
3. From `backend/`, verify that `app/static/uploads` is the intended directory,
   then run with those same numeric values:

```bash
backend_uid=1000
backend_gid=1000
sudo chown -R "${backend_uid}:${backend_gid}" app/static/uploads
sudo chmod -R u+rwX app/static/uploads
```

Do not apply these commands to a parent directory. Afterward, start the backend
and verify an image upload before exposing the service.

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

### Event time contract (PR-8)

Event datetime writes require ISO 8601 with an explicit UTC offset, for example
`2026-11-12T12:00:00+07:00`; responses normalize to `2026-11-12T05:00:00Z`.
Naive strings, date-only values and numeric epochs return 422. PostgreSQL uses
`timestamptz`; SQLite encodes UTC and the ORM restores the offset. Calendar
filters use Asia/Novosibirsk days, not the server/process timezone. A calendar
range that cannot be represented in UTC returns 400 (including 0001-01-01).
Unchanged instants expressed with different offsets compare equal.

Upgrade 0004 requires an empty events table; it intentionally refuses all
historical events. See MIGRATIONS.md. Admin form timezone behavior remains PR-9:
creating/actually changing a date still follows the existing browser conversion.
This PR does not claim that the form interprets all input as Novosibirsk time.
