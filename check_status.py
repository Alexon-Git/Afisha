#!/usr/bin/env python3
"""
Скрипт для проверки статуса проекта
"""

import requests
import subprocess
import sys
import os
from pathlib import Path

def check_backend():
    """Проверяет статус бэкенда"""
    try:
        response = requests.get("http://localhost:8039/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Бэкенд работает: http://localhost:8039")
            return True
    except requests.exceptions.RequestException:
        pass
    
    print("❌ Бэкенд не запущен")
    return False

def check_frontend():
    """Проверяет статус фронтенда"""
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Фронтенд работает: http://localhost:3000")
            return True
    except requests.exceptions.RequestException:
        pass
    
    print("❌ Фронтенд не запущен")
    return False

def check_database():
    """Проверяет базу данных"""
    try:
        # Проверяем наличие файла базы данных
        db_file = Path("backend/afisha.db")
        if db_file.exists():
            print("✅ База данных существует")
            return True
        else:
            print("❌ База данных не найдена")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки базы данных: {e}")
        return False

def check_dependencies():
    """Проверяет зависимости"""
    print("🔍 Проверяем зависимости...")
    
    # Python зависимости
    try:
        result = subprocess.run([sys.executable, "-c", "import fastapi, sqlalchemy, uvicorn"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Python зависимости установлены")
        else:
            print("❌ Python зависимости не установлены")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки Python зависимостей: {e}")
        return False
    
    # Node.js зависимости
    try:
        if os.path.exists("frontend/node_modules"):
            print("✅ Node.js зависимости установлены")
        else:
            print("❌ Node.js зависимости не установлены")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки Node.js зависимостей: {e}")
        return False
    
    return True

def main():
    print("🔍 Проверка статуса проекта афиши мероприятий")
    print("=" * 50)
    
    # Проверяем зависимости
    deps_ok = check_dependencies()
    
    # Проверяем базу данных
    db_ok = check_database()
    
    # Проверяем бэкенд
    backend_ok = check_backend()
    
    # Проверяем фронтенд
    frontend_ok = check_frontend()
    
    print("=" * 50)
    
    if deps_ok and db_ok and backend_ok and frontend_ok:
        print("🎉 Все системы работают!")
        print("🌐 Откройте http://localhost:3000 в браузере")
    else:
        print("⚠️  Некоторые компоненты не работают")
        print("💡 Запустите: python start_all.py")

if __name__ == "__main__":
    main()

