# План PR-1: ограничение попыток входа и доверие proxy

**Статус:** подготовка, реализация не начата. **Дата:** 2026-11-12.
Источник работы: `stash@{0}` (`ff658e9`). Stash не применять через `pop`, не удалять и не менять до успешной интеграции в `master`.

## Цель и границы
Закрыть A1 (нет лимита попыток логина) и A2 (`ProxyHeadersMiddleware(trusted_hosts="*")`). Не включать: обновление зависимостей, `.dockerignore`, изменения модели Event, документацию аудита. `python-multipart` (A3) и `.dockerignore` (A7) — отдельные PR.

## Что известно о stash
- Изменены 16 файлов, из них кодовые: `backend/Dockerfile`, `backend/app/auth/auth.py`, `config.py`, `dependencies.py`, `main.py`, `models/__init__.py`, `routers/auth.py`, `backend/docker-compose.yml`, `backend/env.compose.example`, `backend/env.example`, `backend/start.py`, `backend/tests/test_migrations.py`. Документы: `backend/MIGRATIONS.md`, `docs/AGENT_HANDOFF.md`, `docs/DECISIONS.md`, `docs/DEVELOPMENT_CONTEXT.md`.
- Новые файлы (в `stash@{0}^3`): `alembic/versions/0002_login_attempts.py`, `models/login_attempt.py`, `services/login_limiter.py`, `tests/test_login_rate_limiting.py`.
- Заявленное поведение (из D-011 в stash, **мной не проверялось на выполнение**): таблица `login_attempts`, UPSERT-резервирование до проверки пароля, 5 попыток на аккаунт и 30 на источник за 900 с, HMAC-ключи, 429 с `Retry-After`, 503 при отказе хранилища (fail closed), `--no-proxy-headers`.

## Порядок
1. **Подготовка.** Запустить Docker Desktop (сейчас daemon недоступен), убедиться, что есть PostgreSQL 17. Убедиться, что рабочее дерево чистое: сейчас в `audit/predevelopment-review` лежат неотслеживаемые `docs/audits/`, `TECHNICAL_PLAN.md` и правки `docs/`.
2. `git switch master` → `git switch -c fix/auth-rate-limiting-integration` (ветку `fix/auth-rate-limiting` не трогать).
3. Восстановить **только код** поимённо: `git checkout 'stash@{0}' -- <12 кодовых путей>` и `git checkout 'stash@{0}^3' -- <4 новых файла>`. Документы из stash не брать.
4. Прочитать полный diff по файлам; проверить: `main.py` без wildcard-middleware; `docker-compose.yml` убирает или обновляет собственный `command` (иначе флаг из Dockerfile не действует); `0002` не меняет `users`.
5. Тесты на SQLite: весь `pytest -q`, затем отдельно `test_login_rate_limiting.py` и `test_migrations.py`.
6. PostgreSQL: `alembic upgrade head`, `downgrade -1`, `upgrade head` на чистой БД и на копии со старой схемой (`0001` → `0002`).
7. Конкурентность на PostgreSQL: параллельные запросы к одному аккаунту не превышают лимит; отказ хранилища даёт 503 без токена; успешный вход не сбрасывает прежние неудачи (поведение из D-011).
8. Прямые проверки: поддельный `X-Forwarded-For` не меняет ключ источника; логин неизвестного пользователя обрабатывается так же по времени и коду.
9. Добавить в PR решение о принятых пороговых значениях и компромиссе (временная блокировка аккаунта может быть использована для DoS).
10. Коммит только поимённо добавленных файлов; `git status` перед коммитом. Push, PR и merge — только по отдельной команде владельца.

## Критерии приёмки
- Все тесты зелёные на SQLite и PostgreSQL; результаты приложены.
- Источник запроса не берётся из непроверенных заголовков; настройка реального прокси описана отдельно (R2).
- Миграция откатывается.
- В PR нет документов аудита и нет лишних файлов.

## Риски
- Конфликты правок `DECISIONS.md`, `AGENT_HANDOFF.md`, `DEVELOPMENT_CONTEXT.md` между stash и текущими документами: разрешать вручную, по шаблону из `CLAUDE.md` проекта (источник правды — шаблоны/документы текущей ветки). D-011 из stash вставить в `DECISIONS.md` отдельным коммитом.
- За Nginx источник «общий» (все запросы с адреса прокси), пока доверие proxy не настроено: это ослабляет лимит по источнику; решается в T8.
- Лимиты по аккаунту допускают блокировку чужого аккаунта.

## После PR-1
Stash оставить до подтверждённого merge. Удаление — только по явной команде владельца.
