# Deployment — draft for the reactivated Afisha project

There is no production server selected yet. This document contains a
pre-deployment checklist, **not a working CI/CD promise**.

1. Run `pytest -q` and perform API/Frontend smoke tests.
2. Confirm whether production database is empty. If not, follow
   [backend/MIGRATIONS.md](backend/MIGRATIONS.md) and test with a backup copy.
3. Prepare unique `POSTGRES_PASSWORD`, `DATABASE_URL`, `SECRET_KEY`,
   `ADMIN_USERNAME`, and `ADMIN_PASSWORD` in `backend/.env`. Never commit
   this file or expose it in logs.
4. Configure domain, Nginx HTTPS, and proper API origin. The frontend currently
   has a hardcoded production API origin; it requires adjustment before deploy.
5. Restrict public ports to 80/443. PostgreSQL and API are loopback-bound by
   backend/docker-compose.yml and should not be published publicly.
6. Configure durable volumes, backups, monitoring, rate limits and log rotation.
7. With an empty database, `cd backend && docker compose up -d --build`.
   Backend runs Alembic migrations, then bootstrap administrator.
8. Confirm `/health`, authenticated administration, events CRUD and uploads.
9. Never assume the previous deployment paths or SSH secrets still apply.

The existing `deploy/nginx/afisha.conf` is an illustrative example; its server
name, static paths and frontend API proxy require review for the new host.
