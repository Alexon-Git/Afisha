# Контекст разработки Afisha — технический снимок

**Дата сверки с GitHub:** 2026-11-12  
**Канонический репозиторий:** https://github.com/Alexon-Git/Afisha  
**Основная ветка:** `master` (`main` — исторический исходник)  
**Статус:** реанимация старой афиши → MVP бизнес-афиши Новосибирска.

> Этот документ описывает **проверенное состояние кода на дату снимка**
> и контекст предыдущих решений. Не подменяй им повторное чтение
> затрагиваемых файлов и текущего GitHub Actions.

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

- `master` = `2985b5e` (PR #15 включён). Rate limiting логина и отказ от доверия proxy
  существуют только в `stash@{0}` (`ff658e9`), ветка `fix/auth-rate-limiting` пуста.
- Event сейчас без `event_url`, организатора, источника, `verified_at` и статусов
  публикации; `datetime` без часового пояса.
- Frontend: CRA, API origin и CORS привязаны к `afisha.lalexonl.ru` (домен не утверждён).
  CRA и загрузки backend используют общий путь `/static`: при размещении админки
  в `/admin` нужна настройка `PUBLIC_URL`/`basename`.
- Не проверялось: PostgreSQL, Docker, сборка frontend, браузер, данные старой БД.
