#!/usr/bin/env bash
# Local smoke against a running staging stack. Reads secrets from .env.staging and GATE_PASS; never prints them.
# Usage: GATE_USER=tester GATE_PASS=... tests/staging-smoke.sh
set -uo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env.staging; set +a
B="http://127.0.0.1:$STAGING_PORT"; G=(-u "${GATE_USER:?}:${GATE_PASS:?}")
fail=0; RUN=$(date +%s)
chk() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1: got '$2' want '$3'"; fail=1; fi; }
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$@"; }
C() { docker compose --env-file .env.staging -f docker-compose.staging.yml "$@"; }

# gate
for p in / /events /blog /admin/login /api/health /static/uploads/x.png /robots.txt; do chk "no credentials 401 $p" "$(code $B$p)" 401; done
chk "wrong gate password" "$(code -u x:y $B/)" 401
chk "forged Bearer to /api/auth/login still gated" "$(code -X POST -H 'Authorization: Bearer x' $B/api/auth/login)" 401
# routes
for p in / /events /blog /admin/login /api/health /robots.txt; do chk "route $p" "$(code "${G[@]}" $B$p)" 200; done
chk "sitemap 503 without SITE_URL" "$(code "${G[@]}" $B/sitemap.xml)" 503
chk "404 page" "$(code "${G[@]}" $B/events/99999999)" 404
chk "blog unknown slug 404" "$(code "${G[@]}" $B/blog/nope)" 404
chk "robots disallow" "$(curl -s "${G[@]}" $B/robots.txt | tr -d '\r\n')" "User-Agent: *Disallow: /"
chk "X-Robots-Tag on page" "$(curl -sI "${G[@]}" $B/events | grep -ci 'x-robots-tag: noindex')" 1
chk "X-Robots-Tag on api" "$(curl -sI "${G[@]}" $B/api/health | grep -ci 'x-robots-tag: noindex')" 1
chk "meta noindex" "$(curl -s "${G[@]}" $B/events | grep -c 'name="robots" content="noindex')" 1
chk "no ad script" "$(curl -s "${G[@]}" $B/ | grep -c 'yandex.ru/ads')" 0
# login + Bearer through the gate
T=$(curl -s "${G[@]}" -d "username=$ADMIN_USERNAME&password=$ADMIN_PASSWORD" $B/api/auth/login | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])' 2>/dev/null)
chk "admin login" "$([ -n "$T" ] && echo ok)" ok
chk "Bearer API call without Basic" "$(code -H "Authorization: Bearer $T" $B/api/auth/me)" 200
chk "bad Bearer rejected by backend" "$(code -H 'Authorization: Bearer bad.token.x' $B/api/auth/me)" 401
# content + uploads
CAT=$(curl -s -H "Authorization: Bearer $T" -H 'Content-Type: application/json' -d "{\"name\":\"[ТЕСТ] Категория $RUN\",\"slug\":\"staging-$RUN\"}" $B/api/categories/ | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])' 2>/dev/null)
chk "create category" "$([ -n "$CAT" ] && echo ok)" ok
PNG=$(mktemp).png; python3 - "$PNG" <<'PY'
import sys, zlib, struct
def ch(t, d): c = struct.pack('>I', len(d)) + t + d; return c + struct.pack('>I', zlib.crc32(t + d))
raw = b''.join(b'\x00' + b'\x00\xff\x00' * 8 for _ in range(8))
open(sys.argv[1], 'wb').write(b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', 8, 8, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw)) + ch(b'IEND', b''))
PY
IMG=$(curl -s -H "Authorization: Bearer $T" -F "file=@$PNG;type=image/png" $B/api/events/upload-image | python3 -c 'import sys,json;print(json.load(sys.stdin)["image_url"])' 2>/dev/null)
chk "upload image" "$([ -n "$IMG" ] && echo ok)" ok
chk "uploaded file served via gate" "$(code "${G[@]}" $B$IMG)" 200
chk "uploaded file needs gate" "$(code $B$IMG)" 401
ORG=$(C exec -T db psql -U afisha -d afisha_staging -tAqc "INSERT INTO organizers (name, public_contact) VALUES ('[ТЕСТ] Организатор $RUN', 'test@example.invalid') RETURNING id" 2>/dev/null | head -1)
chk "create organizer (DB, own project)" "$([ -n "$ORG" ] && echo ok)" ok
EV=$(curl -s -H "Authorization: Bearer $T" -H 'Content-Type: application/json' -d "{\"title\":\"[ТЕСТ] Staging событие\",\"datetime\":\"2099-12-15T12:00:00+07:00\",\"location\":\"Тестовая площадка\",\"image_url\":\"$IMG\",\"category_id\":$CAT,\"organizer_id\":$ORG,\"event_url\":\"https://example.invalid/r\",\"source\":\"https://example.invalid/s\"}" $B/api/events/ | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])' 2>/dev/null)
chk "create event" "$([ -n "$EV" ] && echo ok)" ok
A="Authorization: Bearer $T"
curl -s -o /dev/null -X POST -H "$A" $B/api/admin/events/$EV/verify
chk "publish event" "$(code -X PATCH -H "$A" -H 'Content-Type: application/json' -d '{"publication_status":"published"}' $B/api/admin/events/$EV/publication)" 200
chk "event page SSR" "$(code "${G[@]}" $B/events/$EV)" 200
chk "event title in HTML" "$(curl -s "${G[@]}" $B/events/$EV | grep -c 'ТЕСТ')" 1
chk "event page noindex" "$(curl -s "${G[@]}" $B/events/$EV | grep -c 'name="robots" content="noindex')" 1
BODY=$(python3 -c "print('Текст тестовой статьи. '*40)")
AR=$(curl -s -H "$A" -H 'Content-Type: application/json' -d "{\"title\":\"[ТЕСТ] Статья\",\"slug\":\"staging-article-$RUN\",\"excerpt\":\"Тестовая статья staging\",\"seo_description\":\"Тестовая статья для проверки staging\",\"content\":\"$BODY\",\"category\":\"test\"}" $B/api/admin/articles/ | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])' 2>/dev/null)
chk "create article" "$([ -n "$AR" ] && echo ok)" ok
chk "publish article" "$(code -X POST -H "$A" $B/api/admin/articles/$AR/publish)" 200
chk "article page" "$(code "${G[@]}" $B/blog/staging-article-$RUN)" 200

