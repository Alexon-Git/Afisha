#!/usr/bin/env python3
"""
Скрипт для заполнения базы данных тестовыми мероприятиями
"""

import sys
import os
import glob
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

def get_available_images():
    """Получает список доступных изображений"""
    upload_dir = "app/static/uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
    
    # Ищем изображения в папке uploads
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif']
    images = []
    for ext in image_extensions:
        images.extend(glob.glob(os.path.join(upload_dir, ext)))
        images.extend(glob.glob(os.path.join(upload_dir, ext.upper())))
    
    return [f"/static/uploads/{os.path.basename(img)}" for img in images]

# Тестовые данные мероприятий
EVENTS_DATA = [
    {
        "title": "Концерт группы 'Аквариум'",
        "description": "Легендарная рок-группа представит новую программу в сопровождении симфонического оркестра. В программе как классические хиты, так и новые композиции.",
        "location": "БКЗ 'Октябрьский', Лиговский пр., 6",
        "category": "concert"
    },
    {
        "title": "Выставка 'Искусство эпохи Возрождения'",
        "description": "Уникальная коллекция картин и скульптур из музеев Италии. Более 50 экспонатов, включая работы Леонардо да Винчи, Микеланджело и Рафаэля.",
        "location": "Эрмитаж, Дворцовая пл., 2",
        "category": "exhibition"
    },
    {
        "title": "Спектакль 'Евгений Онегин'",
        "description": "Классическая постановка романа в стихах А.С. Пушкина. Режиссер - народный артист России. В главных ролях - звезды российского театра.",
        "location": "Александринский театр, пл. Островского, 1",
        "category": "theatre"
    },
    {
        "title": "Джазовый вечер с Игорем Бутманом",
        "description": "Вечер джазовой музыки с участием саксофониста Игоря Бутмана и его коллектива. В программе - классический джаз и современные композиции.",
        "location": "Джаз-клуб 'JFC', Шпалерная ул., 33",
        "category": "concert",
    },
    {
        "title": "Фестиваль уличного искусства 'Стенограффия'",
        "description": "Международный фестиваль уличного искусства с участием художников из разных стран. Мастер-классы, выставки и создание новых арт-объектов.",
        "location": "Новая Голландия, наб. Адмиралтейского канала, 2",
        "category": "exhibition",
    },
    {
        "title": "Балет 'Лебединое озеро'",
        "description": "Классический балет П.И. Чайковского в постановке Мариинского театра. Одна из самых известных балетных постановок в мире.",
        "location": "Мариинский театр, Театральная пл., 1",
        "category": "theatre",
    },
    {
        "title": "Рок-фестиваль 'Нашествие'",
        "description": "Один из крупнейших рок-фестивалей России. В программе - выступления ведущих российских и зарубежных рок-групп.",
        "location": "Парк 'Сокольники', Москва",
        "category": "concert",
    },
    {
        "title": "Выставка современного искусства 'Арт-Петербург'",
        "description": "Ежегодная выставка современного искусства с участием галерей и художников из России и зарубежья. Инсталляции, перформансы, видеоарт.",
        "location": "ЦВЗ 'Манеж', Исаакиевская пл., 1",
        "category": "exhibition",
    },
    {
        "title": "Опера 'Пиковая дама'",
        "description": "Опера П.И. Чайковского по повести А.С. Пушкина. Постановка с использованием современных технологий и декораций.",
        "location": "Михайловский театр, пл. Искусств, 1",
        "category": "theatre",
    },
    {
        "title": "Концерт симфонического оркестра",
        "description": "Концерт Санкт-Петербургского филармонического оркестра. В программе - произведения Чайковского, Рахманинова и Шостаковича.",
        "location": "Филармония им. Д.Д. Шостаковича, Михайловская ул., 2",
        "category": "concert",
    },
    {
        "title": "Фотовыставка 'Петербург глазами фотографов'",
        "description": "Коллективная выставка фотографов, работающих в жанре городской фотографии. Уникальные ракурсы и виды Санкт-Петербурга.",
        "location": "Русский музей, Инженерная ул., 4",
        "category": "exhibition",
    },
    {
        "title": "Спектакль 'Гамлет'",
        "description": "Современная интерпретация трагедии Шекспира. Режиссерская работа с использованием мультимедиа и интерактивных элементов.",
        "location": "Театр им. Ленсовета, Владимирский пр., 12",
        "category": "theatre",
    },
    {
        "title": "Джаз-фестиваль 'Усадьба Джаз'",
        "description": "Международный джазовый фестиваль с участием звезд мирового джаза. Мастер-классы, джем-сейшены и концерты.",
        "location": "Парк 'Елагин остров'",
        "category": "concert",
    },
    {
        "title": "Выставка 'Советский дизайн'",
        "description": "Ретроспективная выставка советского дизайна 1920-1980-х годов. Плакаты, мебель, посуда, одежда и другие артефакты эпохи.",
        "location": "Музей дизайна, наб. реки Фонтанки, 10",
        "category": "exhibition",
    },
    {
        "title": "Мюзикл 'Кошки'",
        "description": "Знаменитый мюзикл Эндрю Ллойда Уэббера в постановке российского театра. Яркие костюмы, запоминающиеся мелодии и танцы.",
        "location": "Театр 'Мюзик-Холл', Александровский парк, 4",
        "category": "theatre",
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
                password_hash=get_password_hash(admin_password),
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
                password_hash=get_password_hash("admin123"),
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
        admin = db.query(User).filter(User.is_admin == True).first()
        if not admin:
            print("❌ Администратор не найден. Сначала создайте его.")
            return

        # Получаем доступные изображения
        available_images = get_available_images()
        print(f"🖼️  Найдено {len(available_images)} изображений")

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

            price = random.randint(500, 5000)
            rating = round(random.uniform(7.0, 9.8), 1)
            discount = random.choice([None, random.randint(5, 30)])
            payment_url = f"https://pay.afisha.local/event/{i + 1}"

            # Выбираем случайное изображение или None
            image_url = None
            if available_images and i < len(available_images):
                image_url = available_images[i]
            elif available_images:
                image_url = random.choice(available_images)

            event = Event(
                title=event_data["title"],
                description=event_data["description"],
                datetime=event_date,
                location=event_data["location"],
                image_url=image_url,
                category=event_data["category"],
                creator_id=admin.id,
                price=price,
                rating=rating,
                discount=discount,
                payment_url=payment_url,
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
        events_with_images = db.query(Event).filter(Event.image_url.isnot(None)).count()
        
        print(f"\n📊 Статистика:")
        print(f"   Всего мероприятий: {total_events}")
        print(f"   Концерты: {concerts}")
        print(f"   Выставки: {exhibitions}")
        print(f"   Театр: {theatres}")
        print(f"   С изображениями: {events_with_images}")
        
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
