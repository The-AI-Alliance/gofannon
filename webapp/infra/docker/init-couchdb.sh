#!/bin/bash
# init-couchdb.sh

# Exit immediately if a command exits with a non-zero status.
set -e

COUCHDB_URL="http://couchdb:5984"
ADMIN_USER="${COUCHDB_USER:-admin}"
ADMIN_PASSWORD="${COUCHDB_PASSWORD:-password}"

echo "Waiting for CouchDB to be available at ${COUCHDB_URL}..."
until curl -s ${COUCHDB_URL}/_up > /dev/null; do
  echo "CouchDB not yet available, sleeping..."
  sleep 2
done
echo "CouchDB is up and responsive."

AUTH_HEADER="-u ${ADMIN_USER}:${ADMIN_PASSWORD}"

# Function to create a database if it doesn't exist
create_db_if_not_exists() {
  DB_NAME=$1
  echo "Checking for database: ${DB_NAME}"
  
  # Fetch response to check if DB exists. CouchDB returns a 404 for non-existent DBs.
  response=$(curl -s -o /dev/null -w "%{http_code}" ${AUTH_HEADER} "${COUCHDB_URL}/${DB_NAME}")
  
  if [ "$response" == "404" ]; then
    echo "Database ${DB_NAME} not found. Creating..."
    create_response=$(curl -s ${AUTH_HEADER} -X PUT "${COUCHDB_URL}/${DB_NAME}")
    if echo "$create_response" | grep -q "ok"; then
      echo "Database ${DB_NAME} created successfully."
    else
      echo "Failed to create database ${DB_NAME}. Response: ${create_response}"
      exit 1
    fi
  elif [ "$response" == "200" ]; then
    echo "Database ${DB_NAME} already exists."
  else
    echo "Unexpected HTTP response code for ${DB_NAME}: ${response}. Attempting to create anyway."
    create_response=$(curl -s ${AUTH_HEADER} -X PUT "${COUCHDB_URL}/${DB_NAME}")
    if echo "$create_response" | grep -q "ok"; then
      echo "Database ${DB_NAME} created successfully."
    elif echo "$create_response" | grep -q "file_exists"; then
      echo "Database ${DB_NAME} already exists (handled conflict)."
    else
      echo "Failed to create or confirm database ${DB_NAME}. Response: ${create_response}"
      exit 1
    fi
  fi
}

# Create application-specific databases
create_db_if_not_exists "agents"
create_db_if_not_exists "sessions"
create_db_if_not_exists "tickets"

echo "CouchDB application database initialization complete."