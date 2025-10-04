#!/usr/bin/env python3
"""
Скрипт для проверки всех зависимостей и их совместимости
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """Проверяет версию Python"""
    print("🐍 Проверка версии Python...")
    version = sys.version_info
    if version < (3, 8):
        print(f"❌ Требуется Python 3.8+, текущая версия: {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_package(package_name, min_version=None):
    """Проверяет установку пакета"""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✅ {package_name}: {version}")
        
        if min_version and version != 'unknown':
            # Простая проверка версии (можно улучшить)
            if version < min_version:
                print(f"⚠️  {package_name} версия {version} может быть устаревшей (рекомендуется {min_version})")
        
        return True
    except ImportError:
        print(f"❌ {package_name}: не установлен")
        return False

def check_requirements():
    """Проверяет все зависимости из requirements.txt"""
    print("\n📦 Проверка зависимостей...")
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ Файл requirements.txt не найден")
        return False
    
    with open(requirements_file, 'r') as f:
        requirements = f.readlines()
    
    all_good = True
    for req in requirements:
        req = req.strip()
        if req and not req.startswith('#'):
            package = req.split('==')[0].split('>=')[0].split('<=')[0]
            version = req.split('==')[1] if '==' in req else None
            
            if not check_package(package, version):
                all_good = False
    
    return all_good

def check_database_connection():
    """Проверяет подключение к базе данных"""
    print("\n🗄️  Проверка подключения к базе данных...")
    
    try:
        from app.database import engine
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Подключение к базе данных успешно")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False

def check_models():
    """Проверяет модели данных"""
    print("\n📊 Проверка моделей данных...")
    
    try:
        from app.models.user import User
        from app.models.event import Event
        print("✅ Модели User и Event импортированы успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта моделей: {e}")
        return False

def check_auth():
    """Проверяет систему аутентификации"""
    print("\n🔐 Проверка системы аутентификации...")
    
    try:
        from app.auth.auth import get_password_hash, verify_password
        # Тестируем хеширование пароля
        test_password = "test123"
        hashed = get_password_hash(test_password)
        verified = verify_password(test_password, hashed)
        
        if verified:
            print("✅ Система аутентификации работает корректно")
            return True
        else:
            print("❌ Ошибка в системе аутентификации")
            return False
    except Exception as e:
        print(f"❌ Ошибка в системе аутентификации: {e}")
        return False

def check_static_files():
    """Проверяет статические файлы"""
    print("\n📁 Проверка статических файлов...")
    
    static_dir = Path("app/static/uploads")
    if not static_dir.exists():
        print("⚠️  Директория для статических файлов не найдена, создаем...")
        static_dir.mkdir(parents=True, exist_ok=True)
    
    images_dir = Path("app/images")
    if images_dir.exists():
        image_files = list(images_dir.rglob("*.webp")) + list(images_dir.rglob("*.jpg")) + list(images_dir.rglob("*.png"))
        print(f"✅ Найдено {len(image_files)} изображений")
    else:
        print("⚠️  Директория с изображениями не найдена")
    
    return True

def main():
    print("🔍 Проверка зависимостей и конфигурации бэкенда")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_requirements(),
        check_models(),
        check_auth(),
        check_static_files(),
        check_database_connection()
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("🎉 Все проверки пройдены успешно! Бэкенд готов к запуску.")
        return 0
    else:
        print("❌ Обнаружены проблемы. Исправьте их перед запуском.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
