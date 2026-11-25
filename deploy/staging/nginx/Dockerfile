# Staging gateway layer on top of the unchanged project Nginx image.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
USER root
COPY deploy/staging/nginx/staging-server.conf /etc/nginx/conf.d/default.conf
COPY deploy/staging/nginx/00-staging-map.conf /etc/nginx/conf.d/00-staging-map.conf
# Derive staging routes from the project routes so they cannot drift:
#  - every nosniff header gets X-Robots-Tag noindex next to it (location-level add_header
#    cancels server-level ones, so it must be repeated);
#  - /api/ (not /api/auth/login) accepts Basic OR a Bearer-shaped header (JWT verified by FastAPI);
#    login always needs the Basic gate.
RUN set -eu; f=/etc/nginx/afisha/routes.conf; \
    sed -i 's|^\( *\)add_header X-Content-Type-Options nosniff always;$|&\n\1add_header X-Robots-Tag "noindex, nofollow, noarchive" always;|' $f; \
    sed -i 's|^location /api/ {$|&\n    auth_basic $staging_api_gate;|' $f; \
    test "$(grep -c 'X-Robots-Tag' $f)" -ge 6; \
    test "$(grep -c 'auth_basic $staging_api_gate' $f)" = 1; \
    echo '# staging: server-level Basic Auth gate in staging-server.conf' > /etc/nginx/afisha/admin-access.conf
USER nginx
