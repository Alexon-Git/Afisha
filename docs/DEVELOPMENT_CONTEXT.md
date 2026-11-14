# Контекст разработки Afisha — технический снимок

**Дата сверки с GitHub:** 2026-11-12  
**Канонический репозиторий:** https://github.com/Alexon-Git/Afisha  
**Основная ветка:** `master` (`main` — исторический исходник)  
**Статус:** реанимация старой афиши → MVP бизнес-афиши Новосибирска.

> Этот документ описывает **проверенное состояние кода на дату снимка**
> и контекст предыдущих решений. Не подменяй им повторное чтение
> затрагиваемых файлов и текущего GitHub Actions.

## PR #21 — исправление MAJOR в C5 (2026-11-14)

Поверх `b6bcabf`: единая строгая нормализация локального UUID-пути с
допустимыми ASCII query/fragment; путь не декодируется, внешние/вложенные/
traversal/неоднозначно закодированные URL не признаются собственными.
Проверка ссылок сравнивает нормализованные пути всех непустых image_url,
под существующим exclusive inode lock; привязка вариантов URL использует
тот же shared lock. Нераспознанная непустая ссылка консервативно откладывает
cleanup: это может сохранять orphan-файлы, но не удаляет потенциально нужный файл.
Post-commit порядок, O_NOFOLLOW и best-effort обработка ошибок сохранены.
Целевые lifecycle-тесты: **61 passed**; полный backend pytest после исправления
один раз: **228 passed**, 189 deprecation warnings. Compileall и diff-check
успешны. Frontend, API-схемы, модели, миграции и зависимости не менялись.

## PR-5 — надёжность редактора C2–C5 (2026-11-13)

База `origin/master` — `99d0800`, PR #20 уже merged. Изменения в
`fix/event-editor-reliability` подготовлены к review; merge/deploy не выполнялись.

- C2: явный null для title/datetime/location в PUT даёт 422; неуказанные поля
  остаются прежними. Категория проверяется до изменения записи (null удаляет
  связь). Входные price >= 0, rating 0–10, discount 0–100; ограничения только
  на write-схемах, чтобы старые данные не ломали чтение каталога.
- C3: админка запрашивает страницы по 50 событий и показывает номер, total,
  previous/next, загрузку, пустое состояние и ошибку с повтором. После создания
  обновляет первую страницу, после редактирования — текущую; если страница
  исчезла после удаления, запрашивает последнюю доступную. Устаревшие ответы
  игнорируются. Backend-контракт и порядок сортировки сохранены.
- C4: загрузка главной привязана к жизненному циклу effect выбранных дат;
  только актуальный запрос публикует обе группы событий и меняет loading.
  Ошибка текущего запроса очищает обе группы; unmount отменяет публикацию.
  Сетевые запросы не прерываются, но их устаревшие результаты не используются.
- C5: старый файл очищается после успешного commit удаления/замены/сброса
  image_url, только если в БД нет других ссылок. Только canonical URL
  `/static/uploads/<32 lowercase hex>.(jpg|png|webp)` с допустимыми
  query/fragment считаются собственными (исправление 2026-11-14 выше).
  Внешние URL, legacy-имена, вложенные пути и symlinks не удаляются.
  Ошибки cleanup оставляют файл и не меняют успешный ответ мутации.
  Админка явно отправляет image_url=null при удалении изображения.
- Привязка собственного файла держит shared `flock` до commit; cleanup берёт
  exclusive nonblocking lock того же inode до проверки ссылок/unlink. При
  занятом файле cleanup откладывается. Ссылка на уже удалённый/недоступный
  собственный файл даёт 422 до изменения записи, включая случай открытия
  файла перед unlink и получения lock после него (`st_nlink == 0`).
  Это локальная POSIX-политика для Linux Docker/macOS с общим uploads FS,
  без новых lock-файлов/таблиц/зависимостей. Для Windows, нескольких несвязанных
  uploads FS, сетевого или объектного хранилища потребуется отдельное решение;
  прямые SQL-записи обходят координацию сервиса.

