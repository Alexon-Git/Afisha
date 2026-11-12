# Afisha — платформа мероприятий (проект восстановления)

Текущая рабочая ветка: `master`. Старую `main` сохраняем как архив предыдущей реализации.

## Паспорт проекта и работа с AI-агентами

Проект развивается как **бизнес-афиша Новосибирска**. Контекст, требования
и история решений хранятся в репозитории, чтобы несколько разработчиков и
AI-агентов могли продолжать работу без потери договорённостей.

- [AGENTS.md](AGENTS.md) — единые правила для AI-агентов.
- [CLAUDE.md](CLAUDE.md) — точка входа для Claude Code.
- [docs/PROJECT_PASSPORT.md](docs/PROJECT_PASSPORT.md) — паспорт проекта.
- [docs/PRODUCT_REQUIREMENTS.md](docs/PRODUCT_REQUIREMENTS.md) — P0/P1/P2.
- [docs/ROADMAP.md](docs/ROADMAP.md) — дорожная карта.
- [docs/DEVELOPMENT_CONTEXT.md](docs/DEVELOPMENT_CONTEXT.md) — реализованный код и технический долг.
- [docs/DECISIONS.md](docs/DECISIONS.md) — решения и открытые вопросы.
- [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) — передача задач следующему агенту.
- [docs/README.md](docs/README.md) — индекс документации.

**Порядок входа нового агента:** сначала AGENTS.md → паспорт →
требования → текущий handoff → фактический код → тесты. Не принимайте
планируемые функции за уже реализованные.


## Стек
- Backend: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL 17, Alembic.
- Frontend: React 18, TypeScript, Tailwind CSS (Create React App).
- Развёртывание: Docker Compose, Nginx (требует настройки для вашего домена).

## Состояние
Это реанимируемая версия прежней афиши: CRUD мероприятий, категории,
календарные компоненты, авторизация администратора, загрузка изображений.
Новый функционал бизнес-афиши и рекламный кабинет ещё не реализованы.
Перед публичным запуском необходимы тесты, обновление зависимостей и SEO.

## Быстрый локальный запуск

```bash
git clone https://github.com/Alexon-Git/Afisha.git
cd Afisha/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env
```

**Обязательно** замените `SECRET_KEY` и `ADMIN_PASSWORD` в
`backend/.env` на уникальные значения. По умолчанию SQLite используется
только для локальной разработки.

```bash
python start.py
```

Скрипт запускает миграции, создаёт администратора (только если его нет)
и поднимает API на http://127.0.0.1:8039.
Никакие тестовые события автоматически не загружаются.

В другом терминале:

```bash
cd Afisha/frontend
npm ci
npm start
```

Frontend: http://localhost:3000, admin: http://localhost:3000/admin/login.
Логин определяется `ADMIN_USERNAME`; стандартного пароля нет.

## Docker (backend + PostgreSQL)

Из папки `backend/`:

```bash
cp env.compose.example .env
# замените все заглушки, согласуйте POSTGRES_PASSWORD и пароль в DATABASE_URL
docker compose up --build
```

Compose публикует порты API и базы только на loopback-интерфейсе
(`127.0.0.1:8039`, `127.0.0.1:5439`). Frontend в этом compose не включён.
Для доступа снаружи необходимо безопасно настроить Nginx/HTTPS.

**Внимание:** для уже существующей БД сначала выполните процедуру
в [backend/MIGRATIONS.md](backend/MIGRATIONS.md), а не запускайте миграции
вслепую.

## Проверка изменений

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Подробнее: [backend/MIGRATIONS.md](backend/MIGRATIONS.md).

## Безопасность
Не коммитьте `.env`, пароли и дампы. `SECRET_KEY` должен содержать
как минимум 32 символа; пароль администратора — минимум 12 символов.
Создание пользователей через API разрешено только администратору.

Текущая архитектура содержит другие вопросы перед продакшеном:
proxy headers, валидация загружаемых файлов, зависимости, rate limiting,
бэкапы и версионирование API.
