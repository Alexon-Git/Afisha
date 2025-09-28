#!/usr/bin/env python3
"""
Скрипт для запуска всего проекта (бэкенд + фронтенд)
"""

import subprocess
import sys
import os
import time
import threading
from pathlib import Path

def run_backend():
    """Запускает бэкенд"""
    print("🚀 Запускаем бэкенд...")
    os.chdir("backend")
    subprocess.run([sys.executable, "start.py"])

def run_frontend():
    """Запускает фронтенд"""
    print("🎨 Запускаем фронтенд...")
    os.chdir("frontend")
    subprocess.run(["npm", "start"])

def main():
    print("🎭 Запуск полного проекта афиши мероприятий")
    print("=" * 60)
    
    # Проверяем что мы в корневой директории проекта
    if not os.path.exists("backend") or not os.path.exists("frontend"):
        print("❌ Запустите скрипт из корневой директории проекта")
        sys.exit(1)
    
    # Проверяем Node.js
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Node.js не найден. Установите Node.js для запуска фронтенда")
        sys.exit(1)
    
    # Проверяем npm
    try:
        subprocess.run(["npm", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ npm не найден. Установите npm для запуска фронтенда")
        sys.exit(1)
    
    print("✅ Все зависимости найдены")
    print("=" * 60)
    print("🌐 Бэкенд будет доступен: http://localhost:8039")
    print("🎨 Фронтенд будет доступен: http://localhost:3000")
    print("📚 API документация: http://localhost:8039/docs")
    print("⏹️  Для остановки нажмите Ctrl+C")
    print("=" * 60)
    
    try:
        # Запускаем бэкенд в отдельном потоке
        backend_thread = threading.Thread(target=run_backend, daemon=True)
        backend_thread.start()
        
        # Ждем немного чтобы бэкенд запустился
        time.sleep(3)
        
        # Запускаем фронтенд
        run_frontend()
        
    except KeyboardInterrupt:
        print("\n👋 Проект остановлен")

if __name__ == "__main__":
    main()

