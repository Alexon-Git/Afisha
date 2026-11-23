# PR-14 — полуавтоматический импорт

Реализация в `feature/pr14-complete-import`, до независимого review/merge.
Основа: master `1bf9e56` (PR #30/#31). Новая схема — 0006; 0005 не менялась.

## Запуск и границы

После `alembic upgrade head` отдельный процесс с тем же PostgreSQL 17:

```bash
cd backend
python -m app.imports.worker
```

SQLite поддерживает API/unit tests; production worker требует PostgreSQL.
API не запускает worker в фоне. Процесс запускается оператором отдельно от
Uvicorn под тем же non-root пользователем и с обычным окружением backend.
Пароли/токены/response body не пишутся в результаты или логи worker.
SIGTERM/SIGINT прекращают новые запросы; уже подтверждённые записи сохраняются.
Никакой автоматической публикации, изменения существующего Event или переноса
изображений/описаний/контактов с сайта нет. Статусы verify/publish — прежний workflow.

## Разрешение источника — обязанность оператора

Включённых источников и seed нет. Live-интеграция не проверена: подтверждённых
разрешений нет. Wize/bizafisha.ru и другие реальные площадки не опрашивались.
Настройка policy выполняется доверенным оператором БД через существующую ORM,
не через unrestricted API и не из импортируемого JSON-LD. До этого источник
остаётся `pending_review`/`manual_only`. Для разрешённого источника нужны:

- `adapter_key=jsonld_html`, `access_method=jsonld_html`, `state=enabled`;
- проверенные `terms_url`, `permission_basis`, несекретный `permission_reference`,
  `terms_checked_by` реального редактора, `terms_checked_at`, будущий `review_due_at`;
- точные `allowed_origins` (scheme/host/port), `allowed_path_prefixes`, без wildcard;
- `request_interval_seconds>=1`; при отзыве разрешения — paused/prohibited,
  изменение политики увеличивает `policy_version` и требует новой проверки.

Старые queued runs при другой policy_version блокируются. Каждое сетевое действие
и запись кандидата повторно проверяют разрешение; при отзыве во время HTTP
результат не записывается. API не позволяет менять policy, lease, audit или статус.
URL с credentials, потенциально секретными query-ключами и неоднозначными путями
отклоняются. Не храните signed URLs/секреты в source/run.

Robots загружается заново на каждом запуске защищённым transport, проверяется
для каждого URL/redirect. 404/пустой/неразобранный robots — отказ; режим
approved_absent/API exception этим универсальным HTML-адаптером не реализован.
Robots не заменяет право сбора. Учитываются Crawl-delay/Request-rate, более
строгие лимиты требуют ручной проверки. 403/429 и robots disallow приостанавливают
источник; обхода защиты, JS и каталожного crawler нет.

## API (все требуют реального admin из БД)

К backend-путям gateway добавляет `/api`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| GET | /admin/import/sources | Метаданные и состояние разрешений, page/limit<=100 |
| POST | /admin/import/runs | source_id, url; обязательный Idempotency-Key; 202 |
| GET | /admin/import/runs | Последние запуски и безопасные коды ошибок, page/limit |
| GET | /admin/import/runs/{uuid} | Счётчики, результат и record_errors |
| GET | /admin/import/candidates[/{id}] | Существующий список/детали |
| PATCH | /admin/import/candidates/{id} | Разрешённые факты + expected_revision; снимает approval |
| POST | /admin/import/candidates/{id}/recheck | Очередной run, Idempotency-Key |
| POST | /admin/import/candidates/{id}/approve | Явные решения по времени/организатору/matches |
| POST | /admin/import/candidates/{id}/reject | Причина отклонения |
| POST | /admin/import/candidates/{id}/promote | Approved revision -> атомарно draft + converted link |
| POST | /admin/import/candidates/{id}/link | Approved revision + event_id; Event не меняется |

Обычный повтор approve/reject по прежнему контракту — 409. Точный повтор
promote/link возвращает прежнюю связь; другая revision/цель — 409. Потерянная
связь после удаления Event не создаётся заново молча. Неопределённый результат
enqueue можно повторить с тем же ключом. Изменённый payload с тем же ключом — 409;
очередь ограничена 10 queued/running на источник (429 + Retry-After:60).

При promote повторно проверяются snapshot/fingerprint, source обоих runs,
дата/URL/обязательные поля, текущие совпадения. Новые/изменённые matches снимают
approval и требуют повторного review. `defer` запрещает создание нового draft;
для creation все текущие matches должны быть `not_a_duplicate`.
Создаётся только draft/scheduled, verified_at=NULL, image_url=NULL,
source=первоисточник, creator=редактор; observed/reviewed snapshots остаются
в кандидате. Цена переносится только как точный целый RUB или подтверждённый free.
Неполная/неоднозначная дата не получает неявный +07:00. Редактор уточняет ISO с offset.

## Очередь и дедупликация

Source row lock + `FOR UPDATE SKIP LOCKED` захватывают queued run, partial unique
index допускает один running/source. Lease UUID, heartbeat, expiry 45 секунд;
сетевые действия вне транзакций, ожидание rate limit продлевает lease каждые <=5с.
Перед записью каждой записи проверяется действующий token/expiry. Просроченный
worker не может зафиксировать результаты после нового lease. Падение между
записями сохраняет подтверждённые факты, следующая попытка идемпотентна.
Не более трёх попыток; временные сетевые ошибки повторяются с задержкой 30/60с,
прочие ошибки заканчивают run. Статусы interrupted/blocked/failed различаются.
Счётчики суммарные по попыткам; они не являются числом уникальных кандидатов.

Кандидат уникален по source + canonical URL + source_item_key. URL убирает fragment
и известные tracking-параметры; значимые query сохраняются. @id/URL дают стабильный
ключ; fallback title/start hash ограничен и может потребовать ручного сопоставления.
Повтор fingerprint обновляет только observation time/run. Новые факты увеличивают
revision, снимают approval; reviewed snapshot сохраняется. Linked/converted Event
не изменяется: новые наблюдения сохраняются отдельно и помечаются предупреждением.

Совпадения Event: нормализованный source/event URL, близость времени <=30 минут,
похожее название, Organizer как дополнительный сигнал. Предварительная выборка
ограничена 201 записью; превышение лимита блокирует создание без разбора.
Event.city отсутствует: город Event не выводится из location как доказанный факт.
Автоматического merge нет. Advisory transaction lock сериализует import writers
и editorial actions; обычное ручное создание Event этим lock не охвачено.
Глобальной гарантии отсутствия смысловых дублей с ручными записями нет.

## Сетевая граница

DNS проверяет все A/AAAA, запрещает non-global/private/loopback/link-local,
multicast/mapped IPv6/transition ranges. Подключение закреплено за проверенным IP,
TLS проверяет hostname/SNI, сверяется peer. Resolver ограничен четырьмя потоками
и 5с ожидания. Каждый redirect проходит policy/DNS заново; cross-origin и HTTPS
->HTTP запрещены, robots redirect не может запросить произвольную страницу.
Нет env proxies/cookies/auth/compression. Ответ <=1 МиБ, <=4 hops на получение,
<=8 запросов на fetcher/24 на run, socket timeout 8с, body deadline 20с.
JSON-LD ограничен глубиной/числом объектов, внешние @context/@id не загружаются.
Неподдерживаемые кодировки/сжатие/сложные страницы требуют отдельного адаптера.

## Проверки и ограничения

Автоматические fixtures покрывают путь enqueue -> worker -> candidate -> approve
-> promote/link, права, atomic rollback, revision, SSRF, redirects, DNS pinning,
конкурентные workers/conversion, crash/recovery и provenance на SQLite/PG17.
React проверяется через mock API; реальный browser QA остаётся отдельной проверкой.
Live разрешение, provisioning policy и эксплуатационный supervisor нужны до
включения реального источника. Независимое security review требуется до merge.
