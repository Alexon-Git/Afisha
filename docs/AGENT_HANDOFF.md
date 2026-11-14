# Передача контекста следующему агенту — Afisha

**Состояние на:** 2026-11-12  
**Репозиторий:** https://github.com/Alexon-Git/Afisha  
**Default branch:** `master`  
**Историческая база:** `main` (не удалять).

## Прочитать перед действиями

`AGENTS.md` → `docs/PROJECT_PASSPORT.md` →
`docs/PRODUCT_REQUIREMENTS.md` → `docs/ROADMAP.md` →
`docs/DEVELOPMENT_CONTEXT.md` → `docs/DECISIONS.md` →
`backend/MIGRATIONS.md`.

## Актуальная передача: исправление C5 в PR #21 (2026-11-14)

- Ветка `fix/event-editor-reliability`, база исправления `b6bcabf`.
  Нормализатор локальных uploads URL теперь общий для путей, flock и проверки
  ссылок; допустимые query/fragment указывают на тот же физический файл.
- Очистка сравнивает нормализованные ссылки и сохраняет файл при любой
  непустой нераспознанной ссылке. Консервативные orphan-файлы остаются задачей GC.
  Порядок после commit, защита symlinks и обработка cleanup failures сохранены.
- Проверено: lifecycle **61 passed**, один полный backend pytest **228 passed**,
  compileall и diff-check успешны. C2–C4/frontend/модели/миграции/API не менялись.
- Следующее действие: повторное независимое review PR #21 после fix-коммита
  и нового CI. Merge/deploy и переход к PR-6 не выполняются.

## Передача PR-5 (2026-11-13, до исправления MAJOR)

- PR #20 merged (`99d0800`); PR-5 реализован в отдельном worktree
  `.worktrees/afisha-pr5`, ветка `fix/event-editor-reliability` от актуальной
  `origin/master`. C2/C3/C4/C5 разделены логическими коммитами.
- C2: PUT null для обязательных полей → 422, partial update сохраняет остальные
  поля; category_id проверяется перед записью, null снимает категорию;
  диапазоны price/rating/discount согласованы с формой. Реальный HTTP
  PUT/POST проверен на loopback, без production-БД.
- C3: server pagination по 50, total/current/previous/next; loading/empty/error
  и retry; refresh после записи; возврат на доступную страницу после удаления.
- C4: устаревшие запросы не публикуют результаты/loading; ошибка актуального
  запроса очищает обе группы; unmount блокирует дальнейшие обновления.
- C5: очистка после commit и проверки ссылок, только собственные UUID-файлы;
  FS/lookup failure не ломает успешную мутацию. Shared/exclusive inode flock
  координирует привязку и cleanup между backend-процессами одного POSIX FS.
  Недоступная собственная загрузка → 422; symlink/external/legacy не удаляются.
  Удаление изображения в форме теперь явно отправляет image_url=null.
- Итог: backend **191 passed**, React **12 passed**, production build и
  compileall успешны; diff-check чистый. Backend предупреждения — устаревшие
  интерфейсы зависимостей; build предупреждения — устаревшая browser data.
  Новых зависимостей, миграций, изменений моделей и TZ-контракта нет.
- Orphan-файлы сохраняются после незавершённой формы/отложенного cleanup.
  Будущий GC: отдельная команда с dry-run, grace period, inode lock и повторной
  проверкой ссылок; детали в DEVELOPMENT_CONTEXT. Windows/новый тип storage
  потребует пересмотра flock-политики. Реальные uploads не использовались.
- Следующее действие: review опубликованного PR-5, дождаться решения владельца.
  Merge/deploy не выполнялись; stash `ff658e9`, старые worktrees, AGENTS,
  Graphify и локальные настройки сохранены. К следующему PR не переходить.

## Передача PR-4 (исторический снимок до merge)

- PR #19 уже merged; проверенная база PR-4 — `origin/master` `2156f1b`.
  Ветка `fix/event-date-filters`, отдельный worktree `.worktrees/afisha-pr4`.
- Реализованы строгие календарные даты и полуоткрытые naive SQL-границы,
  относительные дни Asia/Novosibirsk и HTTP 400 вместо отключения фильтра.
  Один `date_from` или `date_to` выбирает один день; диапазон важнее `date`.
  В воскресенье weekend включает текущую субботу и воскресенье.
