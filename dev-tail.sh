#!/bin/bash
# dev-tail.sh — Start the dev stack and tail logs.
#
# Usage:
#   ./dev-tail.sh         # start everything (Phase B auth is on by default)
#   ./dev-tail.sh --stop  # stop docker services and vite

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
WEBAPP="$REPO_ROOT/webapp"
INFRA="$WEBAPP/infra/docker"
STOP=false

# Stable compose project name so volumes/data persist across runs.
export COMPOSE_PROJECT_NAME=gofannon-dev

for arg in "$@"; do
  case "$arg" in
    --stop)    STOP=true ;;
    --help|-h)
      grep '^#' "$0" | head -10
      exit 0
      ;;
  esac
done

if [ "$STOP" = true ]; then
  cd "$INFRA"
  docker compose down
  pkill -f "vite" 2>/dev/null || true
  echo "Stopped."
  exit 0
fi

# --- Start docker services (detached so we can launch vite alongside) ---
echo "[dev-tail] Starting docker services (project: $COMPOSE_PROJECT_NAME)..."
cd "$INFRA"
docker compose up -d couchdb api
cd "$REPO_ROOT"

# --- Vite as a background job whose output we tee ---
echo "[dev-tail] Starting webui dev server..."
cd "$WEBAPP"
pkill -f "vite" 2>/dev/null || true
sleep 1

# Prefix vite output so we can tell it apart from docker logs
( pnpm --filter webui dev --host 0.0.0.0 --port 3000 2>&1 | sed 's/^/[webui] /' ) &
VITE_PID=$!

cd "$REPO_ROOT"

cat <<SUMMARY

==========================================================
  CouchDB:  http://localhost:5984   (admin/password)
  API:      http://localhost:8000
  UI:       http://localhost:3000
  Project:  $COMPOSE_PROJECT_NAME
  Volumes:  $(docker volume ls --filter "name=${COMPOSE_PROJECT_NAME}" --format '{{.Name}}' | tr '\n' ' ')

  Phase B auth is enabled. Login at http://localhost:3000/login
  → "Dev stub login". Users defined in .dev-auth.yaml:
    - alice         (admin: tomcat, member: httpd)
    - bob           (emeritus, login is denied)
    - site_admin_1  (cross-workspace site admin)
==========================================================
Tailing logs. Ctrl+C stops vite and tail; docker keeps running.
Use './dev-tail.sh --stop' to stop docker too.

SUMMARY

# Tail docker logs in foreground while vite runs in background
trap "kill $VITE_PID 2>/dev/null; exit 0" INT TERM

cd "$INFRA"
docker compose logs -f couchdb api