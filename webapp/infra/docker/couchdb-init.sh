#!/bin/bash
# webapp/infra/docker/couchdb-init.sh

# Wait for CouchDB to be available
echo "Waiting for CouchDB to start..."
until curl -s http://couchdb:5984/ > /dev/null; do
  echo "CouchDB not yet available, waiting..."
  sleep 5
done
echo "CouchDB is up!"

# Create _users database if it doesn't exist
# This database is crucial for CouchDB's internal user management and authentication
echo "Creating _users database if it does not exist..."
response=$(curl -s -X PUT "http://couchdb:5984/_users" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -H "Content-Type: application/json")

if echo "$response" | grep -q "error"; then
  # If the error is 'file_exists', it's fine, otherwise something is wrong
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
response=$(curl -s -X PUT "http://couchdb:5984/agent_data_store" \
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
response=$(curl -s -X POST "http://couchdb:5984/agent_data_store/_index" \
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
curl -X PUT "http://couchdb:5984/_node/nonode@nohost/_config/log/level" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -d '"warning"'


echo "CouchDB initialization complete."