- Пустой переданный параметр ошибочен; неизвестная категория не скрывает
  ошибку даты. Диапазон включаемых дней: `0001-01-01`…`9999-12-30`;
  `9999-12-31` отклоняется с 400 из-за невозможности вычислить следующий день.
- Полный backend pytest: **142 passed**, 108 предупреждений зависимостей.
  Compileall и diff-check успешны. Добавлен 61 тест, в том числе настоящий
  loopback HTTP через Uvicorn; данные только во временной SQLite. Первый
  локальный запуск 60/61 прошёл, HTTP bind был заблокирован sandbox;
  полный запуск с разрешённым loopback прошёл целиком.
- Изменены только сервис/роутер events, новый тест и три документа.
  Модели, миграции, зависимости, frontend, старые worktrees, Graphify,
  локальная память и stash `ff658e9` не изменялись.
- Следующий шаг: независимое review PR-4 и решение владельца о merge.
  Merge/deploy не выполнялись. PR-8 остаётся зависимым от выяснения семантики
  старых naive datetime; к PR-5 без команды не переходить.

## Текущая задача (историческая запись)

Завершить **этап стабилизации (P0)** до расширения модели
бизнес-мероприятий. Параллельно владелец проекта ищет сервер;
продакшен-деплой сейчас НЕ является задачей агента.

## Фактически подтверждено

- Репозиторий с кодом React + TS / FastAPI + SQLAlchemy + Alembic.
- В `master` добавлены обязательные секреты, запрет публичного
  `/auth/register`, отказ от auto-schema при запуске, безопасная
  initial Alembic migration, Docker Compose и начальные тесты.
- В `master` есть `.github/workflows/backend-ci.yml`.
- Последний **кодовый** проверенный CI-коммит: `5fe7cf6`.
  Прогон: https://github.com/Alexon-Git/Afisha/actions/runs/43194330396
  со статусом `success`.
- После этого добавлены **только документы**, они не доказывают
  новых технических результатов.

## НЕ подтверждено

- Запуск Docker Compose на PostgreSQL.
- Совместимость со старой настоящей БД.
- Frontend build, браузерное QA, E2E, мобильные сценарии.
- Реальная работа рекламного кабинета или публичных SEO-страниц.
- Подключение источников «Харизма»/«Мой бизнес».
- Установка или выполнение gstack на локальной машине.
- Выбор production-сервера и домена.

## Первый технический спринт (исходный план; актуальный статус ниже)

1. Создать `fix/security-baseline` от `master`. Не затрагивать `main`.
2. Ужесточить `EventService.save_image`: проверка реального типа
   файла, допустимые JPG/PNG/WebP, безопасный рандомный filename,
   тесты ошибочных и валидных входов, лимит размера.
3. Добавить разумную защиту `/auth/login` от перебора,
   тесты на лимит и его сброс; предусмотреть доверенный proxy/IP.
4. Пересмотреть `ProxyHeadersMiddleware(trusted_hosts="*")`.
5. Прогнать миграции на SQLite/PG в изолированных тестовых БД.
6. Проверить frontend build и публичную цепочку выбор даты → фильтр.
7. Сформировать отчёт P0/P1/P2, PR в `master`, обновить docs.

## Что агенту запрещено делать автоматически

- Запускать миграции, `alembic stamp`, `downgrade` на реальной
  БД без бэкапа и подтверждённого плана.
- Менять `main` или принудительно обновлять `master`.
- Публиковать сайт, раскрывать пароли, токены, .env или персональные данные.
- Выдавать планируемые требования за действующий функционал.
- Устанавливать/запускать сторонние инструменты без оценки их
  полномочий и разрешения пользователя.

## Формат завершения задачи

Добавить запись в конец этого файла:

```markdown
### YYYY-MM-DD — краткая задача
- Ветка / PR / коммит:
- Изменённые файлы:
- Реально выполненные тесты и результаты:
- Открытые дефекты и ограничения:
- Следующая проверяемая задача:
```

Также обновить `DEVELOPMENT_CONTEXT.md` и, если было принято
архитектурное решение, `DECISIONS.md`.