# restart persistence (own project only; volumes kept)
C restart db backend public nginx >/dev/null 2>&1; sleep 25
chk "after restart: event page" "$(code "${G[@]}" $B/events/$EV)" 200
chk "after restart: article page" "$(code "${G[@]}" $B/blog/staging-article-$RUN)" 200
chk "after restart: upload" "$(code "${G[@]}" $B$IMG)" 200
# backend outage (own project only)
C stop backend >/dev/null 2>&1; sleep 3
S=$(code "${G[@]}" $B/api/health); chk "backend down: gateway answers 502/504 on API" "$([ "$S" = 502 ] || [ "$S" = 504 ] && echo ok)" ok
chk "backend down: public page degrades (no crash)" "$(code "${G[@]}" $B/events)" 200
chk "backend down: leak check" "$(curl -s "${G[@]}" $B/events | grep -ciE 'traceback|INTERNAL_API_URL|backend:8039')" 0
C start backend >/dev/null 2>&1; sleep 20
chk "backend recovered" "$(code "${G[@]}" $B/api/health)" 200
# exposure
PUB=$(C ps --format '{{.Service}} {{.Publishers}}' | grep -E '^(db|backend|public)' | grep -c '0\.0\.0\.0\|127\.0\.0\.1')
chk "db/backend/public publish no ports" "$PUB" 0
chk "nginx published only on loopback" "$(docker port "$(C ps -q nginx)" | grep -vc '^8080/tcp -> 127.0.0.1:')" 0
LAN=$(ipconfig getifaddr en0 2>/dev/null || true)
[ -n "$LAN" ] && chk "LAN address refused" "$(code --max-time 3 "http://$LAN:$STAGING_PORT/")" 000
chk "no secrets baked in backend image" "$(docker run --rm --entrypoint sh "$BACKEND_IMAGE" -c 'ls -a /app | grep -c "^\.env"')" 0
exit $fail
