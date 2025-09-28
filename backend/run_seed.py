#!/usr/bin/env python3
"""
Скрипт для запуска бэкенда и заполнения базы данных
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path

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

def wait_for_server(url, timeout=30):
    """Ждет пока сервер станет доступен"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    return False

def main():
    print("🚀 Запуск системы афиши мероприятий...")
    
    # Проверяем что мы в правильной директории
    if not os.path.exists("app"):
        print("❌ Запустите скрипт из директории backend/")
        sys.exit(1)
    
    # Устанавливаем зависимости если нужно
    print("📦 Проверяем зависимости...")
    success, output = run_command("pip install -r requirements.txt")
    if not success:
        print(f"❌ Ошибка установки зависимостей: {output}")
        sys.exit(1)
    
    # Создаем базу данных и заполняем тестовыми данными
    print("🗄️  Создаем базу данных и заполняем тестовыми данными...")
    success, output = run_command("python seed_events.py")
    if not success:
        print(f"❌ Ошибка заполнения базы данных: {output}")
        sys.exit(1)
    
    print("✅ База данных готова!")
    print("🌐 Запускаем сервер...")
    print("📱 Откройте http://localhost:8039 в браузере")
    print("🔧 API документация: http://localhost:8039/docs")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    # Запускаем сервер
    try:
        subprocess.run(["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8039", "--reload"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска сервера: {e}")

if __name__ == "__main__":
    main()

