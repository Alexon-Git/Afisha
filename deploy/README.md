# Единый локальный origin — PR-12

Nginx обслуживает Next.js, CRA и FastAPI по одному origin. Команды ниже
предназначены для локального окружения. Production остаётся BLOCKED до
утверждения домена, сертификата и дополнительной защиты админки по D-011.

| Путь | Обработчик |
| --- | --- |
| `/`, `/events`, `/events/{id}`, `/_next/*` | Next.js, сохранение upstream HTTP status/query |
| `/admin` | 308 на `/admin/` |
| `/admin/`, `/admin/login` | CRA index.html, SPA fallback |
| `/admin/static/*` | CRA JS/CSS из image, отсутствующие файлы дают 404 |
| `/api/*` | FastAPI со снятым `/api`; slash redirects сохраняют префикс |
| `/static/uploads/*` | read-only alias существующего uploads, jpg/jpeg/png/webp |
| `/robots.txt`, `/sitemap.xml` | Next.js, включая его noindex/503 при пустом SITE_URL |

CRA собирается с PUBLIC_URL=/admin, BrowserRouter basename=/admin, внутренние
routes `/` и `/login`. Login/logout/Navigate используют пути внутри basename,
глобальный 401 redirect ведёт на `/admin/login`. API base URL — `/api`, admin JWT
хранится существующим способом. Тестовые credentials из формы удалены.
Legacy HomePage сохранена в исходниках, публичным маршрутом служит Next.js.

## Локальное развёртывание

