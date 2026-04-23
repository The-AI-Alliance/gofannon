#!/bin/bash
# dev-tail.sh — Start everything and tail logs.
#
# Usage:
#   ./dev-tail.sh             # legacy auth
#   ./dev-tail.sh --phase-b   # Phase B with dev_stub
#   ./dev-tail.sh --stop      # stop everything

set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
WEBAPP="$REPO_ROOT/webapp"
INFRA="$WEBAPP/infra/docker"
PHASE_B=false
STOP=false

# Make sure docker compose uses a stable project name so data persists
# across runs from this repo.
export COMPOSE_PROJECT_NAME=gofannon-dev

for arg in "$@"; do
  case "$arg" in
    --phase-b) PHASE_B=true ;;
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

# --- Optional Phase B auth config ---
if [ "$PHASE_B" = true ]; then
  AUTH_YAML="$REPO_ROOT/.dev-auth.yaml"
  cat > "$AUTH_YAML" <<'YAML'
auth:
  providers:
    - type: dev_stub
      enabled: true
      config:
        display_name: "Dev stub login"
        users:
          - uid: alice
            display_name: Alice Dev
            email: alice@dev.local
            workspaces:
              - id: project:tomcat
                role: admin
                display_name: Apache Tomcat
              - id: project:httpd
                role: member
                display_name: Apache HTTPD
          - uid: bob
            display_name: Bob Emeritus
            email: bob@dev.local
            workspaces: []
          - uid: site_admin_1
            display_name: Site Admin
            email: admin@dev.local
            workspaces: []
  site_admins:
    - dev_stub:site_admin_1
  session_ttl_hours: 24
  workspace_refresh_minutes: 15
  legacy_firebase_enabled: true
YAML

  cat > "$INFRA/docker-compose.phase-b.override.yml" <<YAML
services:
  api:
    volumes:
      - $AUTH_YAML:/auth-config/auth.yaml:ro
    environment:
      AUTH_CONFIG_PATH: /auth-config/auth.yaml
YAML

  COMPOSE_FLAGS="-f docker-compose.yml -f docker-compose.phase-b.override.yml"
else
  COMPOSE_FLAGS=""
fi

# --- Start docker services (detached so we can launch vite alongside) ---
echo "[dev-tail] Starting docker services (project: $COMPOSE_PROJECT_NAME)..."
cd "$INFRA"
docker compose $COMPOSE_FLAGS up -d couchdb api
cd "$REPO_ROOT"

# --- Vite as a background job whose output we tee ---
echo "[dev-tail] Starting webui dev server..."
cd "$WEBAPP"
if [ "$PHASE_B" = true ]; then
  export VITE_AUTH_PROVIDER="session"
fi
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

$([ "$PHASE_B" = true ] && cat <<PB
  Phase B: ON
  Login at http://localhost:3000/login → "Dev stub login"
  Users: alice (projects) / bob (emeritus) / site_admin_1 (admin)
PB
)
==========================================================
Tailing logs. Ctrl+C stops vite and tail; docker keeps running.
Use './dev-tail.sh --stop' to stop docker too.

SUMMARY

# Tail docker logs in foreground while vite runs in background
# trap Ctrl+C to kill the vite process
trap "kill $VITE_PID 2>/dev/null; exit 0" INT TERM

cd "$INFRA"
docker compose $COMPOSE_FLAGS logs -f couchdb api
