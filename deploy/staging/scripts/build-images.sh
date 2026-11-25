#!/usr/bin/env bash
# Build backend/public/nginx images from one exact commit (git archive, no working-tree files).
# Usage: build-images.sh <commit-sha> [--platform linux/amd64]  (run on a build machine, not the VPS)
set -euo pipefail
ref=${1:?commit sha}; shift || true
platform=()
[ "${1:-}" = "--platform" ] && platform=(--platform "${2:?}")
sha=$(git rev-parse --verify "$ref^{commit}")
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git archive "$sha" | tar -x -C "$tmp"
b() { docker build ${platform[@]+"${platform[@]}"} "$@"; }
b -t "afisha-staging/backend:$sha" "$tmp/backend"
b --build-arg NEXT_PUBLIC_API_BASE=/api -t "afisha-staging/public:$sha" "$tmp/public"
b -f "$tmp/deploy/nginx/Dockerfile" -t "afisha-staging/nginx-base:$sha" "$tmp"
b -f "$tmp/deploy/staging/nginx/Dockerfile" --build-arg "BASE_IMAGE=afisha-staging/nginx-base:$sha" \
  -t "afisha-staging/nginx:$sha" "$tmp"
cat <<OUT
BACKEND_IMAGE=afisha-staging/backend:$sha
PUBLIC_IMAGE=afisha-staging/public:$sha
NGINX_IMAGE=afisha-staging/nginx:$sha
# Transfer without a registry: docker save <images> | gzip > release.tgz ; docker load < release.tgz
OUT
