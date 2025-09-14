#!/usr/bin/env python3
"""
Скрипт для создания администратора
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.auth.auth import get_password_hash
from app.config import settings

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
