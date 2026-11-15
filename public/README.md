# Публичный сайт «Бизнес Афиши» — PR-10

Next.js **16.4.6**, React/React DOM **19.3.1**, TypeScript **5.9.3**.
Docker и `.nvmrc`: Node **24.22.3** LTS; Docker base image закреплён digest.
Версии проверены 2026-11-15 по npm registry и официальному Node dist index.
Требования: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation),
[Node releases](https://nodejs.org/en/about/previous-releases).
Production npm audit на момент проверки: 0 vulnerabilities; это не гарантия
отсутствия будущих advisories. Lockfile отдельный от CRA.

## Локальная разработка

Из `public/`, на Node из `.nvmrc` (при наличии nvm: `nvm use`):

```bash
cp .env.example .env.local
npm ci --ignore-scripts
npm run dev
```

Главная: `http://127.0.0.1:3001`. Для проверки соединения запустите FastAPI
отдельно по `backend/MIGRATIONS.md` с безопасной локальной БД. Без FastAPI
главная остаётся доступна и показывает контролируемое состояние недоступности.
Никакие backend credentials, JWT или DATABASE_URL этому приложению не нужны.

- `INTERNAL_API_URL`: runtime, **только сервер**, локально
  `http://127.0.0.1:8039`, в Docker `http://backend:8039`. Обязателен для
  успешной проверки FastAPI, но не для запуска/сборки Next.js. Origin http/https,
  без credentials, пути, query/fragment; production-домен не используется.
- `NEXT_PUBLIC_API_BASE=/api`: build-time адрес для будущих браузерных запросов,
  только путь текущего origin. Клиент подготовлен, но главная его не вызывает.
  Reverse proxy `/api` ещё не реализован: без PR-12 запросы браузера по нему
  не будут работать. Здесь нет rewrite/proxy на произвольный URL и изменений CORS.
- `GET /health` Next.js — собственный liveness, не проверка БД/готовности FastAPI.
  Главная проверяет `/health` FastAPI серверным GET без кеша, credentials и redirects,
  с таймаутом 5 секунд. Внутренние ошибки/адреса не выводятся посетителю.

## Проверки и standalone

```bash
npm run typecheck
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
npm run smoke
```

`typecheck` генерирует типы маршрутов без сетевого API. В tsconfig используются
рекомендованные Next.js `skipLibCheck` и strict-проверка исходников; при первой
проверке без skipLibCheck обнаружена несовместимость URLPattern в декларациях
зависимостей. Зависимости CRA этим не меняются.

Smoke запускает временный FastAPI-совместимый HTTP stub и standalone на loopback,
проверяет 200/health/static JS/404, отказ API и отсутствие internal URL в browser JS.
Это **не** замена реальной Docker-интеграции ниже. Для обычного standalone-запуска
после build нужно скопировать ресурсы (smoke делает это сам):

```bash
cp -R .next/static .next/standalone/.next/static
cp -R public .next/standalone/public
HOSTNAME=127.0.0.1 PORT=3001 INTERNAL_API_URL=http://127.0.0.1:8039 npm start
```

Standalone не загружает `.env.local` из исходной папки автоматически: задайте
runtime INTERNAL_API_URL процессу. Браузерная настройка требует новой сборки.

## Docker

Multi-stage standalone, non-root `node` (UID 1000), exec node server.js,
healthcheck; production image на проверке около 75 MB (decimal, arm64).
`.dockerignore` исключает `.env*`, node_modules, тесты и локальные артефакты.
API и ключи backend не используются при build.

Из `backend/` для **своего локального окружения**, без production-данных:

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.public.yml up --build
```

Расширение добавляет только public, общую сеть afisha и localhost:3001.
Исходный Compose, имя PostgreSQL volume и bind mount uploads не изменены.
Public получает только INTERNAL_API_URL, rootfs read-only, /tmp tmpfs,
cap_drop ALL/no-new-privileges. Backend сохраняет `--no-proxy-headers`.
Это не команда production deploy. Не используйте `down -v`.

Воспроизводимая изолированная интеграция из корня репозитория:

```bash
bash public/tests/compose-smoke.sh
python3 public/tests/image-smoke.py afisha-pr10-image-test:local
```

Требуются Docker Compose и Python 3. Первый скрипт создаёт уникальный project,
тестовый volume, временный uploads и явно тестовые credentials; не читает
backend/.env. Применяются только уже существующие миграции 0001–0003 на пустой
тестовой БД. Порты по умолчанию: 58039 DB, 58040 backend, 53010 public;
можно задать PR10_TEST_DB_PORT/PR10_TEST_BACKEND_PORT/PR10_TEST_PUBLIC_PORT.
После проверки удаляются только созданные контейнеры/сеть и volume с
подтверждённой меткой проекта. Образы остаются для осмотра.
Второй скрипт строит отдельный образ с игнорируемым .env-canary и проверяет
каждый сохранённый слой, non-root и отсутствие backend credentials в image config.

## Границы и следующие этапы

- `src/app`: layout, главная Server Component, fallback ошибок, not-found,
  liveness. CSS адаптивен, внешние шрифты/изображения не загружаются.
- `src/api`: разделённые server-only/browser клиенты и типы фактических схем
  FastAPI. Публичные клиенты используют только GET /health и /events/.
- PR-11: каталог/страница события/фильтры, окончательные metadata/OG,
  sitemap/robots/JSON-LD, политика кеша и инвалидации публикаций. Расширять
  app routes и api; окончательные id/slug маршруты ждут R11. Сейчас нет
  фиктивных событий, ссылок на неготовый каталог, ISR или SEO-разметки Event.
- PR-12: production Nginx, /api, CRA /admin, uploads и trusted proxy.
- PR-13: CI всех приложений. Текущий backend workflow не проверяет Next.js.
- PR-8 **BLOCKED**: семантика старых datetime не подтверждена. Даты в типах —
  непреобразуемые строки; они не отображаются на главной. TZ-safe редактор — PR-9.

Подтверждено локально: public ci/typecheck/6 API tests/build/standalone smoke;
реальная связка public + FastAPI + PostgreSQL 17, health/localhost/non-root,
контролируемый отказ backend; image-layer canary и bundle isolation.
CRA: 33 Jest tests + build. Backend: 86 целевых publication tests.
Production deploy, реальные данные, browser QA и общая CI-автоматизация не проверены.