Подготовьте собственный backend/.env из env.compose.example, задав уникальные
локальные секреты. Не используйте рабочие production credentials или volume.
Из backend/ можно собрать локальный HTTP gateway

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.public.yml -f docker-compose.gateway.yml up --build
```

Откройте http://127.0.0.1:8080, админка доступна по /admin/login. Без trusted
overlay действует исходный --no-proxy-headers, клиенты Nginx делят source bucket.
Это состояние блокирует production-запуск. После проверки локальной сети
включение точного trusted IP производится явным четвёртым overlay

```bash
docker compose --env-file .env -f docker-compose.yml -f docker-compose.public.yml -f docker-compose.gateway.yml -f docker-compose.trusted-proxy.yml up --build
```

Nginx имеет адрес 172.30.123.2, backend 172.30.123.3, public 172.30.123.4
в отдельной internal сети 172.30.123.0/29. Nginx подключён к ней и отдельной ingress bridge-сети для host port publishing.
Internal-only контейнер Docker не публикует host ports; backend/public не входят
в ingress. Общая сеть Nginx/backend только gateway, поэтому DNS upstream backend
не выбирает другую интерфейсную сеть.
В Uvicorn разрешён **один IP Nginx**, не subnet и не wildcard. Launcher проверяет
значение TRUSTED_NGINX_IP через IPv4Address до запуска. NGINX_PROXY_IP,
BACKEND_GATEWAY_IP, PUBLIC_GATEWAY_IP и GATEWAY_SUBNET позволяют явно задать
другую схему, но она требует повторной проверки actual source IP и rate limiter.
Скрипт smoke проверяет именно приведённую выше фиксированную локальную схему.

Nginx перезаписывает X-Forwarded-For значением remote_addr, очищает Forwarded,
X-Real-IP и альтернативные forwarded host/port. X-Forwarded-Proto берётся из
реальной схемы запроса Nginx. Доверие CDN/дополнительным proxy не настроено.
API/HTML не кешируются, CRA fingerprinted static кешируется immutable,
uploads кешируется на час. Лог Nginx содержит метод/URI/status без query,
headers и body. Лимит body 6 МиБ допускает 5 МиБ изображения плюс multipart,
backend сохраняет собственную проверку 5 МиБ реального содержимого.

Base Compose, имя afisha_db_data и uploads source не переименовываются.
Nginx монтирует тот же UPLOADS_PATH только для чтения, backend продолжает запись.
Nginx работает как непривилегированный nginx user, rootfs read-only, temp в /tmp,
cap_drop ALL. Его image включает CRA multi-stage build, Next.js остаётся отдельно.
Все host ports локальной схемы привязаны к 127.0.0.1. Не используйте down -v.

Для существующего uploads перед развёртыванием проверьте доступ backend UID
к записи и Nginx UID к чтению/обходу каталогов. Файлы нужны читаемыми для nginx,
например через согласованную группу или ACL. Не применяйте массовый chmod/chown
к пользовательским данным автоматически. Сам mount read-only права не меняет.

## Воспроизводимые проверки

Из корня репозитория, при работающем разрешённом локальном Docker Desktop

```bash
python3 -m unittest discover -s deploy/tests -p test_gateway_isolation.py -v
python3 -m unittest discover -s public/tests -p test_compose_isolation.py -v
bash deploy/tests/gateway-smoke.sh --config-only
bash deploy/tests/gateway-smoke.sh
```

Gateway runner расширяет строгий PR-10 Smoke через отдельную конфигурацию.
Старый runner не меняется. Все Docker-команды используют очищенное окружение,
проверенный локальный Unix socket, затем pin через --host. Config JSON проверяется
до build/up, сохраняется с правами 0600 и используется далее. Уникальные project,
volume/uploads, точные DB URL/test secrets/IP/ports/network/build options проверяются.
Конфликтующие shell variables, remote DOCKER_HOST/CONTEXT игнорируются.
Существовавшие project/volume/network и пересечение subnet вызывают безопасный отказ.

Smoke создаёт только свою пустую PostgreSQL 17 и применяет существующие 0001–0003.
Проверяет nginx -t, home/catalog/detail/hidden 404, CRA прямой login/refresh и
JS/CSS, API login/me/categories/event CRUD/upload/verify/status/publication,
корректное PNG, 413, query/status/redirect, noindex robots/sitemap, localhost ports
и реальный GET к gateway с хоста. Попытки TCP к backend/PostgreSQL через LAN
адрес хоста должны завершаться отказом. На macOS выбираются физические en-интерфейсы
через ifconfig: адрес default route может принадлежать VPN/TUN и не доказывает LAN.
Два временных клиента с IP .5/.6 проверяют spoofed headers и независимые source
buckets. Public peer .4 обращается к backend .3 напрямую с поддельным XFF,
чтобы проверить отказ доверия другому пиру в том же subnet.

После ошибки up и успешного smoke cleanup удаляет только свой проект и свой
volume при совпадении имени/project label. Временные client containers имеют
уникальные имена/labels и удаляются отдельно с проверкой владения. Используются
--rm и точечный rm оставшегося своего клиента, без удаления чужих ресурсов.
Временные secrets/uploads убираются. Build images сохраняются для осмотра.
SIGKILL/отказ daemon может потребовать ручной проверки своих тестовых ресурсов.

## Production — требуется решение владельца

Локальный HTTP server afisha.conf и шаблон production.conf.template разделены.
Для production замените __APPROVED_DOMAIN__, __CERTIFICATE_PATH__, __PRIVATE_KEY_PATH__
реальными подтверждёнными значениями. Шаблон не загружается локальным image.
Получение сертификатов, DNS и публичное экспонирование в этой задаче не выполняются.

Production template требует отдельный production-routes.conf. Подготовьте его
из routes.conf, заменив все `/etc/nginx/afisha/admin-access.conf` на
`/etc/nginx/afisha/production-admin-access.conf`. Последний файл должен содержать
одобренную владельцем защиту. Оба production-файла отсутствуют в локальном image,
поэтому шаблон не стартует без явной подготовки. Есть fail-closed пример deny all
и неактивный пример Basic Auth без credentials. Выбор VPN/IP allowlist/Basic Auth/MFA
остаётся открытым. Для выбранного способа нужно проверить login и JWT API.

Утвердите HTTPS origin и задайте SITE_URL public. Пока SITE_URL пуст, действует
noindex, sitemap 503. Для реального deploy потребуется TLS/порты/проверка сертификата,
удаление прямого backend/DB publishing при необходимости и проверка всей actual
сети. Production readiness не подтверждена. PR-8 BLOCKED, PR-9 редактор/TZ,
PR-13 общий CI остаются отдельными задачами.
