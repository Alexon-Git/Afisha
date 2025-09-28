#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных тестовыми мероприятиями
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Добавляем путь к приложению
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models.event import Event
from app.models.user import User
from app.database import Base

# Создаем таблицы если их нет
Base.metadata.create_all(bind=engine)

# Тестовые данные мероприятий
EVENTS_DATA = [
    {
        "title": "Концерт группы 'Аквариум'",
        "description": "Легендарная рок-группа представит новую программу в сопровождении симфонического оркестра. В программе как классические хиты, так и новые композиции.",
        "location": "БКЗ 'Октябрьский', Лиговский пр., 6",
        "category": "concert",
        "image_url": "/static/uploads/20250915_160541_320x480.webp"
    },
    {
        "title": "Выставка 'Искусство эпохи Возрождения'",
        "description": "Уникальная коллекция картин и скульптур из музеев Италии. Более 50 экспонатов, включая работы Леонардо да Винчи, Микеланджело и Рафаэля.",
        "location": "Эрмитаж, Дворцовая пл., 2",
        "category": "exhibition",
        "image_url": "/static/uploads/20250915_160720_v57hIVklCyJfX3MCjGRhNlwgCgoTJZBU_wVt2ViScCvTK0m74QaEJ5XHFP4tUCwVcT590PkLAnLKQRM-jXhhJu66wCFtgZsmKntTRihAlLZYABqvNkDRgF7AjnvucBJZZQh7SQKk5CcVB1CLDKT5QOWLKQFtChTETmc2uIqoFsXv_ZFGbQL6Qqx-s_N_gANnfjdqi5D3UpU5hg0JTO.webp"
    },
    {
        "title": "Спектакль 'Евгений Онегин'",
        "description": "Классическая постановка романа в стихах А.С. Пушкина. Режиссер - народный артист России. В главных ролях - звезды российского театра.",
        "location": "Александринский театр, пл. Островского, 1",
        "category": "theatre",
        "image_url": "/static/uploads/20250916_154946_v57hIVklCyJfX3MCjGRhNlwgCgoTJZBU_wVt2ViScCvTK0m74QaEJ5XHFP4tUCwVcT590PkLAnLKQRM-jXhhJu66wCFtgZsmKntTRihAlLZYABqvNkDRgF7AjnvucBJZZQh7SQKk5CcVB1CLDKT5QOWLKQFtChTETmc2uIqoFsXv_ZFGbQL6Qqx-s_N_gANnfjdqi5D3UpU5hg0JTO.webp"
    },
    {
        "title": "Джазовый вечер с Игорем Бутманом",
        "description": "Вечер джазовой музыки с участием саксофониста Игоря Бутмана и его коллектива. В программе - классический джаз и современные композиции.",
        "location": "Джаз-клуб 'JFC', Шпалерная ул., 33",
        "category": "concert",
        "image_url": None
    },
    {
        "title": "Фестиваль уличного искусства 'Стенограффия'",
        "description": "Международный фестиваль уличного искусства с участием художников из разных стран. Мастер-классы, выставки и создание новых арт-объектов.",
        "location": "Новая Голландия, наб. Адмиралтейского канала, 2",
        "category": "exhibition",
        "image_url": None
    },
    {
        "title": "Балет 'Лебединое озеро'",
        "description": "Классический балет П.И. Чайковского в постановке Мариинского театра. Одна из самых известных балетных постановок в мире.",
        "location": "Мариинский театр, Театральная пл., 1",
        "category": "theatre",
        "image_url": None
    },
    {
        "title": "Рок-фестиваль 'Нашествие'",
        "description": "Один из крупнейших рок-фестивалей России. В программе - выступления ведущих российских и зарубежных рок-групп.",
        "location": "Парк 'Сокольники', Москва",
        "category": "concert",
        "image_url": None
    },
    {
        "title": "Выставка современного искусства 'Арт-Петербург'",
        "description": "Ежегодная выставка современного искусства с участием галерей и художников из России и зарубежья. Инсталляции, перформансы, видеоарт.",
        "location": "ЦВЗ 'Манеж', Исаакиевская пл., 1",
        "category": "exhibition",
        "image_url": None
    },
    {
        "title": "Опера 'Пиковая дама'",
        "description": "Опера П.И. Чайковского по повести А.С. Пушкина. Постановка с использованием современных технологий и декораций.",
        "location": "Михайловский театр, пл. Искусств, 1",
        "category": "theatre",
        "image_url": None
    },
    {
        "title": "Концерт симфонического оркестра",
        "description": "Концерт Санкт-Петербургского филармонического оркестра. В программе - произведения Чайковского, Рахманинова и Шостаковича.",
        "location": "Филармония им. Д.Д. Шостаковича, Михайловская ул., 2",
        "category": "concert",
        "image_url": None
    },
    {
        "title": "Фотовыставка 'Петербург глазами фотографов'",
        "description": "Коллективная выставка фотографов, работающих в жанре городской фотографии. Уникальные ракурсы и виды Санкт-Петербурга.",
        "location": "Русский музей, Инженерная ул., 4",
        "category": "exhibition",
        "image_url": None
    },
    {
        "title": "Спектакль 'Гамлет'",
        "description": "Современная интерпретация трагедии Шекспира. Режиссерская работа с использованием мультимедиа и интерактивных элементов.",
        "location": "Театр им. Ленсовета, Владимирский пр., 12",
        "category": "theatre",
        "image_url": None
    },
    {
        "title": "Джаз-фестиваль 'Усадьба Джаз'",
        "description": "Международный джазовый фестиваль с участием звезд мирового джаза. Мастер-классы, джем-сейшены и концерты.",
        "location": "Парк 'Елагин остров'",
        "category": "concert",
        "image_url": None
    },
    {
        "title": "Выставка 'Советский дизайн'",
        "description": "Ретроспективная выставка советского дизайна 1920-1980-х годов. Плакаты, мебель, посуда, одежда и другие артефакты эпохи.",
        "location": "Музей дизайна, наб. реки Фонтанки, 10",
        "category": "exhibition",
        "image_url": None
    },
    {
        "title": "Мюзикл 'Кошки'",
        "description": "Знаменитый мюзикл Эндрю Ллойда Уэббера в постановке российского театра. Яркие костюмы, запоминающиеся мелодии и танцы.",
        "location": "Театр 'Мюзик-Холл', Александровский парк, 4",
        "category": "theatre",
        "image_url": None
    }
]

