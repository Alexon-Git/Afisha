# Передача контекста следующему агенту — Afisha

**Состояние на:** 2026-11-12  
**Репозиторий:** https://github.com/Alexon-Git/Afisha  
**Default branch:** `master`  
**Историческая база:** `main` (не удалять).

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


## Прочитать перед действиями

`AGENTS.md` → `docs/PROJECT_PASSPORT.md` →
`docs/PRODUCT_REQUIREMENTS.md` → `docs/ROADMAP.md` →
`docs/DEVELOPMENT_CONTEXT.md` → `docs/DECISIONS.md` →
`backend/MIGRATIONS.md`.

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

## PR #25 — повторное review category slug (2026-11-22)

- Ветка `feature/public-event-catalog-seo`: исправлена несовместимость category
  с backend slug (`_`, допустимые сочетания разделителей, длина до 150).
- Добавлены регрессии query/API и standalone-формы для `business_meetings`,
  негативные случаи URL/traversal/control chars/длины. Node 24.22.3: целевые
  2 passed, полный public suite 13 passed, typecheck/build/HTTP smoke успешны.
- Изменены только frontend parser, три тестовых файла и два документа контекста.
  Следующий шаг — повторное review PR #25. Merge/deploy не выполнялись.

## Передача PR-11 (2026-11-17)

- База `90b19db`, PR #24 merged, CI merge success. Ветка
  `feature/public-event-catalog-seo`, `.worktrees/afisha-pr11`.
- Public SSR `/`, `/events`, `/events/[id]` с реальными API, GET-фильтрами
  и серверной пагинацией. ID разрешён владельцем для MVP, будущий slug R11 открыт.
- Organizer summary только name, контакты исключены. Backend добавил стабильный
  порядок id при равных датах. Миграций и изменений timezone нет.
- Naive datetime показывается исходными компонентами с оговоркой. Aware явно
  форматируется в Asia/Novosibirsk. Главная выбирает календарные даты от сегодня,
  точность абсолютного будущего момента ждёт PR-8. Цена 0/NULL требует уточнения R7.
- Canonical/OG/Twitter/robots/sitemap, JSON-LD только для aware. Отсутствующий
  SITE_URL включает noindex и sitemap 503. Динамические страницы/no-store,
  sitemap целиком перечитывает API, 404 скрытым событиям, cancelled/postponed
  сохраняются без активного CTA регистрации. Детали и команды public/README.md.
- Проверено public ci/typecheck/11 tests ×3 TZ/build/standalone smoke,
  backend 384 passed/compileall, CRA 33 tests/build. Docker socket недоступен,
  защищённый runner отказал на config-only до создания контейнеров. Browser
  access host недоступен, mobile QA не подтверждена. Preflight имеет известную
  ошибку .git worktree, Git проверен отдельно.
- PR-8 BLOCKED и его worktree сохранён. Production SITE_URL/маршрутизация uploads
  и Nginx ждут владельца/PR-12. Merge/deploy не выполнялись.

## Передача PR-10 (2026-11-15, до merge)

- База master `88349e6`, PR #23 merged, CI merge success. Ветка
  `feature/public-nextjs-foundation`, worktree `.worktrees/afisha-pr10`.
- Добавлено отдельное `public/` (Next 16.4.6/React 19.3.1/TS 5.9.3), Node
  24.22.3 Docker standalone multi-stage/non-root. Инструкции и повторяемые
  smoke-команды: `public/README.md`. CRA остаётся админкой, FastAPI общим backend.
- Главная — нейтральный SSR-каркас со статусом FastAPI. Нет дат/событий/каталога.
  Server-only API: runtime INTERNAL_API_URL, Docker http://backend:8039.
  Browser API: build-time /api; без PR-12 reverse proxy этот путь ещё не работает.
  Ключи backend, JWT и доступ к БД публичному приложению не нужны.
- Compose opt-in: `backend/docker-compose.public.yml`, базовый Compose не менялся;
  существующий volume и uploads сохранены. Все ports localhost, security flags
  backend и --no-proxy-headers сохранены. Не выполнять down -v.
- Проверки: public npm ci/typecheck/6 API tests/build/standalone smoke;
  реальный Docker public→backend + PG17, outage, health, non-root/ports;
  canary отсутствует во всех image layers, internal URL отсутствует в browser JS.
  Production npm audit: 0. CRA 33 Jest tests/build, backend 86 publication tests.
  Тестовый stack/volume удалён; production данные не использовались.