Проверки: Python 3.11, полный backend `pytest -q` — **191 passed**, 154 известных
deprecation warnings; `compileall -q app alembic tests` успешен. 49 новых backend
тестов: валидация/атомарность отклонения, реальные HTTP PUT/POST 200/422,
shared images, commit/unlink/lookup failures, пути/symlinks и конкурентная
привязка/очистка. Данные и файлы только в pytest tmp_path/SQLite.
React/Jest: **12 passed**, детерминированные deferred promises для гонок;
`npm ci --no-audit --no-fund` и `npm run build` успешны. Build без TS/ESLint
ошибок; предупреждения только об устаревшей Browserslist/Baseline-базе.
`git diff --check` успешен. Зависимости/lockfile, модели, Alembic и timezone
редактора не менялись; Docker и браузерная QA не запускались.

Остаются orphan uploads после незавершённой формы, замены неиспользованной
загрузки или отложенного/ошибочного cleanup. Автоматического GC пока нет.
Будущая отдельная maintenance-команда: сначала dry-run, согласованный grace
period для свежих загрузок, только собственные файлы, exclusive inode lock
и повторная проверка отсутствия ссылок перед удалением. Legacy-файлы требуют
отдельного инвентаря/решения, массовая очистка в этом PR не выполняется.
Пагинация остаётся offset-based и не является snapshot при параллельных правках;
TZ-roundtrip админки остаётся PR-9, миграция дат — PR-8.

## PR-4 — фильтрация календарных дней (2026-11-13, исторический снимок до merge)

