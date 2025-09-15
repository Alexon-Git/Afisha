# Афиша мероприятий - Backend

FastAPI приложение для управления мероприятиями.

## Запуск с Docker

### 1. Подготовка

Скопируйте файл конфигурации:

```bash
cp env.example .env
```

Отредактируйте `.env` файл под ваши нужды.

### 2. Сборка и запуск

```bash
# Сборка образа
docker build -t afisha-backend .

# Запуск контейнера
docker run -d \
  --name afisha-backend \
  -p 8000:8000 \
  --env-file .env \
  afisha-backend
```

### 3. Проверка работы

- API доступно по адресу: http://localhost:8000
- Документация API: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Конфигурация

### Переменные окружения

- `DATABASE_URL` - URL базы данных (по умолчанию SQLite)
- `SECRET_KEY` - Секретный ключ для JWT токенов
- `ALGORITHM` - Алгоритм для JWT (по умолчанию HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Время жизни токена в минутах
- `ADMIN_USERNAME` - Имя администратора
- `ADMIN_PASSWORD` - Пароль администратора

### База данных

По умолчанию используется SQLite. Для использования PostgreSQL:

1. Установите PostgreSQL
2. Создайте базу данных
3. Обновите `DATABASE_URL` в `.env` файле

## API Endpoints

- `GET /` - Главная страница API
- `GET /health` - Проверка состояния
- `POST /auth/login` - Авторизация
- `GET /events/` - Список мероприятий
- `POST /events/` - Создание мероприятия (требует авторизации)
- `PUT /events/{id}` - Обновление мероприятия (требует авторизации)
- `DELETE /events/{id}` - Удаление мероприятия (требует авторизации)

## Структура проекта

```
backend/
├── app/
│   ├── auth/          # Модуль авторизации
│   ├── models/        # SQLAlchemy модели
│   ├── routers/       # API роутеры
│   ├── schemas/       # Pydantic схемы
│   ├── static/        # Статические файлы
│   ├── config.py      # Конфигурация
│   ├── database.py    # Настройка БД
│   └── main.py        # Главный файл приложения
├── alembic/           # Миграции базы данных
├── create_admin.py    # Скрипт создания администратора
├── Dockerfile         # Docker конфигурация
├── requirements.txt   # Python зависимости
└── env.example        # Пример конфигурации
```