- PR-8 BLOCKED, его локальная документация не переносилась. Не начинать PR-11:
  каталог/страницы/SEO/инвалидация позже. Production Nginx — PR-12, CI всех
  приложений — PR-13. Ни merge, ни deploy не выполнялись; browser QA нет.

## Передача PR-7 (2026-11-15, до merge)

- PR #21/#22 merged; база PR-7 `2ef5326`, CI master после merge success.
  Ветка `feature/event-publication-workflow`, `.worktrees/afisha-pr7`.
- Public events только published, draft/archive дают 404 и не входят в COUNT;
  cancelled/postponed опубликованные доступны. Admin GET `/admin/events/` и
  `/{id}` защищены реальным JWT/is_admin в БД, видят все состояния.
- Явный POST `/{id}/verify` под admin prefix ставит UTC. PATCH `/{id}/publication`
  и `/{id}/status` меняют независимые статусы. Неполная публикация → 422 с fields,
  без частичной записи. Общий POST/PUT не позволяет статусы/verified_at.
- Критичные title/datetime/location/organizer_id/event_url/source и event_status
  меняются через draft → правка → verify → published. Правка сбрасывает verify;
  опубликованные некритичные правки проверяют итоговые требования до mutation.
  Organizer требует name и designated public_contact; контакт не раскрывается.
- Event row locks PG / BEGIN IMMEDIATE SQLite + свежий identity-map state
  защищают от гонки «проверено → критичная правка → публикация со старым verify».
  Изображения сохраняют post-commit/flock гарантии. AdminDashboard читает новый
  endpoint; его пагинация, публичный HomePage и C2–C5 покрыты регрессиями.
- Итог: backend **383 passed**, React **13 passed**, production build,
  compileall/diff-check OK; PostgreSQL 17 concurrency test passed. Моделей,
  миграций и зависимостей не добавляли. Документация PR-6 ниже — старый снимок.
- Ограничения: verified_by/аудита нет в модели; static uploads остаются публичны
  даже у скрытой карточки. PR-8 — время; PR-9 — полный редакторский UI;
  PR-11 — уведомления об отмене, Next/SEO/sitemap. Прямые SQL-изменения вне API
  обходят workflow. Production/legacy-копия не проверена, браузер QA не запускался.
- Следующее действие: независимое review PR-7 и решение владельца. Merge/deploy
  и переход к PR-8 не выполнялись; stash, старые worktrees и локальные настройки
  сохранены. gstack/review не запускался.

## Передача PR-6 (2026-11-15, до merge/PR-7)

- PR #21 merged (`d4c5b23`), CI master после merge success (43658041385).
  PR-6 в `feature/event-organizers-and-statuses`, `.worktrees/afisha-pr6`.
- Добавлены Organizer, Event.organizer_id/event_url/source/verified_at и два
  независимых статуса (D-020/R6). Миграция 0003 от 0002; старые события draft,
  новые nullable сведения NULL. datetime и payment_url не конвертируются.
- Организатор не удаляет события: FK SET NULL + ORM-снятие связи.
  Контакт не включается в публичные ответы; Organizer CRUD/UI не добавлены.
- Общий POST/PUT принимает новые URL и organizer_id с валидацией, но отвергает
  verified_at/publication_status/event_status (422); автопроверки/публикации нет.
- **296 backend tests passed**, compileall/diff-check OK. SQLite и реальные
  HTTP API проверены; PostgreSQL 17.11 — изолированные миграционные проверки,
  сохранность старых данных, defaults/FK/CHECK, schema equivalence, ORM/сервис.
  Реальная legacy/production-копия не проверена. Frontend/dependencies не менялись.
- **Не выпускать PR-6 отдельно:** публичные draft пока видны. В PR-7 остаются
  переходы и права, видимость draft/archive, явный verified_at, проверка
  публикации/правок опубликованного, поведение отмен/переносов и публичный контакт.
  Downgrade удаляет новые данные; только после backup/отдельного плана.
- Следующее действие: независимое review PR-6 и решение владельца о merge.
  Merge/deploy и переход к PR-7 не выполнялись. Старые worktrees, stash ff658e9,
  AGENTS и локальные настройки не затронуты.

## Передача исправления C5 в PR #21 (2026-11-14, до merge)

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