База: `origin/master` `2156f1b` (PR #19 merged); ветка
`fix/event-date-filters`. Реализация завершена, ожидает независимого review
и merge. SQLAlchemy-модели, Alembic и зависимости не менялись.

- `date`, `date_from`, `date_to`: строго ASCII `YYYY-MM-DD`; диапазон
  `[00:00 первого дня, 00:00 после последнего дня)`, включая микросекунды.
  Одна граница выбирает один день; границы имеют приоритет над `date`.
- `today`/`tomorrow`/`weekend` вычисляются от Asia/Novosibirsk. В воскресенье
  weekend — текущие суббота и воскресенье; в будни — ближайшие выходные.
  SQL-границы остаются naive, без UTC-конвертации: историческая семантика
  данных и переход на timestamptz остаются задачей PR-8.
- Неверный формат, несуществующая дата, пустой переданный параметр,
  неизвестный selector и обратный диапазон дают HTTP 400, даже с неизвестной
  категорией. Отсутствие параметров сохраняет нефильтрованный каталог.
  Первая допустимая дата — `0001-01-01`; последний включаемый день —
  `9999-12-30`. Для `9999-12-31` невозможно представить следующий день,
  поэтому возвращается 400 вместо переполнения/500.
- Проверки Python 3.11: полный `pytest -q` — **142 passed**, 108 deprecation
  warnings зависимостей; `compileall -q app alembic tests`, `git diff --check`
  успешны. 61 новый тест покрывает границы, TZ UTC/Новосибирск/Москва/Лос-Анджелес,
  категории, пагинацию, ошибки сервиса/API и реальные HTTP 200/400 через
  Uvicorn на временном loopback-порту. БД — только временная SQLite.
- Совместимость списка админки проверена по JSON-контракту и frontend-вызовам;
  frontend не изменялся, браузерная проверка и frontend build не запускались.
  Preflight по-прежнему не распознаёт `.git`-файл worktree; Git проверен напрямую.

## 1. Продуктовая цель

Веб-платформа бизнес-мероприятий Новосибирска: календарь и каталог,
поиск по теме/ЦА/дате, ожидаемая посещаемость, организаторы,
партнёрские заявки, рекламные размещения. Важное отличие от общей
афиши — ответ на вопросы «кому подходит мероприятие» и «с кем
можно познакомиться/договориться о партнёрстве».

Источники для исследования: собственное содержание организаторов,
публичные календари и сообщества («Харизма», «Мой бизнес» и др.).
Факта подключения этих каналов пока нет.

Документы: [PROJECT_PASSPORT.md](PROJECT_PASSPORT.md) и
[PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md).

## 2. Что уже было в старом репозитории

### Backend (реализовано в исходниках)
- `backend/app/main.py` — FastAPI app, CORS, статические файлы и роутеры.
- `backend/app/models/{user,category,event}.py` — SQLAlchemy модели.
- `backend/app/schemas/` — Pydantic-схемы.
- `backend/app/routers/{auth,categories,events}.py` — REST API.
- `backend/app/services/` — логика CRUD, загрузки изображений, фильтрации.
- `backend/app/auth/auth.py` — JWT bearer и проверка пароля.
- `backend/app/config.py` — настройки из окружения.
- `backend/alembic/` — добавленные базовые миграции.
- `backend/docker-compose.yml` и `backend/Dockerfile` — backend + PostgreSQL.

**Публичные API сейчас:** `GET /events/`, `GET /events/{id}`,
`GET /categories/`, `GET /health`. Админские API для событий,
категорий и загрузки изображений; `/auth/login`, `/auth/me`,
`/auth/register` (последний теперь доступен только администратору).

**Текущая Event-модель:** `id`, `title`, `description`,
`datetime`, `location`, `image_url`, `category_id`,
`creator_id`, `price`, `rating`, `discount`, `payment_url`.
Моделей организаторов, аудитории, партнёрских лидов и рекламных
кампаний **пока нет**.

### Frontend (реализовано в исходниках)
- `frontend/src/App.tsx` — React Router:
  `/`, `/admin/login`, `/admin`.
- `frontend/src/pages/HomePage.tsx` — главная, календарь/даты,
  подборки по категориям, баннер.
- `frontend/src/pages/AdminDashboard.tsx` — большая админка
  событий/категорий (требует разделения на модули).
- `frontend/src/components/` — `EventCard`, `EventModal`,
  `EventFilters`, `DateScroller`, `CalendarGrid`,
  `ThisWeekSection`, `YandexAdBanner` и др.
- `frontend/src/services/api.ts` — Axios + типы.
- `frontend/src/config/api.ts` — **жёсткий production API origin**.

**Ключевой долг:** публичная страница события пока не является
отдельным маршрутом, детали открываются в модальном окне.
Нужна URL/SEO-стратегия до переработки публичного интерфейса.

## 3. Что изменилось при восстановлении в master

Подтверждено чтением дерева и коммитов GitHub:

1. Создана `master` от исторической `main` и сделана default branch.
2. `backend/app/config.py`: обязательные `SECRET_KEY` (мин. 32 символа)
   и `ADMIN_PASSWORD` (мин. 12 символов), валидация заглушек.
3. `backend/app/routers/auth.py`: `POST /auth/register` требует
   админские права; публичного self-signup пока нет.
4. `backend/create_admin.py`: админ создаётся идемпотентно;
   пароль не выводится; события не создаются автоматически.
5. `backend/app/main.py`: удалены `create_all` и `ensure_columns`
   при импорте приложения.
6. `backend/alembic/versions/0001_initial.py`: миграция для **пустой**
   БД; старые таблицы вызывают отказ вместо неявного изменения.
7. `backend/start.py`, `run_local.py`, `start_all.py`:
   обновлён безопасный старт; требуется .env с секретами.
8. `backend/docker-compose.yml`: явные секреты, healthcheck БД,
   миграции перед запуском, порты PostgreSQL/API на loopback.
9. `backend/tests/`, `backend/conftest.py`,
   `backend/requirements-dev.txt` и `.github/workflows/backend-ci.yml`:
   тесты миграций и базовой авторизации, GitHub Actions.
10. `frontend/src/pages/HomePage.tsx`: выбранная дата теперь
    передаётся в `eventsApi.getAll`; **браузерный тест не выполнялся**.
11. `backend/alembic.ini`: исправлено экранирование `%04d` в
    `version_num_format`, снята ошибка CI.
12. Добавлена документация по миграциям и безопасному запуску.

**CI:** GitHub Actions backend `success` для коммита `5fe7cf6`:
https://github.com/Alexon-Git/Afisha/actions/runs/43194330396
(предыдущий запуск падал с Alembic `InterpolationSyntaxError`).

Наличие green CI **не значит**, что проект проверен в Docker,
PostgreSQL production, мобильных браузерах или под нагрузкой.

## 4. Критические и существенные незакрытые задачи

### P0 — до публичного запуска
- Проверка содержимого загрузки изображений реализована и локально
  протестирована в `fix/image-upload-validation`; пока не включена в `master`.
  Подробности и ограничения — раздел 9.
- Добавить rate limiting и журналирование попыток входа,
  проверить JWT lifecycle и меры против перебора.
- Проверить `ProxyHeadersMiddleware(trusted_hosts="*")`;
  в production доверять только реальному reverse proxy.
- Подтвердить миграции для PostgreSQL в чистой БД и отработать
  процедуру переноса старой схемы на восстановленном бэкапе.
- Убедиться, что API и админка запускаются с новыми обязательными
  секретами; ротировать прежний реальный пароль вручную при необходимости.

### P1 — до наполнения каталога
- В `frontend/src/config/api.ts` захардкожен URL
  `https://afisha.lalexonl.ru`; сделать конфиг окружения и один origin
  при reverse proxy.
- Проверить работу фильтров и тесты date-range.
  `EventFilters.tsx` содержит локации Санкт-Петербурга, а в backend
  `list_events` нет location-фильтра.
- Добавить SEO-страницы событий. React SPA → SSR/Next.js
  **открытое архитектурное решение**, не проводить миграцию самовольно.
- Проверить frontend build, адаптивность, admin dashboard и
  состояние зависимостей (Create React App / старые пакеты).
- Добавить публикационные статусы и защиту от дублей.
- Рекламный `YandexAdBanner.tsx` сейчас статический placeholder
  с фиксированной внешней ссылкой, не рекламный кабинет.

### P2 — после запуска
- Личные кабинеты, подписки/Telegram, собственная билетная система,
  расширенный анализ поведения и другие города.

## 5. Локальная работа и проверки

```bash
# Разработка backend (из папки backend/)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp env.example .env
# заменить SECRET_KEY и ADMIN_PASSWORD на реальные локальные значения
python start.py

# Проверка backend
pytest -q

# Отдельный терминал, папка frontend/
npm ci
npm run build
npm start
```

Внимание: у frontend сейчас зафиксирован production origin,
поэтому для локального API требуется отдельная настройка.
Docker Compose живёт в `backend/` и не поднимает frontend.

**В GitHub проверены исходники и backend CI; запуск локального frontend,
PostgreSQL, браузерное QA и gstack пока не подтверждены.**

## 6. Инфраструктура

На дату снимка **сервер ещё выбирается**. Домены и конфигурации из
исторического проекта не считать актуальными без проверки.
Production `.env` и дампы БД сюда не сохранять.

При выборе хостинга: Linux, Docker Compose v2, PostgreSQL 17,
reverse proxy + HTTPS, постоянное хранилище изображений,
бэкапы с тестом восстановления, мониторинг и логи.
Настройка CI/CD для деплоя — отдельный этап.

## 7. Интеграция новых агентов

- Читать `AGENTS.md` в корне, затем паспорт, требования,
  роудмап и этот снимок; проверять свежий `git status`/CI.
- Работать в feature/fix ветке; перед merge выполнять тесты,
  сообщать точный результат.
- Не трогать production БД и не выполнять слепой `alembic stamp`.
- В конце обновлять этот файл только **фактами**, handoff
  и журнал архитектурных решений.
- Сторонний `gstack` изучен как возможный процесс ревью;
  **ни установка, ни прогон навыков gstack на Afisha не подтверждены**.

## 8. Следующее действие

После согласования и интеграции `fix/image-upload-validation` следующая
изолированная задача — защита `/auth/login` от перебора с регрессионными
тестами. Proxy trust остаётся отдельной P0-задачей.

См. [AGENT_HANDOFF.md](AGENT_HANDOFF.md).

## 9. 2026-11-12 — безопасная загрузка изображений

Источник: текущая рабочая ветка `fix/image-upload-validation` от `master`
(`affbd2e`), код `EventService.save_image` и результаты локального pytest.
Изменение подготовлено к PR в `master`; пользователь разрешил коммит, push
и открытие PR. Merge и деплой запрещены; задача не включена в `master`.

- Добавлена единственная новая runtime-зависимость `Pillow==13.0.0`.
- Формат определяется декодером, а не MIME/расширением запроса; разрешены
  только JPG, PNG и WebP. Проверяются структура и декодирование пикселей.
- Лимит входа и результата — 5 × 1024 × 1024 байт (равенство допустимо),
  чтение ограничено лимитом + 1 байт. До декодирования проверяется предел
  20 миллионов пикселей; анимированные PNG/WebP отклоняются.
- Изображение перекодируется в распознанный формат без исходных метаданных
  и добавленных данных. EXIF-ориентация применяется к пикселям до очистки.
  JPEG/WebP перекодируются с потерями; сохранение исходных байтов не обещается.
- Имя — случайный UUID4 с расширением `.jpg`, `.png` или `.webp`.
  Создание через `xb` исключает перезапись существующего файла.
- API сохраняет контракт `{image_url: ...}`, HTTP 400 при неверном файле
  и требование администраторского доступа. Роутер не изменён.

Проверки на Python 3.11.17 в `backend/.venv`:

- `cd backend && .venv/bin/python -m pytest -q` — **48 passed**, 9 предупреждений
  deprecation от существующих passlib/httpx; 42 теста загрузки изображений. Дополнительно проверены HTTP 400 для
  ошибок декодера Pillow и отсутствие вызова декодера при превышении 5 МиБ.
- `uv --no-cache pip check --python backend/.venv/bin/python` — все 43 пакета
  совместимы. `python -m pip check` недоступен: окружение uv не содержит pip.
- `git diff --check` — успешно.

Тесты используют временные каталоги и тестовые SQLite-БД, без production.
Frontend, Docker/PostgreSQL и браузер не запускались. Ограничение размера
проверяется сервисом после multipart-разбора: лимиты HTTP body на proxy/ASGI
и обновление существующих multipart-зависимостей остаются отдельной работой.
Старые файлы uploads не проверялись и не переписывались.

Среда: backend-зависимости установлены через uv; frontend-зависимости и `.env`
не создавались. Личный gstack 1.99.2.0 установлен ранее, runtime найден
preflight; gstack-проверки на Afisha не запускались. Старые отметки выше о
неподтверждённой установке отражают состояние исходного GitHub-снимка.

## 10. 2026-11-12 — предпроектный аудит и план MVP (документация)

Источник: ветка `audit/predevelopment-review`, чтение кода и Git; код не менялся.
Отчёты: `docs/audits/ENGINEERING_REVIEW.md`, `docs/audits/PRODUCT_REVIEW.md`.
План реализации: `TECHNICAL_PLAN.md` (корень репозитория, v2.1), критерии запуска:
`docs/RELEASE_CHECKLIST.md`, ближайший PR: `docs/PR1_AUTH_RATE_LIMITING_PLAN.md`.

- `master` = `666696e` (PR #16 включён поверх PR #15). Rate limiting логина (таблица
  `login_attempts`, миграция `0002`) и отказ от доверия proxy влиты в `master`
  (`b9cba12`, `138ca5e`), CI успешен. Stash `ff658e9` сохранён до отдельного решения
  об очистке. Настройка trusted proxy на production остаётся условием запуска.
- Event сейчас без `event_url`, организатора, источника, `verified_at` и статусов
  публикации; `datetime` без часового пояса.
- Frontend: CRA, API origin и CORS привязаны к `afisha.lalexonl.ru` (домен не утверждён).
  CRA и загрузки backend используют общий путь `/static`: при размещении админки
  в `/admin` нужна настройка `PUBLIC_URL`/`basename`.
- Не проверялось: PostgreSQL, Docker, сборка frontend, браузер, данные старой БД.

## 11. 2026-11-13 — PR-3: безопасность Docker и Compose

Источник: ветка `fix/docker-security` от актуального `origin/master`
`b4622f7` (PR #18 уже включён). Production, рабочие тома и stash не
затрагивались; проверки выполнены в отдельном Compose-проекте с отдельным
PostgreSQL volume, тестовыми credentials и uploads-каталогом.

- Новый `backend/.dockerignore` исключает `.env`, ключи, локальные БД и дампы,
  virtualenv/bytecode, uploads, кэши тестов, Graphify и локальные настройки Codex.
  Alembic, приложение, `requirements.txt` и `create_admin.py` остаются в образе.
- Backend-образ использует Python 3.11 slim-bookworm с зафиксированным digest,
  не устанавливает компилятор/curl/libpq-dev, запускается как non-root UID/GID,
  имеет healthcheck и сохраняет fail-closed цепочку
  `alembic upgrade head -> create_admin.py -> exec uvicorn --no-proxy-headers`.
- Compose не задаёт глобальные `container_name` и имя сети. Порты PostgreSQL и
  backend опубликованы только на `127.0.0.1`; backend имеет read-only rootfs,
  tmpfs `/tmp`, `cap_drop: ALL`, `no-new-privileges` и ограничение процессов.
- Имя существующего DB-volume по умолчанию остаётся `afisha_db_data`; для тестов
  и параллельных проектов добавлен `POSTGRES_VOLUME_NAME`. Uploads остаются в
  прежнем bind-пути, поэтому миграция пользовательских файлов не требуется.

Фактически выполнено:

- `docker compose config` с безопасным тестовым env — успешно; localhost-only
  bindings, отдельный DB-volume и read-only backend подтверждены.
- Backend image собран; canary `.env`/ключ/дамп/upload/Graphify/Codex-файлы не
  попали в filesystem, config, history или сохранённые слои образа.
- PostgreSQL 17: чистое применение `0001_initial`, затем
  `0001_initial -> 0002_login_attempts`; таблица `login_attempts` существует.
- Compose: 2/2 services healthy; `/health`, bootstrap и login администратора,
  upload PNG, сохранность файла и тестовой категории после force-recreate — OK.
- Runtime: backend non-root, rootfs read-only, capabilities dropped; Uvicorn
  завершился по stop-сигналу с exit 0. Поддельные `X-Forwarded-For` не разделили
  source-bucket: попытка 31 получила 429 и `Retry-After`.
- Полный backend pytest в временной актуальной venv: **81 passed**, 45 известных
  deprecation warnings; `compileall` и `git diff --check` успешны. Первая попытка
  в старой общей `.venv` дала 80 passed / 1 fail из-за отсутствия уже требуемого
  `python_multipart`; окружение проекта не изменялось.

Ограничения: проверена чистая PostgreSQL-БД, но не копия старой схемы/production.
Production trusted proxy остаётся PR-12/T8; до него сохраняется общий source-bucket
за Nginx. Значения runtime-секретов берутся только из неотслеживаемого env и не
встроены в образ, но оператор с полным доступом к Docker может видеть environment;
внешний secret manager/Docker secrets — отдельное production-решение. Preflight
ошибочно считает стандартный Git worktree «не Git checkout», потому что ожидает
каталог `.git`; скрипт в PR-3 не менялся.

Финальное review подтвердило: существующий `root:root 0755` uploads недоступен
для записи non-root UID до одноразовой подготовки ownership. Процедура без
перемещения/удаления данных добавлена в `backend/README.md`; на изолированном
volume checksum существующего файла сохранился, после `chown`/`chmod u+rwX`
запись от целевого UID успешна. Автоматический `chown` и дополнительные
capabilities контейнеру не добавлялись.
