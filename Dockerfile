# syntax=docker/dockerfile:1

# Stage 1: generate the static site from apps.json (build.py is stdlib-only)
FROM python:3.12-slim AS build
WORKDIR /src
COPY . .
# Shown in the footer; the release workflow passes the version from the release/vX.Y.Z branch.
ARG SITE_VERSION=dev
RUN SITE_VERSION="$SITE_VERSION" python build.py

# Stage 2: serve dist/ with nginx on :3000
FROM nginx:alpine
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 3000;
    listen [::]:3000;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_types text/css application/javascript text/javascript image/svg+xml;

    # Liveness probe for the release workflow's smoke test and deploy health check.
    location = /healthz {
        access_log off;
        default_type text/plain;
        return 200 "ok";
    }

    location /assets/ {
        add_header Cache-Control "public, max-age=2592000";
        try_files $uri =404;
    }

    location / {
        add_header Cache-Control "no-cache";
        try_files $uri $uri/ /index.html;
    }
}
EOF
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:3000/healthz || exit 1
