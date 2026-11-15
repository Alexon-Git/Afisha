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
python3 -m unittest discover -s public/tests -p test_compose_isolation.py -v
bash public/tests/compose-smoke.sh --config-only
bash public/tests/compose-smoke.sh
python3 public/tests/image-smoke.py afisha-pr10-image-test:local
```

Требуются Docker Compose и Python 3. Shell-скрипт делегирует stdlib runner
`compose_smoke.py`. **BLOCKER review:** прежний вариант наследовал shell env,
который мог переопределить test.env. Он заменён единым runner с очищенным
окружением (только фиксированный PATH и HOME), явным Docker config и context.
DATABASE_URL/секреты/COMPOSE_*/DOCKER_* из shell не наследуются, включая TMPDIR.
Контекст по умолчанию desktop-linux разрешён только с локальным Unix socket
`~/.docker/run/docker.sock`; `--context default` — только `/var/run/docker.sock`.
Иной endpoint, отсутствие socket или daemon не Linux дают безопасный отказ.
После проверки endpoint закрепляется через --host для всех дальнейших команд.
Глобальные contexts/settings не меняются. Произвольные удалённые daemons не поддержаны.

До build/up валидируется `compose config --format json`: точные services,
project/network/volume, отсутствие external и неожиданных mounts/overrides,
DATABASE_URL только db:5432/afisha_db, случайные test-only secrets текущего
запуска, uploads только в новом временном каталоге, localhost ports. Существующий
volume/network/project с сгенерированным именем вызывает отказ. Проверенный JSON
сохраняется с правами 0600 и используется всеми дальнейшими Compose-командами.
Секреты и stderr/config с потенциальными секретами не печатаются.

`--config-only` выполняет только чтение/проверку, не build/up/down/volume rm.
Регрессионные тесты используют настоящий config parser и config-only CLI с
конфликтующим окружением; ошибки up/cleanup и подмена endpoint проверяются
mock-командами, без удалённого подключения или изменения чужих ресурсов.
Тесты требуют доступного разрешённого локального Docker daemon.

Полный smoke создаёт уникальные project/volume/uploads и случайные credentials;
не читает backend/.env. Применяются существующие миграции 0001–0003 только на
пустой тестовой БД. Порты фиксированы: 58039 DB, 58040 backend, 53010 public;
shell-переопределения PR10_TEST_* больше не используются. Если порт занят, up
откажет и cleanup уберёт только свой новый проект.
До начала up cleanup не выполняет Docker-операций. После up (включая ошибку)
он использует тот же socket/project/проверенный JSON; volume rm разрешён только
для нового точного имени с совпадающим project label. Нет down -v/remove-orphans.
Временные файлы удаляются при ошибках и SIGINT/SIGTERM; после SIGKILL/аварии daemon
может понадобиться ручная проверка своих тестовых ресурсов. Образы остаются для осмотра.
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
