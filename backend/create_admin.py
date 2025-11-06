#!/usr/bin/env python3
"""
Скрипт для создания администратора. Если создан, дополнительно проверяет заполненность таблицы событий
и при необходимости запускает `seed_events.py` для заполнения тестовыми данными.
"""

import sys
import os
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User  # ensures User and Event are both registered
from app.auth.auth import get_password_hash
from app.config import settings
from app.database import engine, Base
from app.utils import schema as schema_utils

# Ensure DB tables exist when script runs (helpful for first-time startup without running alembic)
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    # If this fails (e.g. remote DB with migrations), continue and let DB/migrations handle schema
    pass

schema_utils.ensure_columns(
    engine,
    (
        schema_utils.ColumnRequirement("events", "category", "VARCHAR"),
        schema_utils.ColumnRequirement("users", "email", "VARCHAR"),
    ),
)


def try_seed_if_empty():
    """Запускает seed_events.py если таблица events пуста."""
    db = SessionLocal()
    try:
        from app.models.event import Event
        count = db.query(Event).count()
    except Exception:
        count = None
    finally:
        db.close()

    if count == 0:
        print("\u26a1\ufe0f Events table empty — running seed_events.py to populate DB...")
        try:
            subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'seed_events.py')], check=False)
        except Exception as e:
            print(f"\u274c Failed to run seed_events.py: {e}")


def create_admin():
    db = SessionLocal()
    try:
        # Проверяем, существует ли уже админ
        admin = db.query(User).filter(User.username == settings.admin_username).first()
        if admin:
            print(f"Администратор {settings.admin_username} уже существует")
            return
        
        # Создаем админа
        admin = User(
            username=settings.admin_username,
            password_hash=get_password_hash(settings.admin_password),
            email=settings.admin_email,
            is_admin=True
        )
        db.add(admin)
        db.commit()
        print(f"Администратор {settings.admin_username} создан успешно")
        print(f"Пароль: {settings.admin_password}")
        
    except Exception as e:
        print(f"Ошибка при создании администратора: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
    # После попытки создать администратора попробуем заполнить события если потребуется
    try_seed_if_empty()
