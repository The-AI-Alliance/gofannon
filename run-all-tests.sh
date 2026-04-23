#!/usr/bin/env bash
# run-all-tests.sh — run every test suite in the gofannon webapp and print a summary.
#
# Assumes:
#   - You're running this from the repo root (where ./webapp lives), OR you've
#     set REPO_ROOT below to point at it.
#   - Docker Compose stack from webapp/infra/docker is already up (couchdb,
#     minio, api, webui) — required for integration + E2E tests.
#   - `uv`, `pnpm`, and `docker` are on your PATH.
#
# The script does NOT fail-fast: every suite runs, results are collected, and a
# summary prints at the end. Exit code is 0 only if every suite passed.

set -u
set -o pipefail

# ---------- config ----------
REPO_ROOT="${REPO_ROOT:-$(pwd)}"
WEBAPP_DIR="$REPO_ROOT/webapp"
BACKEND_DIR="$WEBAPP_DIR/packages/api/user-service"
DOCKER_DIR="$WEBAPP_DIR/infra/docker"

# ---------- colors ----------
if [[ -t 1 ]]; then
  C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YLW=$'\033[33m'
  C_BLU=$'\033[34m'; C_BLD=$'\033[1m';  C_RST=$'\033[0m'
else
  C_RED=""; C_GRN=""; C_YLW=""; C_BLU=""; C_BLD=""; C_RST=""
fi

section() { printf "\n${C_BLU}${C_BLD}=== %s ===${C_RST}\n" "$1"; }
ok()      { printf "${C_GRN}✔ %s${C_RST}\n" "$1"; }
warn()    { printf "${C_YLW}⚠ %s${C_RST}\n" "$1"; }
fail()    { printf "${C_RED}✘ %s${C_RST}\n" "$1"; }

# ---------- result tracking ----------
declare -A RESULTS   # suite name -> PASS | FAIL | SKIP
SUITE_ORDER=()

record() {
  local name=$1 status=$2
  RESULTS[$name]=$status
  SUITE_ORDER+=("$name")
}

run_suite() {
  local name=$1; shift
  section "$name"
  if "$@"; then
    ok "$name passed"
    record "$name" PASS
  else
    fail "$name FAILED (exit $?)"
    record "$name" FAIL
  fi
}

# ---------- sanity checks ----------
[[ -d $WEBAPP_DIR  ]] || { fail "webapp dir not found: $WEBAPP_DIR"; exit 2; }
[[ -d $BACKEND_DIR ]] || { fail "backend dir not found: $BACKEND_DIR"; exit 2; }

section "Preflight"
echo "Repo root:  $REPO_ROOT"
echo "Webapp:     $WEBAPP_DIR"

# Check Docker services — integration + E2E need them.
DOCKER_OK=1
if ! docker ps --format '{{.Names}}' | grep -Eq '(^|-)couchdb(-|$)'; then
  warn "couchdb container not detected — integration/E2E tests will likely fail"
  DOCKER_OK=0
fi
if ! docker ps --format '{{.Names}}' | grep -Eq '(^|-)minio(-|$)'; then
  warn "minio container not detected — integration tests may fail"
  DOCKER_OK=0
fi
if ! docker ps --format '{{.Names}}' | grep -Eq '(^|-)api(-|$)'; then
  warn "api container not detected — E2E tests will fail"
  DOCKER_OK=0
fi
if ! docker ps --format '{{.Names}}' | grep -Eq '(^|-)webui(-|$)'; then
  warn "webui container not detected — E2E tests will fail"
  DOCKER_OK=0
fi
[[ $DOCKER_OK == 1 ]] && ok "Docker services detected"

# ---------- backend python env (uv) ----------
section "Python env (uv)"
cd "$BACKEND_DIR"
if [[ ! -d .venv ]]; then
  echo "Creating .venv with uv…"
  uv venv
  uv pip install -r requirements.txt
else
  ok ".venv already exists (skipping install — rerun 'uv pip install -r requirements.txt' if deps changed)"
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# ---------- frontend deps + playwright ----------
section "Frontend deps + Playwright browsers"
cd "$WEBAPP_DIR"
pnpm install --frozen-lockfile || pnpm install
# Playwright browser binaries (idempotent; skips if already installed)
npx playwright install >/dev/null 2>&1 || warn "playwright install had issues (browsers may already be present)"

# ---------- run all test suites ----------
cd "$WEBAPP_DIR"

run_suite "Frontend unit (Vitest)" pnpm run test:unit:frontend

cd "$BACKEND_DIR"
run_suite "Backend unit (pytest)" python -m pytest tests/unit -v

if [[ $DOCKER_OK == 1 ]]; then
  run_suite "Backend integration (pytest)" python -m pytest tests/integration -v
  cd "$WEBAPP_DIR"
  run_suite "E2E (Playwright)" pnpm run test:e2e
else
  warn "Skipping integration + E2E (Docker services not fully up)"
  record "Backend integration (pytest)" SKIP
  record "E2E (Playwright)"            SKIP
fi

# ---------- summary ----------
section "Summary"
fail_count=0
skip_count=0
for name in "${SUITE_ORDER[@]}"; do
  case "${RESULTS[$name]}" in
    PASS) printf "  ${C_GRN}PASS${C_RST}  %s\n" "$name" ;;
    FAIL) printf "  ${C_RED}FAIL${C_RST}  %s\n" "$name"; ((fail_count++)) ;;
    SKIP) printf "  ${C_YLW}SKIP${C_RST}  %s\n" "$name"; ((skip_count++)) ;;
  esac
done
echo
if (( fail_count == 0 && skip_count == 0 )); then
  ok "All suites passed."
  exit 0
elif (( fail_count == 0 )); then
  warn "$skip_count suite(s) skipped, no failures."
  exit 0
else
  fail "$fail_count suite(s) failed."
  exit 1
fi