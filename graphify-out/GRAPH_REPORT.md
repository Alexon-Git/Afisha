# Graph Report - бизнес афиша  (2026-11-12)

## Corpus Check
- 110 files · ~55,482 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 829 nodes · 1243 edges · 66 communities (55 shown, 11 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 35 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2985b5ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AGENTS.md
- EventService
- test_image_upload.py
- categories.py
- package.json
- dependencies
- Engineering Review: Бизнес Афиша
- 🎭 Афиша мероприятий - Инструкция по запуску
- User
- What You Must Do When Invoked
- Требования к продукту — Afisha Business MVP
- Afisha: предпроектный продуктовый разбор
- compilerOptions
- Журнал решений (ADR-lite) — Afisha
- HomePage.tsx
- services/api.ts
- Технический план реализации MVP «Бизнес Афиша» — v2.1
- Event
- auth/auth.py
- check_dependencies.py
- Контекст разработки Afisha — технический снимок
- routers/auth.py
- Паспорт проекта — Afisha / Бизнес-афиша Новосибирска
- UserService
- schema.py
- Передача контекста следующему агенту — Afisha
- Roadmap — Бизнес Афиша: публичный MVP
- authenticate_user
- App.tsx
- EventsFeed.tsx
- Интеграция с Яндекс.Директ
- Codex: подготовка рабочего места Afisha
- check_status.py
- Release checklist — публичный запуск «Бизнес Афиши»
- graphify reference: extra exports and benchmark
- CalendarGrid.tsx
- План PR-1: ограничение попыток входа и доверие proxy
- manifest.json
- run_seed.py
- graphify reference: query, path, explain
- Settings
- main.py
- test_api_security.py
- test_migrations.py
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- run_local.py
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- codex-bootstrap.sh
- afisha-onboard/SKILL.md
- afisha-p0-review/SKILL.md
- conftest.py
- extraction-spec.md
- react-big-calendar.d.ts
- codex-preflight.sh

## God Nodes (most connected - your core abstractions)
1. `EventService` - 28 edges
2. `Event` - 22 edges
3. `Журнал решений (ADR-lite) — Afisha` - 21 edges
4. `CategoryService` - 19 edges
5. `InvalidImageError` - 18 edges
6. `User` - 16 edges
7. `compilerOptions` - 16 edges
8. `UserService` - 15 edges
9. `image_bytes()` - 15 edges
10. `upload()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Event` --uses--> `Category`  [INFERRED]
  backend/app/schemas/event.py → backend/app/schemas/category.py
- `EventService` --uses--> `InvalidImageError`  [INFERRED]
  backend/app/services/event_service.py → backend/app/services/exceptions.py
- `service()` --uses--> `EventService`  [INFERRED]
  backend/tests/test_image_upload.py → backend/app/services/event_service.py
- `CalendarGridProps` --references--> `Event`  [EXTRACTED]
  frontend/src/components/CalendarGrid.tsx → frontend/src/services/api.ts
- `EventCardProps` --references--> `Event`  [EXTRACTED]
  frontend/src/components/EventCard.tsx → frontend/src/services/api.ts

## Import Cycles
- None detected.

## Communities (66 total, 11 thin omitted)

### Community 0 - "AGENTS.md"
Cohesion: 0.08
Nodes (31): AGENTS.md — инструкции для AI-агентов проекта Afisha, graphify, Локальное окружение Codex, Миссия, Правила работы и проверки, Репозиторий и ветки, Сначала прочитай, Технологическая база (текущее состояние) (+23 more)

### Community 1 - "EventService"
Cohesion: 0.08
Nodes (33): create_event(), delete_event(), delete, EventCreate, EventUpdate, get, post, put (+25 more)

### Community 2 - "test_image_upload.py"
Cohesion: 0.11
Nodes (35): upgrade(), UploadFile, CategoryError, InvalidImageError, Custom exceptions used by the service layer., Raised when an uploaded image does not meet validation rules., Base class for category related errors., Base class for service layer errors. (+27 more)

### Community 3 - "categories.py"
Cohesion: 0.11
Nodes (28): get_category_service(), get_event_service(), get_user_service(), Session, Dependency providers for FastAPI routers., create_category(), delete_category(), list_categories() (+20 more)

### Community 4 - "package.json"
Cohesion: 0.06
Nodes (34): autoprefixer, browserslist, development, production, devDependencies, autoprefixer, postcss, react-scripts (+26 more)

### Community 5 - "dependencies"
Cohesion: 0.07
Nodes (29): axios, date-fns, dependencies, axios, date-fns, lucide-react, react, react-big-calendar (+21 more)

### Community 6 - "Engineering Review: Бизнес Афиша"
Cohesion: 0.07
Nodes (26): 1. Текущая архитектура и границы проверки, 2. Сильные стороны реализации, 3. Проблемы и риски P0/P1/P2, 4. React SPA и Next.js для этого проекта, 5. Рекомендации для архитектуры MVP, 6. Что исправить до дальнейшей разработки и запуска, 7. Что можно отложить, 8. Архитектурные решения владельца и статус workflow (+18 more)

### Community 7 - "🎭 Афиша мероприятий - Инструкция по запуску"
Cohesion: 0.07
Nodes (26): 1. Запуск бэкенда, 2. Запуск фронтенда, 🔧 API Endpoints, Адаптивность:, 🎭 Афиша мероприятий - Инструкция по запуску, 🚀 Быстрый запуск, Вариант 1: Запуск всего проекта одной командой, Вариант 2: Пошаговый запуск (+18 more)

### Community 8 - "User"
Cohesion: 0.16
Nodes (19): Base, Declarative base class for SQLAlchemy models., Category, Категория мероприятия, управляемая через админ-панель., Event, User, create_admin_user(), get_available_images() (+11 more)

### Community 9 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 10 - "Требования к продукту — Afisha Business MVP"
Cohesion: 0.09
Nodes (23): 1. Пользователи и задачи, 2. Приоритеты, 3. Информационная архитектура (проектная), 4. Предлагаемая модель данных, 5. Бизнес-правила, 6. UX-предпосылки, 7. Нефункциональные требования, 8. Open questions для владельцев продукта (+15 more)

### Community 11 - "Afisha: предпроектный продуктовый разбор"
Cohesion: 0.09
Nodes (22): 10. Сопоставление двух проходов и разрешение противоречий, 11. Решения владельца до продолжения разработки, 12. Сохранность работы и контроль результата, 1. Вывод для владельца, 2. Основания и пределы вывода, 3. Office-hours: проверка идеи и альтернатив, 4. Plan-ceo-review: стратегическая оценка текущего MVP, 5. Рекомендуемый MVP и сравнение scope (+14 more)

### Community 12 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowJs, allowSyntheticDefaultImports, esModuleInterop, forceConsistentCasingInFileNames, isolatedModules, jsx, lib (+13 more)

### Community 13 - "Журнал решений (ADR-lite) — Afisha"
Cohesion: 0.10
Nodes (21): D-001 — Рабочая основа репозитория, D-002 — Вертикаль продукта, D-003 — Безопасное управление схемой БД, D-004 — Публичная регистрация, D-005 — Платёжная модель MVP, D-006 — Публичный frontend, D-007 — Данные посещаемости, D-008 — Управление рекламой (+13 more)

### Community 14 - "HomePage.tsx"
Cohesion: 0.14
Nodes (13): Contact(), DateScroller(), DateScrollerProps, DayItem, isWeekendRu(), EventModal(), Footer(), Header() (+5 more)

### Community 15 - "services/api.ts"
Cohesion: 0.13
Nodes (14): EventsListProps, PRODUCTION_API_ORIGIN, AdminDashboard(), api, CategoryCreatePayload, CategoryUpdatePayload, EventCreate, EventListParams (+6 more)

### Community 16 - "Технический план реализации MVP «Бизнес Афиша» — v2.1"
Cohesion: 0.10
Nodes (19): 0. Что исправлено относительно v2.0, 10. Порядок и независимость PR, 1. Фактическое состояние (проверено 2026-11-12), 2. Данные и семантика datetime — миграция заблокирована, 3. Приоритеты, 4.1 Диапазон дат (A), 4.2 Время в админке (B), 4.3 Отмена и жизненный цикл (C) (+11 more)

### Community 17 - "Event"
Cohesion: 0.14
Nodes (10): AdvancedCalendarProps, CalendarEvent, locales, localizer, CategorySection(), CategorySectionProps, EventModalProps, EventsCalendarProps (+2 more)

### Community 18 - "auth/auth.py"
Cohesion: 0.22
Nodes (7): Alembic environment; schema changes never happen on application import., get_password_hash(), verify_password(), get_db(), create_admin(), Password hashing regression tests (no credentials in logs)., test_password_hashing()

### Community 19 - "check_dependencies.py"
Cohesion: 0.18
Nodes (15): check_auth(), check_database_connection(), check_models(), check_package(), check_python_version(), check_requirements(), check_static_files(), main() (+7 more)

### Community 20 - "Контекст разработки Afisha — технический снимок"
Cohesion: 0.12
Nodes (16): 10. 2026-11-12 — предпроектный аудит и план MVP (документация), 1. Продуктовая цель, 2. Что уже было в старом репозитории, 3. Что изменилось при восстановлении в master, 4. Критические и существенные незакрытые задачи, 5. Локальная работа и проверки, 6. Инфраструктура, 7. Интеграция новых агентов (+8 more)

### Community 21 - "routers/auth.py"
Cohesion: 0.25
Nodes (12): get, User, read_users_me(), register(), BaseModel, Token, TokenData, User (+4 more)

### Community 22 - "Паспорт проекта — Afisha / Бизнес-афиша Новосибирска"
Cohesion: 0.13
Nodes (15): 10. Сроки и бюджет (не обязательства), 11. Критерии приёмки MVP, 12. Риски и ограничения, 13. Принятие изменений, 1. Идея и проблема, 2. Целевые аудитории, 3. Ценностное предложение, 4. Цель MVP (+7 more)

### Community 23 - "UserService"
Cohesion: 0.22
Nodes (8): Raised when attempting to create a user that already exists., UserAlreadyExistsError, Service layer for the Afisha backend., Session, User, High level API for working with users., UserService, PasswordHasher

### Community 24 - "schema.py"
Cohesion: 0.23
Nodes (11): Utility helpers for low-level application concerns., ColumnRequirement, ensure_column(), ensure_columns(), _quoted(), Helpers for inspecting and amending database schemas at runtime., Describe a column that should exist on a database table., Return an SQL identifier quoted for safe interpolation. (+3 more)

### Community 25 - "Передача контекста следующему агенту — Afisha"
Cohesion: 0.15
Nodes (13): 2026-11-12 — P0: безопасная загрузка изображений, 2026-11-12 — предпроектный аудит и согласование плана (только документация), 2026-11-12 — финальная проверка перед PR, НЕ подтверждено, Первый технический спринт (исходный план; актуальный статус ниже), Передача контекста следующему агенту — Afisha, Подготовка среды Codex (добавлено 2026-11-12), Прочитать перед действиями (+5 more)

### Community 26 - "Roadmap — Бизнес Афиша: публичный MVP"
Cohesion: 0.15
Nodes (13): Roadmap — Бизнес Афиша: публичный MVP, Гейты качества, Открытые решения владельца, Отложено, Принятая стратегия (кратко), Этап 0. Стабилизация и безопасность — IN PROGRESS, Этап 1. Модель данных и публикация — TODO, Этап 2. Время и диапазоны дат — частично BLOCKED (+5 more)

### Community 27 - "authenticate_user"
Cohesion: 0.20
Nodes (12): authenticate_user(), create_access_token(), get_current_admin_user(), get_current_user(), Session, User, login(), post (+4 more)

### Community 28 - "App.tsx"
Cohesion: 0.23
Nodes (8): App(), ProtectedRoute(), ProtectedRouteProps, root, AdminLogin(), LoginForm, HomePage(), authApi

### Community 29 - "EventsFeed.tsx"
Cohesion: 0.24
Nodes (8): EventCard(), EventCardProps, TODO: Share event, TODO: Share event, EventFilters(), EventFiltersProps, FilterState, Category

### Community 30 - "Интеграция с Яндекс.Директ"
Cohesion: 0.17
Nodes (11): 1. Получение кода рекламы, 2. Замена заглушки на реальный код, 3. Альтернативный способ (рекомендуемый), Интеграция с Яндекс.Директ, Интеграция с Яндекс.Директ, Описание, Примечания, Размеры баннера (+3 more)

### Community 31 - "Codex: подготовка рабочего места Afisha"
Cohesion: 0.18
Nodes (11): 1. Синхронизация локальной папки, 2. Диагностика без установки, 3. Установка зависимостей приложения (отдельное действие), 4. Установка gstack для Codex — опционально, 5. Локальные скиллы, уже находящиеся в репозитории, 6. Экономный стартовый запрос, 7. Проверки после установки, Codex: подготовка рабочего места Afisha (+3 more)

### Community 32 - "check_status.py"
Cohesion: 0.29
Nodes (9): check_backend(), check_database(), check_dependencies(), check_frontend(), main(), Проверяет статус бэкенда, Проверяет статус фронтенда, Проверяет базу данных (+1 more)

### Community 33 - "Release checklist — публичный запуск «Бизнес Афиши»"
Cohesion: 0.20
Nodes (9): 1. Безопасность авторизации и API, 2. Данные и публикация, 3. Время и диапазоны дат, 4. Публичный сайт и SEO, 5. Маршрутизация и сборка, 6. Эксплуатация, 7. Аналитика (D-017), 8. Контент и операции (параллельно разработке) (+1 more)

### Community 34 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 35 - "CalendarGrid.tsx"
Cohesion: 0.39
Nodes (8): addDays(), CalendarGrid(), CalendarGridProps, dayKey(), endOfMonth(), parseEventDate(), startOfMonth(), startOfWeek()

### Community 36 - "План PR-1: ограничение попыток входа и доверие proxy"
Cohesion: 0.25
Nodes (7): Критерии приёмки, План PR-1: ограничение попыток входа и доверие proxy, Порядок, После PR-1, Риски, Цель и границы, Что известно о stash

### Community 37 - "manifest.json"
Cohesion: 0.25
Nodes (7): background_color, display, icons, name, short_name, start_url, theme_color

### Community 38 - "run_seed.py"
Cohesion: 0.40
Nodes (5): main(), Запускает команду и возвращает результат, Ждет пока сервер станет доступен, run_command(), wait_for_server()

### Community 39 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 40 - "Settings"
Cohesion: 0.50
Nodes (3): Settings, BaseSettings, field_validator

### Community 41 - "main.py"
Cohesion: 0.50
Nodes (3): health_check(), get, read_root()

### Community 43 - "test_migrations.py"
Cohesion: 0.60
Nodes (4): Alembic migration safety tests using disposable SQLite databases., run_upgrade(), test_fresh_database_migrates_and_repeat_is_safe(), test_legacy_database_is_not_modified()

### Community 44 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 45 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 46 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **342 isolated node(s):** `name`, `version`, `private`, `@types/node`, `@types/react` (+337 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `EventService` connect `EventService` to `test_image_upload.py`, `categories.py`, `UserService`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Why does `Требования к продукту — Afisha Business MVP` connect `Требования к продукту — Afisha Business MVP` to `AGENTS.md`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Why does `Afisha: предпроектный продуктовый разбор` connect `Afisha: предпроектный продуктовый разбор` to `AGENTS.md`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `EventService` (e.g. with `EventNotFoundError` and `InvalidDateFilterError`) actually correct?**
  _`EventService` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `CategoryService` (e.g. with `CategoryAlreadyExistsError` and `CategoryNotFoundError`) actually correct?**
  _`CategoryService` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `InvalidImageError` (e.g. with `EventService` and `test_animated_images_are_rejected()`) actually correct?**
  _`InvalidImageError` has 11 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `private` to the rest of the system?**
  _342 weakly-connected nodes found - possible documentation gaps or missing edges._