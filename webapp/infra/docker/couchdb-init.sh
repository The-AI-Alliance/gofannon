#!/bin/bash
# webapp/infra/docker/couchdb-init.sh
#
# Idempotent CouchDB initialization. Reads COUCHDB_URL, COUCHDB_USER, and
# COUCHDB_PASSWORD from the environment so the same script works from
# inside a docker container (COUCHDB_URL=http://couchdb:5984) or from
# the host via puppet (COUCHDB_URL=http://localhost:5984).

set -e

COUCHDB_URL="${COUCHDB_URL:-http://couchdb:5984}"
COUCHDB_USER="${COUCHDB_USER:?COUCHDB_USER must be set}"
COUCHDB_PASSWORD="${COUCHDB_PASSWORD:?COUCHDB_PASSWORD must be set}"

# Wait for CouchDB to be available
echo "Waiting for CouchDB at ${COUCHDB_URL} ..."
until curl -sf "${COUCHDB_URL}/" > /dev/null; do
  echo "CouchDB not yet available, waiting..."
  sleep 5
done
echo "CouchDB is up!"

# Create _users database if it doesn't exist
echo "Creating _users database if it does not exist..."
response=$(curl -s -X PUT "${COUCHDB_URL}/_users" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -H "Content-Type: application/json")

if echo "$response" | grep -q "error"; then
  if ! echo "$response" | grep -q "file_exists"; then
    echo "Error creating _users database: $response"
    exit 1
  else
    echo "_users database already exists."
  fi
else
  echo "_users database created: $response"
fi

# --- Agent Data Store: database + indexes ---
# Create the agent_data_store database and its Mango indexes so that
# queries by userId/namespace are fast from the very first request.
# These are idempotent — CouchDB returns {"result":"exists"} if the
# index already exists with the same definition.

echo "Creating agent_data_store database if it does not exist..."
response=$(curl -s -X PUT "${COUCHDB_URL}/agent_data_store" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -H "Content-Type: application/json")

if echo "$response" | grep -q "error"; then
  if ! echo "$response" | grep -q "file_exists"; then
    echo "Warning: error creating agent_data_store: $response"
  else
    echo "agent_data_store database already exists."
  fi
else
  echo "agent_data_store database created: $response"
fi

echo "Creating Mango index idx-user-namespace on agent_data_store..."
response=$(curl -s -X POST "${COUCHDB_URL}/agent_data_store/_index" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -H "Content-Type: application/json" \
  -d '{
    "index": {
      "fields": ["userId", "namespace"]
    },
    "name": "idx-user-namespace",
    "type": "json"
  }')
echo "  Index result: $response"

# Disable logging of non-essential info to reduce noise
echo "Setting CouchDB logging level to 'warning'..."
curl -s -X PUT "${COUCHDB_URL}/_node/nonode@nohost/_config/log/level" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -d '"warning"' > /dev/null

echo "CouchDB initialization complete."
