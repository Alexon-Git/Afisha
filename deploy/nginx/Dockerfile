FROM node:24.22.3-alpine@sha256:116b800c3754b440ee0aa3ed2f20f5bf3d99a554bfd9adeea09ea8017f6e85f5 AS admin-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
ENV PUBLIC_URL=/admin
RUN npm run build

FROM nginx:1.30.7-alpine@sha256:caf4e1e032a20f9c3c5e28fc7f25ffd768ad8677b4975c54193075997b3a97e3
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx/afisha.conf /etc/nginx/conf.d/default.conf
COPY deploy/nginx/routes.conf /etc/nginx/afisha/routes.conf
COPY deploy/nginx/admin-access.local.conf /etc/nginx/afisha/admin-access.conf
COPY --from=admin-build /app/build /srv/admin
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/api/health"]
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
