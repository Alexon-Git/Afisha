# Контекст разработки Afisha — технический снимок

## PR-14A.2a — административная модерация импорта (2026-11-23)

- PR #30 merged: master `9e6135d934fb0b930633e6f9913f23fcb3fe81f8`,
  [merge CI 45123943836](https://github.com/Alexon-Git/Afisha/actions/runs/45123943836) success.
- Ветка feature/pr14-import-review-api. Только GET list/detail и POST approve/reject
  по `/admin/import/candidates`; реальный admin из БД, закрытые audit-поля,
  revision/status conflicts, row locks + conditional update, атомарный commit/rollback.
- Проверка source_id обоих first/last runs при каждом решении; без новой миграции.
  Это не DB-гарантия для будущего worker, его писателей нужно защитить отдельно.
- Approved требует разрешённого времени и явных решений по организатору/matches.
  Все повторы 409. Match acknowledgements сохраняются в reviewed_payload;
  CandidateMatch и Event не изменяются. Контракт: [IMPORT_REVIEW_API.md](IMPORT_REVIEW_API.md).
- Целевые SQLite/PG17: 104 passed, 4 SQLite-only concurrency skips.
  Полный backend (один прогон): 488 passed, 103 skipped, 398 warnings.
  Compileall и diff-check успешны; CI будет проверен на опубликованном HEAD.
- Схема, модели, UI, сеть/worker, link/promote, verified_at/публикация не меняются.
  Production/VPS/volumes не используются; merge/deploy запрещены в этой задаче.

## PR #30 — исправление P2 SQLite FK (2026-11-23, до повторного review)

- По независимому review исправлен только app.database: каждое SQLite-подключение
  стандартного engine включает foreign_keys=ON через connect listener.
  PostgreSQL, модели, миграция 0005, worker/API/UI не меняются.
- Регрессионный тест запускает стандартные engine/SessionLocal в отдельном процессе
  на мигрированной временной SQLite, без тестового PRAGMA listener. Проверяет два
  одновременных подключения и новое после dispose, ORM/SQL DELETE Event, SET NULL,
  lost_event_link и сохранение CandidateMatch/historical_event_id/reason_codes/score.
  До исправления тест падает; после — проходит.
- Целевой suite: 34 passed SQLite (с новой регрессией), 33 passed PostgreSQL17.
  Полный backend: 438 passed, 45 PG opt-in skipped, 344 warnings; побочных эффектов
  в прежних тестах нет. Compileall и diff-check успешны. CI проверяется на новом HEAD.
  Тестовый PostgreSQL остановлен; volumes/production/VPS не затрагивались.
- Соответствие source_id кандидата и его runs остаётся отдельной задачей до worker;
  в этом исправлении схема не расширяется. Merge/deploy не выполняются.


## PR-14A.1 — ядро хранения импорта (2026-11-23, до review/merge)

- По прямому поручению владельца реализован только слой схемы из локального
  `docs/plans/PR14_IMPORT_ARCHITECTURE.md` основной рабочей папки. Остальные части
  плана не разрешены этой задачей. База: origin/master
  `6b47007fe7a4b1bc442e6628ac3f01feac0bf12c`, PR #29 merged; merge CI
  [45117558497](https://github.com/Alexon-Git/Afisha/actions/runs/45117558497) success.
- Четыре модели в `backend/app/models/imports.py`, зарегистрированы в metadata;
  одна аддитивная миграция `0005_import_schema` от `0004_event_datetime_utc`.
  Старые модели/таблицы/данные Event и Organizer не меняются; seed нет.
- UUID запуска, строковые CHECK-статусы, FK/unique/индексы, частичный unique
  running/source, неотрицательные счётчики, положительные revisions,
  Numeric(18,4) цен, timestamptz/aware UTC, JSONB (SQLite JSON) до 16384 символов.
  `base_origin`/`base_path` хранят нормализованную идентичность источника;
  нормализация и проверка URL будут реализованы отдельно.
- Удаление Event: nullable FK SET NULL сохраняют кандидатов/matches и
  `historical_event_id` (писатель обязан передать snapshot event_id). Триггеры
  только на новых таблицах ставят отдельный флаг-предупреждение `lost_event_link`,
  не переписывая JSON и не рискуя превысить его размер при DELETE Event.
  Триггеры устанавливаются миграцией, не `metadata.create_all`.
- Только хранилище: здесь нет policy/SSRF/HTTP/парсеров, worker, API, UI,
  переходов review/revision, конвертации, автопубликации или реальных источников.
  Прямой SQL/ORM не считается авторизованным workflow; будущий сервис обязан
  проверять policy, revision, решения редактора и форму JSON. Поля VARCHAR
  ограничены PostgreSQL; SQLite не является доказательством проверок длины строк.
- Проверки: целевые import-schema **33 passed на PostgreSQL 17 + 33 passed
  на SQLite** (включая upgrade/repeat, сохранность всех прежних таблиц,
  metadata, FK/unique/CHECK, DELETE Event и отсутствие автопубликации).
  Единственный полный локальный backend-прогон: 433 passed, 45 skipped,
  4 проверки остановлены окружением (локальный порт/старая python-multipart).
  После временного подключения закреплённой python-multipart 0.0.33 и разрешения
  локального порта перепроверены только эти четыре — **4 passed**.
  Полного повторного локального прогона нет; полный suite и PG17 проверяет CI HEAD.
  Compileall и git diff --check успешны. Frontend локально не прогонялся: изменений нет.
- Downgrade удаляет импортную историю; на реальных данных требует отдельного
  backup/export и согласованного плана. Production/VPS/volumes не затронуты.


**Дата сверки с GitHub:** 2026-11-12  
**Канонический репозиторий:** https://github.com/Alexon-Git/Afisha  
**Основная ветка:** `master` (`main` — исторический исходник)  
**Статус:** реанимация старой афиши → MVP бизнес-афиши Новосибирска.

> Этот документ описывает **проверенное состояние кода на дату снимка**
> и контекст предыдущих решений. Не подменяй им повторное чтение
> затрагиваемых файлов и текущего GitHub Actions.

## PR-9 — админка: время и редакционный workflow (2026-11-23, до review/merge)

- База: актуальный origin/master `eba175325defe1e4a97466637c318664fb098180`;
  PR #28 merged, merge CI 45113752739 — success, все четыре jobs проверены.
  Отдельная ветка `fix/admin-event-timezone`, worktree `.worktrees/afisha-pr9`;
  прочие worktrees, локальные изменения и stash ff658e9 сохранены.
- `eventTime.ts` с date-fns-tz 3.2.0: datetime-local трактуется только в
  Asia/Novosibirsk. Пример 2026-11-23 18:00 → 11:00Z во всех TZ. Обратное
  отображение, исторический offset, границы UTC 1900–2100, неверные даты и
  неоднозначные/несуществующие местные часы покрыты тестами.
- Снимок формы и частичный PUT сохранены: без правок PUT нет; description-only
  не отправляет datetime; возвращённая к исходной дата не отправляется.
  Native input показывает до миллисекунд; неизменённые микросекунды API не
  переписываются, остаток сохраняется при смене даты без смены миллисекунд.
- В текущую форму добавлены organizer_id/event_url/source, статусы и явный verify;
  publication/status вызываются отдельно. Клиент не задаёт verified_at/статусы
  в обычном POST/PUT и не обходит 422 published edits. Несохранённые правки
  блокируют editorial actions; ошибки backend остаются видимыми в форме.
- Выявлен конкретный пробел: backend не имел списка организаторов. Добавлен
  только GET /admin/organizers/, реальный DB-admin, поля id/name без контактов;
  справочник доступен для выбора, управление/создание организаторов не добавлено.
  Публикация по-прежнему требует существующего организатора с публичным контактом.
- Полный frontend Jest: **75 passed в каждом из четырёх TZ** (UTC, Новосибирск,
  Москва, Лос-Анджелес), без моков преобразования времени. Production CRA build
  с PUBLIC_URL=/admin успешен. CI admin job теперь повторяет suite в четырёх TZ.
- Backend targeted publication/metadata: **160 passed**; полный pytest:
  **404 passed, 12 PG opt-in skipped, 344 warnings**. PG17-матрицу и gateway smoke
  проверяет unified CI нового PR; локальная PG/preview не запускались и не менялись.
  Compileall и diff --check успешны. Warnings — прежние deprecations зависимостей;
  frontend также предупреждает об устаревших Browserslist данных/React Router v7.
- Миграция 0004, публичный Next.js, production/VPS и Docker-ресурсы не менялись.
  Browser QA не выполнялась; Jest проверяет реальный datetime-local DOM, включая
  миллисекундное ограничение. Следующий шаг: independent review опубликованного
  PR и CI на точном head; merge/deploy автоматически не выполнять.

## PR-8 — исправление P2 диапазона datetime (2026-11-23)

- Причина: psycopg2 декодирует timestamptz в TZ сессии до UTCDateTime result hook;
  крайние годы Python могли переполниться уже после успешного commit.
- Общий as_utc (Pydantic EventInstant и ORM UTCDateTime) теперь проверяет UTC-момент
  в диапазоне 1900-01-01T00:00:00Z…2100-12-31T23:59:59.999999Z включительно до записи.
  Проверка offset сохранена; TimeZone PostgreSQL автоматически не меняется.
- Сначала обе границы проверены реальным PG17/psycopg2 в четырёх TZ — 8 passed.
  API/ORM регрессии: годы 1/9999, соседние микросекунды за границами, сами границы,
  обычная дата и эквивалентные offsets. После 422 POST нет строки; PUT не меняет
  ни дату, ни остальные поля; admin GET/list и последующие записи продолжают работать.
- Поисковые UTC-границы имеют отдельный DateTime bind: исключительная полночь
  после последнего допустимого дня не является записываемой датой мероприятия.
- Полный backend pytest с изолированной PG17 и SQLite/четырьмя TZ: **408 passed,
  344 warnings**. Целевые локальные проверки: 73 passed, 12 PG opt-in skipped.
  Compileall и diff --check успешны. Миграция 0004/UI/зависимости не менялись.
- Исправление публикуется отдельным коммитом в существующую ветку PR #28;
  GitHub Actions проверяются на новом head. Тестовая PG остановлена, данные и
  volumes сохранены; preview/production/VPS не затрагивались. Merge/deploy нет.

## PR-8 — готово к независимому review, до merge (2026-11-23)

- Владелец подтвердил новую пустую PostgreSQL17 и отсутствие старой БД Afisha
  с мероприятиями для сохранения: D-021, R10 снят для чистой БД.
- `fix/event-timezone-contract`, `.worktrees/afisha-pr8-current`, актуальная после
  fetch база origin/master `332f4eaa8e4f4c1d8070da76ee9d41e34938651b` (PR #27 merged,
  merge CI 45021827606 success). Старые worktrees/ветки и stash ff658e9 сохранены.
- Черновик активирован как 0004_event_datetime_utc от 0003: PG ACCESS EXCLUSIVE
  lock/5s timeout, отказ при любой строке, затем timestamptz. SQLite BEGIN IMMEDIATE,
  тот же empty guard и UTC ORM-кодирование. Downgrade/offline upgrade запрещены.
- API datetime только ISO с явным offset, нормализация UTC/Z; naive/date-only/
  numeric epoch → 422. UTCDateTime не допускает naive ORM writes, восстанавливает
  UTC из SQLite и нормализует PostgreSQL независимо от session TZ.
- Фильтры date/today/tomorrow/weekend/date_from/date_to: местные дни Новосибирска,
  UTC-полуоткрытые границы. Непредставимые UTC-границы → 400. Publication/visibility,
  critical edits и verify остаются прежними; одинаковые моменты с разными offset равны.
- Изолированная PostgreSQL17 + полный backend pytest в Linux image: **400 passed,
  336 warnings**, включая 16 time-contract/migration случаев SQLite/PG × четыре TZ.
  UTC, Asia/Novosibirsk, Europe/Moscow, America/Los_Angeles проверены для процесса,
  PG-сессии, CRUD/публикации/статусов/фильтров/сортировки и guard непустой таблицы.
  Первое локальное выполнение выявило старое сравнение строк вместо instant;
  оно исправлено. Compileall/new-file whitespace/git diff --check успешны.
- CI backend job дополнен отдельной PG17 service и PostgreSQL-матрицей на каждом PR.
  Gateway smoke fixture теперь передаёт +07:00. UI/зависимости не менялись;
  Next/CRA/gateway проверки выполняет unified CI на публикуемом head.
- PR-9 остаётся отдельным: datetime-local формы ещё зависит от TZ браузера.
  Это не исправляется неявным приписыванием зоны API. PR-14 не реализовывался.
- Test PG остановлена, БД/схемы/container/network/volume сохранены. Preview
  http://127.0.0.1:58080 не менялся. Production/сервер Харизмы не подключались,
  merge/deploy не выполнялись. Текущий GitHub CI проверять на head PR, не на базе.

## PR-8 — аудит данных, контракт ещё не внедрён (2026-11-22)

- PR #27 merged: база `332f4eaa8e4f4c1d8070da76ee9d41e34938651b`,
  [merge CI 45021827606](https://github.com/Alexon-Git/Afisha/actions/runs/45021827606)
  success, все четыре jobs. Работа в `fix/event-timezone-contract`,
  `.worktrees/afisha-pr8-current`; старый отсутствующий на диске worktree PR-8,
  его metadata/ветка и stash ff658e9 не изменены.
- Read-only аудит доступной локальной preview-БД: events=0,
  datetime=`timestamp without time zone`, head=`0003_event_metadata`,
  session TZ=Etc/UTC. Файловых БД/дампов в доступном дереве не найдено.
  Production не проверялась. Это не подтверждение отсутствия иной старой БД.
- **P0 / BLOCKED:** нужен ответ владельца: запуск только с пустой БД или
  сохранение исторических данных вне preview? Для исторических строк нет
  разрешённой копии и подтверждённой исходной зоны; автоматическая конвертация
  не выполнялась. Не утверждается, что такие строки обнаружены.
- Отдельный неактивный `backend/migration_drafts/0004_event_datetime_utc.py`
  отказывает при непустой events; не входит в Alembic versions. Проверен на
  изолированной PG17: 8 passed (empty/nonempty × UTC/Новосибирск/Москва/LA),
  сохранение пользователей/категорий/индекса и aware-момента, отказ downgrade.
- Полный backend pytest: 381 passed; 3 loopback-сценария получили sandbox
  PermissionError. Только эти 3 повторены с разрешённым bind: 3 passed.
  Это тесты существующего контракта, не нового API. Новые фильтры/aware API
  ещё не реализованы; frontend/gateway повторно не собирались.
- Compileall и git diff --check успешны. Подробности и план продолжения:
  [PR8_TIME_DATA_AUDIT.md](audits/PR8_TIME_DATA_AUDIT.md).
- Новая тестовая PG остановлена; БД/volume/container/network сохранены,
  manifest `/private/tmp/afisha-pr8-audit-g16_gp96/resources.json`.
  Прежний preview http://127.0.0.1:58080 сохранён. Модели, API, frontend,
  активные миграции не менялись; commit/push/готовый PR/deploy не выполнялись.

## PR-13 — исправление независимого review (2026-11-22)

- Все 8 вызовов GitHub Actions в `.github/workflows/backend-ci.yml` закреплены
  полными commit SHA вместо изменяемых major-тегов. Выбраны те же версии
  checkout/setup-node/setup-python, которые исполнялись в успешном CI
  45019004362 для head `2031c9320fe4e5e057118cfd937ebc942118c5c4`;
  принадлежность SHA официальным репозиториям Actions проверена через GitHub.
- Локально: YAML разобран, все uses проверены на полный SHA, сохранение
  семантики workflow после нормализации refs и `git diff --check` проверены.
  Preflight по-прежнему не распознаёт `.git`-файл worktree; ветка и статус
  проверены средствами Git. Новый CI нужно проверить после push в PR #27.
- Merge/deploy не выполнялись; VPS и Docker-ресурсы не затрагивались.

## PR-13 — общий CI и диагностика staging (2026-11-22, до review)

- Изолированная ветка `feature/unified-ci-smoke`, `.worktrees/afisha-pr13`,
  база master `38ae10e`; PR #26 merged, master backend CI 45017002695 success.
- Общий workflow в прежнем backend-ci.yml без path filters: backend-tests,
  admin-tests (PUBLIC_URL=/admin), public-tests (typecheck/unit/build/HTTP smoke),
  затем gateway-smoke (сборка FastAPI/Next/Nginx+CRA и новая PG17).
  Python 3.11, Node 24.22.3, Ubuntu 24.04; read-only GitHub permissions,
  timeouts/concurrency; secrets, push images и deploy отсутствуют.
- Smoke runners поддерживают проверенный local context default на Linux,
  desktop-linux на macOS. Чужие DOCKER_HOST/CONTEXT и данные не наследуются.
  Регрессии проверяют оба Unix sockets и отказ remote context.
- Локально: backend pytest 384 passed (328 warnings); CRA 36 passed и CI build;
  public 13 passed, typecheck/build/standalone HTTP smoke success; 10 PR-10
  isolation tests passed. Gateway suite: 5 passed, 1 безопасно BLOCKED —
  подсеть 172.30.123.0/29 занята существующим локальным preview project.
  Полный gateway smoke не запускался после отказа config-only; preview сохранён.
  Linux CI 45018323444 для code head `8ff7a0e` success: все 4 jobs;
  10+6 isolation tests, полный gateway smoke и scoped cleanup passed.
  Draft PR #27: https://github.com/Alexon-Git/Afisha/pull/27;
  независимое review ещё не выполнено.
- Известный preflight не распознаёт .git-file worktree; Git проверен отдельно.
  Python syntax (deploy/public test runners) и git diff --check успешны.
- VPS проверен по SSH только read-only: 9 running, 2 stopped другого проекта,
  свободно 2 GiB; RAM 957 MiB/available ~384 MiB, swap 845 MiB/1 GiB.
  Images/volumes все referenced, build cache shared/private 316.8 MB/0 B.
  Journal 216 MB, APT cache ~176 MiB; backups обеих баз есть за 21.11
  (содержимое и restore сейчас не проверялись). Затем владелец явно разрешил
  APT clean и vacuum архивных journal старше 7 суток: выполнены только эти
  операции. Journal 216→56 MiB, APT cache ~176 MiB→20 KiB, по df свободно
  2,057,203,712→2,409,365,504 bytes (+335.85 MiB), занято 80→76%.
  Все 9 рабочих containers сохранены, DB/Redis healthy; images 7, volumes 8,
  размеры backup-каталогов не изменились. Перезапусков/deploy не было.
- `deploy/STAGING_PLAN.md`: границы согласуемой очистки, нехватка ресурсов,
  сборка вне VPS, отдельные DB/uploads/networks, Caddy ingress и rollback.
  Caddy находится в двух сетях ботов; новый proxy-hop требует отдельной
  exact-IP/scheme/rate-limit проверки. Production config не менялся.
- Локальный preview, существовавший до задачи, сохранён: http://127.0.0.1:58080.
  GET /api/health, /, /events, /admin/login — 200. Визуальная/browser QA
  не выполнялась; это не новый deploy ветки PR-13.
- PR-8 BLOCKED, PR-9 не готов. Следующий шаг — независимое review PR #27;
  без merge/deploy. Дальнейшая очистка VPS требует нового согласования.


## PR-12 — единый локальный Nginx gateway (2026-11-22, до merge)

- Работа продолжена в существующем `.worktrees/afisha-pr12`, ветка
  `feature/unified-nginx-routing`, база `7aa62117043b680f7160e4313381bf9621ffff21`.
  PR #25 merged; merge CI 44993369781 success. Старые worktrees/stash сохранены.
- Nginx `/`/events/robots/sitemap → Next, `/admin` → CRA (basename и PUBLIC_URL),
  `/api` → FastAPI со снятием префикса, uploads → общий read-only mount.
  CRA использует same-origin /api, старый публичный route и demo credentials
  убраны из UI. JWT storage и backend business code/модели/миграции не менялись.
- Новый Nginx image: pinned Node/Nginx, non-root/read-only/cap_drop ALL,
  все temp dirs в /tmp. API/admin HTML no-store, assets immutable, body 6 МиБ.
  Docker context не включает env, node_modules, build и локальные настройки.
- Base Compose и afisha_db_data не менялись. Gateway и trusted-proxy — opt-in
  overlays. Nginx имеет один точный доверенный IPv4 в отдельной internal сети;
  launcher отвергает wildcard/subnet. Nginx заменяет XFF на remote_addr,
  очищает Forwarded/X-Real-IP и альтернативные forwarded host/port.
  Без trusted overlay base остаётся --no-proxy-headers с общим source bucket.
- До прерывания: CRA npm ci, 36 Jest tests и PUBLIC_URL=/admin build; public
  npm ci, typecheck, 13 tests, build и standalone smoke успешны. Повторно эти
  длительные проверки не запускались: соответствующие исходники не менялись.
- Финальный gateway smoke: PostgreSQL 17 с чистыми миграциями 0001–0003,
  nginx -t, health, SSR/catalog/detail/hidden 404, Next/CRA JS/CSS, refresh login,
  login/me/CRUD/categories/upload/verify/status/publication через /api, query и
  slash redirects, реальные PNG и body 413, no-store и отсутствие старого API
  домена в CRA bundle. Пустой SITE_URL: noindex и sitemap 503 ожидаемы.
- Spoofed XFF/Forwarded/X-Real-IP не меняют bucket: клиент .5 получает 429 с
  Retry-After после 3 отказов, .6 сохраняет 401. Peer public .4 при прямом
  обращении к backend .3 с поддельными заголовками также получает 429.
  Это проверяет точный IP, включая отказ доверять другому пиру того же subnet.
- Runner расширяет исходный PR-10 без его изменения: clean env, pin local Unix
  socket, frozen validated JSON, новые credentials/project/volume/uploads,
  проверка коллизий/subnet до build/up. Isolation tests: 5 новых + 10 прежних
  passed. Фактические port bindings всех сервисов только 127.0.0.1; GET gateway
  с хоста проходит, TCP к backend/DB через физический LAN IP отвергается.
  Для host publishing Nginx имеет отдельную ingress-сеть; связь с backend
  остаётся через internal gateway и точный IP. Удалённый скан production
  не выполнялся. Тестовые containers/networks/volume
  удалены, images оставлены. Production/существующая БД не использовались.
- Browser host недоступен: браузерная/mobile QA не подтверждена; login/logout
  проверены Jest, маршруты и assets — HTTP. Backend pytest локально не повторялся:
  backend код не менялся, реальные API проверены smoke; CI проверяется на head PR.
- **Production BLOCKED:** владелец должен утвердить домен/SITE_URL, HTTPS certificate
  и допзащиту admin/login по D-011. TLS template и policy examples не активны,
  production include отсутствует до явной подготовки. Права реального uploads,
  firewall и фактические proxy IP на сервере требуют отдельной проверки.
  PR-8 остаётся BLOCKED, PR-9 UI/TZ и PR-13 CI не выполнялись. Инструкции и
  команды: `deploy/README.md`. Следующий шаг — независимое review, без merge/deploy.

## PR #25 — исправление category slug (2026-11-22)

- В `feature/public-event-catalog-seo` frontend-валидация category согласована
  с backend: непустой slug из `[a-z0-9_-]`, максимум 150 символов по колонке БД.
  Существующие slug не изменяются; URL, traversal, управляющие символы,
  повторные параметры и превышение длины отклоняются.
- Node 24.22.3: два целевых теста и полный public suite (**13 passed**),
  typecheck, production build, standalone SSR/HTTP smoke успешны. Smoke проверяет
  наличие и выбор `business_meetings` в форме и передачу category в GET `/events/`.
  Backend/БД не менялись, backend pytest не повторялся. Ожидает повторного review.

## PR-11 — публичный каталог и SEO (2026-11-17)

- База master `90b19db`, PR #24 merged, merge CI 44025620978 success.
  Ветка `feature/public-event-catalog-seo`, отдельный `.worktrees/afisha-pr11`.
- Реализованы `/`, `/events`, `/events/[id]`, серверные фильтры date/range/category,
  sort и пагинация с query в URL. Числовой ID выбран владельцем для PR-11, R11
  о slug остаётся открытым. Все данные читаются из публичных API.
- EventSchema возвращает organizer только с name, GET/list eager-load связь,
  сортировка при равных датах стабильна по id. Тест подтверждает отсутствие контакта.
  CRA получил необязательное поле типа. БД/миграции не изменялись.
- Naive-компоненты выводятся без преобразования зоны. Aware-путь явно использует
  Asia/Novosibirsk. Главная выбирает ближайшие календарные даты от сегодняшнего
  дня по существующему контракту фильтров. Точная классификация будущего момента
  для legacy-данных зависит от PR-8. Цена 0/NULL показана как требующая уточнения.
- Dynamic SSR/no-store и request-scoped React cache. Draft/archived/missing ID
  дают HTTP 404. Cancelled/postponed доступны с уведомлением и без CTA регистрации.
  Безопасные event_url/source и локальные UUID uploads, fallback изображений,
  plain-text описание и экранированный JSON-LD. Схема Event только при aware date.
- Canonical/OG/Twitter, robots/sitemap зависят от строгого runtime SITE_URL.
  Без origin — noindex/nofollow, robots disallow, sitemap 503. Sitemap обходит
  все API-страницы до 499×100 событий, при ошибках/изменении total_pages — 503.
  Старые списки не кешируются. Production origin не утверждён.
- Проверено npm ci/typecheck/build, 11 public tests в трёх TZ, standalone HTTP
  smoke с >100 fixture events, 404, SEO, XSS и publication changes. Backend
  384 passed/compileall, CRA 33 tests/build. Docker config-only безопасно отказал
  из-за отсутствующего socket. Контейнеры не создавались. Browser access host
  недоступен, mobile/desktop browser QA остаётся неподтверждённой.
- Preflight запущен и отверг .git-файл worktree, Git принадлежность проверена.
  PR-8 worktree/документы не затрагивались, задача остаётся BLOCKED. Инструкции
  и ограничения в public/README.md. Состояние подготовлено к review, без merge/deploy.

## PR-10 — отдельный публичный Next.js foundation (2026-11-15, до merge)

- База `88349e6`: PR #23 merged, CI master 43731712143 success.
  Отдельная ветка `feature/public-nextjs-foundation`, `.worktrees/afisha-pr10`.
- `public/`: Next.js 16.4.6 App Router, React 19.3.1, TS 5.9.3, CSS;
  Node 24.22.3 в .nvmrc/Docker (base image pinned digest), отдельный lockfile.
  Главная Server Component показывает состояние связи с API; layout, базовые
  metadata, 404, безопасный error fallback, собственный `/health`.
- Server-only клиент использует runtime INTERNAL_API_URL (`http://backend:8039`
  в Docker); отдельный browser client — build-time NEXT_PUBLIC_API_BASE=/api.
  Нет прокси/rewrite, admin JWT, DB credentials или обращений к admin/events.
  Fetch без кеша/credentials/redirects, таймаут 5 секунд; URL/ошибки транспорта
  не попадают посетителю. Типы соответствуют фактическим FastAPI-схемам.
- `backend/docker-compose.public.yml` — opt-in расширение. Базовый Compose,
  volume PostgreSQL, uploads и --no-proxy-headers не изменены. Public non-root,
  read-only/cap-drop/no-new-privileges, localhost:3001; внутренняя общая сеть.
- Проверено: npm ci, typecheck, 6 API tests, production build, standalone
  smoke (home/health/static JS/404/API outage/bundle isolation). Изолированная
  связка public + backend + PostgreSQL 17: healthy, DNS backend:8039, публичный
  GET events, safe outage, localhost порты и отсутствие DB credentials в public.
  Отдельный image-layer .env-canary smoke успешен, production npm audit: 0.
  Размер arm64 образа около 75 MB. CRA: 33 Jest tests/build; backend: 86
  целевых publication tests, 88 dependency warnings. Полный backend suite не повторялся.
- Тестовые Compose контейнеры/сеть/уникальный volume удалены, рабочие данные
  не использовались. Скрипты проверок и инструкции — `public/README.md`.
  Preflight запущен, но не распознаёт .git-файл worktree; Git проверен отдельно.
- PR-8 остаётся BLOCKED; datetime не изменяется и не показывается. Нет каталога,
  event routes, SEO Event/OG/sitemap/robots/ISR (PR-11), Nginx/CRA routing (PR-12)
  и общего CI (PR-13). Политика id/slug R11 не выбиралась. Реального production
  deploy и browser QA нет. Старый frontend/backend и PR-8 worktree не менялись.

## PR-7 — публикация и административное чтение (2026-11-15, до merge)

База `origin/master` — `2ef5326`, PR #22 merged, CI merge success (43659473620).
Ветка `feature/event-publication-workflow`, отдельный `.worktrees/afisha-pr7`;
реализация подготовлена к review, merge/deploy не выполнялись.

- Публичные GET `/events/` и `/events/{id}` видят только published. Draft/archive
  по ID дают одинаковый 404 с несуществующим ID. Фильтр включён в общий WHERE
  до OFFSET/LIMIT/COUNT; cancelled/postponed published остаются доступны.
  Query-параметров обхода видимости нет, токен admin не расширяет публичную выдачу.
- GET `/admin/events/` и `/{id}` требуют действительного JWT пользователя с
  is_admin в БД, возвращают все статусы с прежней пагинацией/фильтрами. Админка
  использует getAdminAll; публичный getAll и HomePage не менялись.
- POST `/admin/events/{id}/verify` ставит серверный UTC verified_at; клиентский
  timestamp не используется. Повторный вызов обновляет его. В модели нет
  verified_by/истории проверок, поэтому аудит проверяющего не заявляется.
  SQLite naive представление именно verified_at сериализуется как UTC;
  это не утверждение о зоне старого Event.datetime и не его преобразование.
- PATCH `/admin/events/{id}/publication` принимает publication_status;
  `/status` — event_status. Обычные POST/PUT по-прежнему отвергают эти поля
  и verified_at. Переход в published требует непустых title/location,
  datetime, существующего Organizer с name и непустым designated public_contact,
  безопасных event_url/source и явного verified_at. Online URL отдельным полем
  в модели не предусмотрен: location остаётся обязательной строкой.
  Контакт организатора всё ещё не выдаётся автоматически публично.
- Критичные поля: title, datetime, location, organizer_id, event_url, source.
  Их фактическое изменение у published отклоняется целиком с 422 и перечнем
  полей. Безопасный путь: draft → правка (сбрасывает verified_at) → verify →
  published. Изменение event_status использует такой же путь. Неизменившиеся
  значения и некритичные правки не сбрасывают проверку, но любое изменение
  published проходит проверку итогового обязательного минимума до ORM mutation.
  Автоматического TTL verified_at нет: срок проверки владельцем не утверждён.
- Мутации одного события сериализуются FOR UPDATE на PostgreSQL с перечитыванием
  identity map; SQLite резервирует BEGIN IMMEDIATE до чтения состояния.
  Organizer при публикации удерживается FOR SHARE до commit. Post-commit
  cleanup изображений, их нормализация/ссылки/flock остаются общими для всех статусов.
- Проверки: полный backend **383 passed**, 327 dependency warnings; **87**
  целевых HTTP/транзакционных тестов публикации; реальная PostgreSQL 17 гонка
  правки/публикации со stale ORM state — passed. SQLite гонка входит в suite.
  Использован отдельный Compose PostgreSQL 17.11; созданные контейнер/сеть/volume
  удалены после проверки, существующие данные не затрагивались.
  React/Jest **13 passed**, npm ci и production build успешны. Один сбой нового
  Axios mock (Jest resetMocks) исправлен в тесте; приложение собрано успешно.
  Compileall и diff-check успешны. Модели, миграции, зависимости и JWT не менялись.

Ограничения: naive Event.datetime остаётся PR-8; полноценный UI verify/status и
формы организаторов/метаданных — PR-9; видимые уведомления об отмене, sitemap,
SEO и Next.js — PR-11. Скрытый Event не делает его файл приватным: прямой
static/uploads URL может отвечать 200, что отдельно подтверждено HTTP-тестом.
Будущий Organizer CRUD должен учитывать опубликованные ссылки; прямые SQL-правки
в обход сервисов не являются защищённым редакторским workflow. Production-копия
данных и production routing не проверялись; браузерная QA не запускалась.

## PR-6 — организаторы, метаданные и R6 (2026-11-15, до PR-7)

База `origin/master` — `d4c5b23`, PR #21 merged; CI merge-коммита
43658041385 success. Ветка `feature/event-organizers-and-statuses`, отдельный
worktree `.worktrees/afisha-pr6`; реализация готова к review, не merged/deployed.

- Organizer: обязательное name, nullable description/website_url/public_contact,
  created_at/updated_at; связь один-ко-многим. Удаление организатора снимает
  organizer_id, не удаляя события (ORM и FK ON DELETE SET NULL).
- Event: nullable organizer_id с индексом/FK, event_url/source, verified_at;
  publication_status draft/published/archived, event_status
  scheduled/cancelled/postponed (D-020), default draft/scheduled.
  Проверки значений согласованы в Python и DB, без native PostgreSQL enum.
- API: старые запросы совместимы; новые ссылки только абсолютные http/https
  без credentials/whitespace/backslashes, organizer_id проверяется до записи
  (422 при ошибке; FOR KEY SHARE на PostgreSQL защищает назначаемую строку).
  Статусы и verified_at доступны только в ответах; передача любого из них
  через общий POST/PUT, даже null/default, отклоняется с 422.
  verified_at не выставляется/не обновляется автоматически. Контакт организатора
  не выдаётся публично; CRUD/каталог организаторов пока не добавлен.
- Alembic head: 0003_event_metadata. Новые поля nullable, статусы NOT NULL
  с безопасными server defaults; существующие записи draft/scheduled,
  verified_at NULL. Старые datetime/payment_url и остальные данные не меняются.
  SQLite использует batch recreation; PostgreSQL — аддитивный ALTER TABLE.
- Итог: Python 3.11, **296 passed**, 241 предупреждение зависимостей;
  compileall и diff-check успешны. Новый coverage: модели/HTTP/API protections,
  статусы/URL, сохранность записей и сравнение схемы с SQLAlchemy.
  Один обнаруженный сбой SQLite с выключенным FK устранён ORM-снятием связей;
  финальный полный прогон успешен. Frontend и зависимости не менялись,
  npm build не повторялся. Preflight всё ещё не распознаёт .git-файл worktree.
- PostgreSQL **17.11**: отдельный Compose-проект afisha_pr6_review_20261115,
  динамический localhost-порт, собственный volume и credentials. Три теста
  миграций проверили чистую установку, upgrade с 0002, defaults, сохранность
  users/categories/events/login_attempts, FK/CHECK и schema/model equivalence;
  ORM/сервис также проверены на реальной мигрированной PostgreSQL.
  Созданные тестовые контейнер, сеть и volume после проверки удалены;
  существующие volumes и данные не затрагивались.
  Копия production/старой неверсированной БД не предоставлена и не проверена.

**Release-блокер:** PR-6 нельзя отдельно выкатывать в production: публичный API
ещё возвращает draft для совместимости. PR-7 должен реализовать видимость,
права и переходы, проверку обязательных сведений при публикации/правках,
явную редакторскую проверку и поведение archived/cancelled/postponed.
PR-9 добавит UI организаторов/метаданных. Переход существующего datetime
в UTC/timestamptz остаётся PR-8; destructive downgrade 0003 описан в MIGRATIONS.

## PR #21 — исправление MAJOR в C5 (2026-11-14, до merge)

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
