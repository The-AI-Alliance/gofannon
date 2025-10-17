#!/bin/bash
# webapp/infra/docker/couchdb-init.sh

# Wait for CouchDB to be available
echo "Waiting for CouchDB to start..."
until curl -s http://couchdb:5984/_utils/ > /dev/null; do
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

# You can add commands to create other essential databases here if needed, e.g.:
# echo "Creating sessions database if it does not exist..."
# curl -s -X PUT "http://couchdb:5984/sessions" -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" -H "Content-Type: application/json"
# echo "Creating agents database if it does not exist..."
# curl -s -X PUT "http://couchdb:5984/agents" -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" -H "Content-Type: application/json"

# Disable logging of non-essential info to reduce noise
echo "Setting CouchDB logging level to 'warning'..."
curl -X PUT "http://couchdb:5984/_node/nonode@nohost/_config/log/level" \
  -u "${COUCHDB_USER}:${COUCHDB_PASSWORD}" \
  -d '"warning"'


echo "CouchDB initialization complete."