def create_admin_user():
    """Создает администратора из ENV файла или по умолчанию"""
    db = SessionLocal()
    try:
        from app.config import settings
        
        # Получаем данные администратора из конфигурации
        admin_username = settings.admin_username
        admin_password = settings.admin_password
        admin_email = getattr(settings, 'admin_email', f"{admin_username}@afisha.ru")
        
        admin = db.query(User).filter(User.username == admin_username).first()
        if not admin:
            from app.auth.auth import get_password_hash
            admin = User(
                username=admin_username,
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                is_admin=True
            )
            db.add(admin)
            db.commit()
            print(f"✅ Создан администратор: {admin_username}/{admin_password}")
            print(f"📧 Email: {admin_email}")
        else:
            print(f"✅ Администратор {admin_username} уже существует")
        return admin
    except Exception as e:
        print(f"❌ Ошибка создания администратора: {e}")
        # Создаем администратора по умолчанию
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            from app.auth.auth import get_password_hash
            admin = User(
                username="admin",
                email="admin@afisha.ru",
                hashed_password=get_password_hash("admin123"),
                is_admin=True
            )
            db.add(admin)
            db.commit()
            print("✅ Создан администратор по умолчанию: admin/admin123")
        return admin
    finally:
        db.close()

def seed_events():
    """Заполняет базу данных тестовыми мероприятиями"""
    db = SessionLocal()
    try:
        # Получаем администратора
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("❌ Администратор не найден. Сначала создайте его.")
            return

        # Очищаем существующие мероприятия
        db.query(Event).delete()
        db.commit()
        print("🗑️  Очищены существующие мероприятия")

        # Создаем мероприятия
        events_created = 0
        base_date = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        
        for i, event_data in enumerate(EVENTS_DATA):
            # Создаем случайные даты в ближайшие 3 месяца
            days_offset = random.randint(0, 90)
            hours_offset = random.randint(0, 23)
            event_date = base_date + timedelta(days=days_offset, hours=hours_offset)
            
            event = Event(
                title=event_data["title"],
                description=event_data["description"],
                datetime=event_date,
                location=event_data["location"],
                image_url=event_data["image_url"],
                category=event_data["category"],
                creator_id=admin.id
            )
            
            db.add(event)
            events_created += 1
            
            if events_created % 5 == 0:
                print(f"📅 Создано {events_created} мероприятий...")

        db.commit()
        print(f"✅ Успешно создано {events_created} мероприятий!")
        
        # Показываем статистику
        total_events = db.query(Event).count()
        concerts = db.query(Event).filter(Event.category == "concert").count()
        exhibitions = db.query(Event).filter(Event.category == "exhibition").count()
        theatres = db.query(Event).filter(Event.category == "theatre").count()
        
        print(f"\n📊 Статистика:")
        print(f"   Всего мероприятий: {total_events}")
        print(f"   Концерты: {concerts}")
        print(f"   Выставки: {exhibitions}")
        print(f"   Театр: {theatres}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании мероприятий: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🌱 Начинаем заполнение базы данных...")
    create_admin_user()
    seed_events()
    print("🎉 Готово!")