## Синхронизация с локальной папкой пользователя

После сохранения коммитов в GitHub пользователь выполняет
`git pull origin master` **из своей уже клонированной папки**.
Если папка пустая, сначала следует клонировать репозиторий:
`git clone --branch master https://github.com/Alexon-Git/Afisha.git .`
(выполнять только в действительно пустой директории).

GitHub-коммиты и файлы на личном Mac не синхронизируются автоматически.

## Подготовка среды Codex (добавлено 2026-11-12)

- Документ по локальному запуску: `docs/CODEX_SETUP.md`.
- Префлайт: `bash scripts/codex-preflight.sh` (без изменений файлов).
- Опциональная установка зависимостей: `bash scripts/codex-bootstrap.sh --deps`.
- Собственные проектные скиллы: `.agents/skills/afisha-onboard` и `.agents/skills/afisha-p0-review`.
- Это изменение относится к подготовке агента; **не означает** установки gstack или запуска тестов на Mac.

### 2026-11-12 — P0: безопасная загрузка изображений
- Ветка / PR / коммит: `fix/image-upload-validation` от `master` (`affbd2e`).
  Пользователь разрешил коммит, push ветки и PR в `master`; изменение
  подготовлено к публикации. Merge и деплой запрещены. `main` не затронута.
- Изменённые файлы: `backend/app/services/event_service.py`,
  `backend/requirements.txt`, `backend/tests/test_image_upload.py`,
  `docs/DEVELOPMENT_CONTEXT.md`, `docs/AGENT_HANDOFF.md`.
- Реализовано: проверка JPG/PNG/WebP через Pillow (verify + load),
  перекодирование без исходных метаданных/посторонних данных с применением
  EXIF-ориентации, UUID4 + проверенное расширение, создание без перезаписи.
  Вход и выход ограничены 5 МиБ, изображение — 20 млн пикселей;
  анимированные изображения отклоняются. MIME запроса не определяет формат.
- Среда: preflight выполнен; создан `backend/.venv` на Python 3.11.17,
  установлены backend requirements-dev и новая зависимость Pillow 13.0.0.
  Frontend-зависимости и `.env` не создавались.
- Реально выполненные тесты и результаты: полный backend
  `.venv/bin/python -m pytest -q` — **48 passed**, 9 deprecation warnings
  passlib/httpx. Из них 42 теста загрузки: реальные форматы, ложный MIME,
  опасные имена, подделки, повреждения, лимиты, анимация, метаданные,
  EXIF-ориентация, API-контракт/запрет анонимной загрузки, HTTP 400 для
  исключений Pillow и отказ до вызова декодера при превышении 5 МиБ.
  `uv --no-cache pip check --python backend/.venv/bin/python` и
  `git diff --check` успешны. pip в uv-окружении отсутствует, поэтому
  первоначальная попытка `python -m pip check` заменена проверкой через uv.
- Открытые дефекты и ограничения: HTTP body до multipart-разбора этим
  изменением не ограничен; старые uploads не проверены. Перекодирование
  JPEG/WebP меняет качество. Docker/PostgreSQL, frontend и браузер не проверялись.
  Auth rate limiting и proxy trust остаются P0. Production-БД не затрагивалась.
- Личный gstack установлен ранее, preflight находит runtime; в этой задаче
  gstack и дополнительные AI-агенты не использовались. Старое «не подтверждено»
  выше относится к исходному снимку, а не к текущей локальной среде.
- Следующая проверяемая задача: после согласования текущего изменения —
  ограничение попыток `/auth/login` с тестами лимита и сброса. Не начинать
  следующую задачу, не выполнять merge или деплой автоматически.

### 2026-11-12 — финальная проверка перед PR
- Diff относительно `master` проверен: только сервис загрузки, Pillow, тесты
  и два файла контекста. Свежий `origin/master` совпадает с локальным `master`.
- Полный backend pytest: 48 passed; проверка зависимостей uv и diff --check успешны.
- Полный gstack-аудит и дополнительные агенты не запускались; прочитаны
  инструкции ship для публикации в ограниченном пользователем объёме.
- Текущая ветка: `fix/image-upload-validation`; PR должен направляться только
  в `master`. CI GitHub на момент локальной проверки ещё не подтверждён.

