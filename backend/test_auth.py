#!/usr/bin/env python3
"""
Скрипт для тестирования системы аутентификации
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.auth.auth import get_password_hash, verify_password

def test_password_hashing():
    """Тестирует хеширование паролей"""
    print("🔐 Тестирование системы аутентификации...")
    
    test_passwords = [
        "admin123",
        "password123",
        "very_long_password_that_might_cause_issues_with_bcrypt_limitation_of_72_bytes",
        "test",
        "a" * 100  # Очень длинный пароль
    ]
    
    for password in test_passwords:
        try:
            print(f"\n📝 Тестируем пароль: '{password[:20]}{'...' if len(password) > 20 else ''}'")
            print(f"   Длина: {len(password)} символов, {len(password.encode('utf-8'))} байт")
            
            # Хешируем пароль
            hashed = get_password_hash(password)
            print(f"   ✅ Хеш создан: {hashed[:50]}...")
            
            # Проверяем пароль
            is_valid = verify_password(password, hashed)
            print(f"   {'✅' if is_valid else '❌'} Проверка: {'успешна' if is_valid else 'неудачна'}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    test_password_hashing()
