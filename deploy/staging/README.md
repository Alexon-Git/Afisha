# Изолированное staging «Бизнес Афиши»

Закрытое окружение для тестирования владельцем и партнёром. Не production.
Образы собираются из одного commit SHA вне VPS и переносятся готовыми. Сервер,
Caddy, DNS и firewall этим PR не меняются.

## Схема

```
интернет ─(будущий Caddy, HTTPS)─> nginx :8080 (Basic Auth на всё, X-Robots-Tag noindex)
                                     ├─ /            -> public (Next.js)
                                     ├─ /admin/      -> CRA из образа nginx
                                     ├─ /api/        -> backend (FastAPI), JWT проверяет backend
                                     └─ /static/uploads/ -> volume uploads (read-only)
сеть internal (internal: true, без выхода наружу): db, migrate, backend, public, nginx
сеть edge: только nginx; порт публикуется на 127.0.0.1:${STAGING_PORT}
```

Файлы: `docker-compose.staging.yml`, `.env.staging.example`, `nginx/` (слой поверх
образа проекта: пароль, noindex), `scripts/` (build-images, init-env, preflight,
backup, restore-check), `tests/staging-smoke.sh`.

- Свой Compose project, сети, тома `db_data` и `uploads`, своя БД `afisha_staging`.
  Подсеть задаётся в env и проверяется `preflight.sh` на пересечение. Фиксированный
  адрес Nginx лежит вне `ip_range`, который выдаётся остальным контейнерам.
- PostgreSQL и backend порты не публикуют. Nginx слушает `127.0.0.1` по умолчанию.
- Backend доверяет `X-Forwarded-*` только от точного IP Nginx (`STAGING_NGINX_IP`).
  Настройки локального gateway подсеть не доверяют и сюда не копировались.
- `SITE_URL` пуст: meta noindex, `robots.txt` Disallow, sitemap 503. `AD_ENABLED=false`,
  ID блоков нет. Реальные данные не использовать, тестовые записи называть `[ТЕСТ] …`.
- Лимиты памяти/CPU/pids, ротация логов 10 MB x 3, `restart: unless-stopped`.

## Доступ

Весь сайт, включая `/admin` и `/api`, закрыт Basic Auth. Исключение: запросы `/api/*`
с заголовком `Authorization: Bearer …` (кроме `/api/auth/login`) пропускаются, потому
что SPA передаёт JWT именно так. JWT проверяет FastAPI, поддельный токен получает 401.
Это не заменяет VPN/IP-ограничение; решение о способе доступа за владельцем.

## Запуск (локально или на сервере, шаги те же)

```bash
# 1. На сборочной машине, из чистого коммита:
deploy/staging/scripts/build-images.sh <full-sha> [--platform linux/amd64]
docker save afisha-staging/{backend,public,nginx}:<sha> | gzip > release.tgz   # перенос без registry
# 2. На целевой машине:
docker load < release.tgz
cd deploy/staging && scripts/init-env.sh <sha> tester     # один раз; печатает пароли в терминал
# при необходимости отредактировать STAGING_* в .env.staging (подсеть, порт)
scripts/preflight.sh
C="docker compose --env-file .env.staging -f docker-compose.staging.yml"
$C config -q && $C up -d
GATE_USER=tester GATE_PASS=<пароль> tests/staging-smoke.sh
```

Открыть: `http://127.0.0.1:${STAGING_PORT}/`, браузер спросит логин/пароль доступа.
Админка: `/admin/login` (`ADMIN_USERNAME`/`ADMIN_PASSWORD` из `.env.staging`).
Секреты лежат только в `.env.staging` и `secrets/` (оба в `.gitignore`, права 600).

## Обновление

1. `scripts/backup.sh`, скопировать каталог бэкапа за пределы хоста.
2. Собрать и загрузить новые образы, поменять три `*_IMAGE` в `.env.staging`.
3. `$C up -d` пересоздаёт только изменившиеся сервисы; `migrate` применит Alembic до head
   нового образа (0009 сейчас, 0010 после PR-18). Тома не затрагиваются.
4. `tests/staging-smoke.sh`.

## Откат

- Приложение, схема не менялась: вернуть прежние `*_IMAGE`, `$C up -d`.
- Миграция не совместима с прежним образом: остановить `backend public nginx`,
  восстановить БД из бэкапа (ниже) и вернуть прежние образы. `alembic downgrade`
  использовать только после проверки: downgrade 0009 удаляет статьи.

## Резервные копии и восстановление

```bash
scripts/backup.sh /путь/backups        # db.dump (pg_dump -Fc), uploads.tar, alembic_revision.txt, SHA256SUMS
scripts/restore-check.sh /путь/backups/<метка>   # проверка в одноразовом postgres:17, стек не трогает
```

Восстановление в работающий staging (только после остановки приложения, с отдельного
разрешения, потому что это перезапись данных):

```bash
$C stop backend public nginx
$C exec -T db psql -U afisha -d postgres -c "DROP DATABASE afisha_staging" -c "CREATE DATABASE afisha_staging"
$C exec -T db pg_restore -U afisha -d afisha_staging --no-owner < backups/<метка>/db.dump
# uploads: распаковать uploads.tar в том ${COMPOSE_PROJECT_NAME}_uploads через одноразовый контейнер
$C up -d
```

Бэкап снимать до каждого обновления и хранить вне сервера. Успешность восстановления
подтверждает только `restore-check.sh`, наличие файла её не доказывает.

## Логи и состояние

```bash
$C ps
$C logs --tail 100 -f backend        # также: nginx, public, db, migrate
docker stats --no-stream $($C ps -q)
```

Запрещено: `down -v`, `system prune`, `volume prune`, удаление чужих сетей/томов.
Остановка staging: `$C down` (тома сохраняются).

## Что нужно для реального VPS

Отдельный сервер или подтверждённое увеличение ресурсов (ориентир от 2 vCPU, 4 GiB RAM,
30–40 GiB SSD; текущий VPS «Харизмы» 1 vCPU/1 GiB не подходит); домен и HTTPS; решение
о способе закрытого доступа; для схемы Caddy → Nginx отдельная доработка доверия
(`STAGING_BIND`, exact-IP trust Caddy в Nginx, очистка forged headers, проверка
rate-limit `/admin/login`) и план изменения Caddy с откатом. Все эти шаги требуют
отдельного согласования.
