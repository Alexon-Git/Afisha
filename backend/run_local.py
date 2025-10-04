#!/usr/bin/env python3
"""
Улучшенный скрипт для локального запуска бэкенда с проверкой зависимостей
"""

import subprocess
import sys
import os
import time
import shutil
from pathlib import Path

def check_python_version():
    """Проверяет версию Python"""
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"   Текущая версия: {sys.version}")
        return False
    print(f"✅ Python версия: {sys.version.split()[0]}")
    return True

def create_env_file():
    """Создает .env файл из env.example если его нет"""
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Создаем .env файл из env.example...")
        shutil.copy(env_example, env_file)
        print("✅ .env файл создан")
    elif not env_file.exists():
        print("⚠️  Файл .env не найден, создаем с настройками по умолчанию...")
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write("""# Конфигурация базы данных
DATABASE_URL=sqlite:///./afisha.db

# Секретный ключ для JWT токенов (ОБЯЗАТЕЛЬНО измените в продакшене!)
SECRET_KEY=your-secret-key-change-in-production

# Алгоритм для JWT
ALGORITHM=HS256

# Время жизни токена в минутах
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Данные администратора
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@afisha.ru
""")
        print("✅ .env файл создан с настройками по умолчанию")

def install_dependencies():
    """Устанавливает зависимости"""
    print("📦 Проверяем зависимости...")
    
    # Проверяем наличие pip
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ pip не найден. Установите pip и попробуйте снова.")
        return False
    
    # Устанавливаем зависимости
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Зависимости установлены")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False

def run_command(command, cwd=None):
    """Запускает команду и возвращает результат"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def main():
    print("🚀 Запуск системы афиши мероприятий...")
    print("=" * 50)
    
    # Проверяем версию Python
    if not check_python_version():
        sys.exit(1)
    
    # Проверяем что мы в правильной директории
    if not os.path.exists("app"):
        print("❌ Запустите скрипт из директории backend/")
        sys.exit(1)
    
    # Создаем .env файл если его нет
    create_env_file()
    
    # Устанавливаем зависимости
    if not install_dependencies():
        print("❌ Не удалось установить зависимости")
        sys.exit(1)
    
    # Создаем базу данных и заполняем тестовыми данными
    print("🗄️  Создаем базу данных и заполняем тестовыми данными...")
    success, output = run_command(f"{sys.executable} seed_events.py")
    if not success:
        print(f"❌ Ошибка заполнения базы данных: {output}")
        sys.exit(1)
    
    print("✅ База данных готова!")
    print("=" * 50)
    print("🌐 Сервер будет доступен по адресу: http://localhost:8039")
    print("📚 API документация: http://localhost:8039/docs")
    print("🔧 Интерактивная документация: http://localhost:8039/redoc")
    print("⏹️  Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    # Запускаем сервер
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8039", 
            "--reload",
            "--log-level", "info"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска сервера: {e}")
    except FileNotFoundError:
        print("❌ uvicorn не найден. Установите его: pip install uvicorn[standard]")

if __name__ == "__main__":
    main()
