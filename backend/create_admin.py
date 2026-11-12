#!/usr/bin/env python3
"""Create a bootstrap administrator after Alembic migrations have completed.

Never seeds demonstration events or mutates the database schema.
"""
from app.auth.auth import get_password_hash
from app.config import settings
from app.database import SessionLocal
from app.models import User


def create_admin() -> None:
    with SessionLocal() as db:
        existing = db.query(User).filter(User.username == settings.admin_username).first()
        if existing:
            if not existing.is_admin:
                raise RuntimeError(
                    "Configured ADMIN_USERNAME belongs to a non-admin account. "
                    "Resolve manually; no privileges have been changed."
                )
            print("Administrator exists; password has not been changed.")
            return

        admin = User(username=settings.admin_username,
                     password_hash=get_password_hash(settings.admin_password),
                     email=settings.admin_email, is_admin=True)
        db.add(admin)
        db.commit()
        print("Administrator created.")


if __name__ == "__main__":
    create_admin()
