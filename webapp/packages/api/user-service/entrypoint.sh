#!/bin/bash
set -e

COUCHDB_URL="${COUCHDB_URL:-http://couchdb:5984}"
COUCHDB_USER="${COUCHDB_USER:-admin}"
COUCHDB_PASSWORD="${COUCHDB_PASSWORD:-password}"
MAX_RETRIES=30
RETRY_INTERVAL=2

# --- Wait for CouchDB to be reachable ---
echo "Waiting for CouchDB at ${COUCHDB_URL} ..."
retries=0
until curl -sf "${COUCHDB_URL}/" > /dev/null 2>&1; do
  retries=$((retries + 1))
  if [ "$retries" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: CouchDB not available after $((MAX_RETRIES * RETRY_INTERVAL))s — giving up."
    exit 1
  fi
  sleep "$RETRY_INTERVAL"
done
echo "CouchDB is up."

# --- One-time initialization (idempotent) ---
echo "Ensuring _users database exists..."
response=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
  "${COUCHDB_URL}/_users" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -H "Content-Type: application/json")

case "$response" in
  201) echo "_users database created." ;;
  412) echo "_users database already exists." ;;
  *)   echo "WARNING: Unexpected status $response creating _users — continuing anyway." ;;
esac

# Reduce CouchDB log noise
curl -s -X PUT "${COUCHDB_URL}/_node/nonode@nohost/_config/log/level" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -d '"warning"' > /dev/null 2>&1 || true

echo "CouchDB initialization complete."

# --- Hand off to the real command ---
exec "$@"