### 2026-11-12 — предпроектный аудит и согласование плана (только документация)
- Ветка: `audit/predevelopment-review` от `master` (`2985b5e`). Код, миграции, зависимости не менялись; push, merge и deploy не выполнялись.
- Файлы: `docs/audits/ENGINEERING_REVIEW.md`, `docs/audits/PRODUCT_REVIEW.md`, `docs/DECISIONS.md` (D-012…D-019, уточнение D-019), `docs/ROADMAP.md`, `docs/RELEASE_CHECKLIST.md`, `docs/PR1_AUTH_RATE_LIMITING_PLAN.md`, `TECHNICAL_PLAN.md` (корень).
- Утверждено владельцем: аудитория, scope MVP, публичный запуск с SEO, редактор 5–10 ч/нед, агрегация из открытых источников, 8 недель оценки, ручная B2B-монетизация, проверенный минимум полей; архитектура R1–R5 (Next.js для публичной части, админка на React SPA, один origin, UTC в БД, модель Organizer, ревью auth из stash).
- PR-1 выполнен: PR #16 влит в `master` (merge-коммит `666696e`; коммиты `b9cba12`, `138ca5e`); CI Pull Request и CI `master` после merge — success, job backend-tests пройден. Stash `ff658e9` и ветка `backup/5d9f280-original` сохранены; удалять только по явной команде владельца.
- Проверено для PR-1: SQLite (68 тестов), PostgreSQL 17, Docker Compose, реальный Nginx. Не проверено: семантика старых naive datetime (данных нет), миграция копии старой БД.
- Следующая задача: PR-2 (`python-multipart`, совместимость с FastAPI 0.104) — только после отдельной команды владельца.

### 2026-11-13 — PR-3: Docker security (локально, без публикации)
- Ветка / база: `fix/docker-security` от `origin/master` `b4622f7` (PR #18
  merged, CI success по данным владельца). Push, merge и deploy не выполнялись.
- Изменённые файлы: `backend/.dockerignore`, `backend/Dockerfile`,
  `backend/README.md`, `backend/docker-compose.yml`, `backend/env.compose.example`,
  `backend/app/static/uploads/.gitkeep`, `docs/DEVELOPMENT_CONTEXT.md` и этот файл.
- Реализовано: закрытый build context; pinned Python 3.11 base; non-root backend;
  healthcheck; единый Dockerfile CMD с миграциями/bootstrap и
  `--no-proxy-headers`; localhost-only порты; read-only rootfs, dropped caps,
  `no-new-privileges`; project-scoped контейнеры/сеть; параметризованный DB-volume
  с сохранением прежнего имени `afisha_db_data` по умолчанию.
- Проверки: Docker/Compose 29.6.2/5.3.1; build OK; canary-секрет отсутствует в
  образе; PostgreSQL 17 и миграции 0001 -> 0002 OK; `/health`, admin login,
  upload/persistence и DB persistence после пересоздания OK; 31 поддельный XFF
  остаётся одним bucket (429 + Retry-After); graceful Uvicorn stop exit 0;
  backend pytest **81 passed**, 45 warnings; compileall и diff-check OK.
- Изоляция/очистка: использованы только проект `afisha_pr3_b4622f7`, volume
  `afisha_pr3_test_db_b4622f7`, тестовые credentials и каталог в `/private/tmp`;
  production и существующие volumes не использовались. После проверки все эти
  тестовые контейнеры, сеть, volume, образы и временный каталог удалены.
- Ограничения: копия старой БД не проверена; PR-12 должен настроить конкретный
  trusted proxy/Nginx; runtime environment виден Docker-администратору;
  production secret manager, backups/restore, сервер и домен остаются release
  blockers. `codex-preflight.sh` не распознаёт Git worktree с `.git`-файлом.
- Финальное review: root-owned uploads требует перед первым non-root запуском
  одноразового `chown`/`chmod u+rwX` на точном каталоге после backup; инструкция
  добавлена в `backend/README.md` и проверена на отдельном volume без изменения
  checksum существующего файла. Это обязательный шаг обновления, не автоматизирован.
- Следующее действие: после локального коммита — review/push PR-3 только по
  отдельной команде владельца. К PR-4 автоматически не переходить.
