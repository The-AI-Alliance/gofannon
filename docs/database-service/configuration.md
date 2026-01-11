# Configuration

## Environment Variables

Configuration is managed through environment variables, defined in [config/__init__.py](../../webapp/packages/api/user-service/config/__init__.py).

**Core Settings**:
```python
class Settings:
    # Database provider selection
    DATABASE_PROVIDER: str = os.getenv("DATABASE_PROVIDER", "memory")

    # CouchDB configuration
    COUCHDB_URL: str | None = os.getenv("COUCHDB_URL")
    COUCHDB_USER: str | None = os.getenv("COUCHDB_USER")
    COUCHDB_PASSWORD: str | None = os.getenv("COUCHDB_PASSWORD")

    # DynamoDB configuration
    DYNAMODB_REGION: str = os.getenv("DYNAMODB_REGION", "us-east-1")
    DYNAMODB_ENDPOINT_URL: str | None = os.getenv("DYNAMODB_ENDPOINT_URL")

    # Firestore uses GOOGLE_APPLICATION_CREDENTIALS (Firebase Admin SDK standard)
```

## Configuration File

Create a `.env` file in the user-service directory:

```bash
# Database Provider Selection
# Options: memory, couchdb, firestore, dynamodb
DATABASE_PROVIDER=couchdb

# CouchDB Configuration (if using couchdb)
COUCHDB_URL=http://localhost:5984
COUCHDB_USER=admin
COUCHDB_PASSWORD=password

# DynamoDB Configuration (if using dynamodb)
DYNAMODB_REGION=us-east-1
DYNAMODB_ENDPOINT_URL=http://localhost:8000  # Optional, for local DynamoDB

# Firestore Configuration (if using firestore)
# Set GOOGLE_APPLICATION_CREDENTIALS to service account JSON path
# export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

## Factory Function

The `get_database_service()` function in [__init__.py](../../webapp/packages/api/user-service/services/database_service/__init__.py:33-69) instantiates the correct database implementation:

```python
_db_instance: DatabaseService | None = None

def get_database_service(settings) -> DatabaseService:
    """
    Factory function to get the appropriate database service instance.
    Returns a singleton instance based on DATABASE_PROVIDER setting.
    """
    global _db_instance

    if _db_instance is not None:
        return _db_instance

    provider = settings.DATABASE_PROVIDER.lower()

    if provider == "couchdb":
        if not all([settings.COUCHDB_URL, settings.COUCHDB_USER, settings.COUCHDB_PASSWORD]):
            raise ValueError("CouchDB configuration incomplete")
        _db_instance = CouchDBService(
            settings.COUCHDB_URL,
            settings.COUCHDB_USER,
            settings.COUCHDB_PASSWORD
        )

    elif provider == "firestore":
        _db_instance = FirestoreService()

    elif provider == "dynamodb":
        _db_instance = DynamoDBService(
            region_name=settings.DYNAMODB_REGION,
            endpoint_url=settings.DYNAMODB_ENDPOINT_URL
        )

    else:  # Default to memory
        _db_instance = MemoryDatabaseService()

    return _db_instance
```

## Validation

The factory function validates required credentials and raises errors if configuration is incomplete:

```python
# Example: CouchDB validation
if not all([settings.COUCHDB_URL, settings.COUCHDB_USER, settings.COUCHDB_PASSWORD]):
    raise ValueError("CouchDB requires COUCHDB_URL, COUCHDB_USER, and COUCHDB_PASSWORD")
```

## Docker Compose Configuration

For local development, [docker-compose.yml](../../webapp/infra/docker/docker-compose.yml) includes database services:

```yaml
services:
  couchdb:
    image: couchdb:latest
    container_name: gofannon-couchdb
    ports:
      - "5984:5984"
    environment:
      - COUCHDB_USER=${COUCHDB_USER:-admin}
      - COUCHDB_PASSWORD=${COUCHDB_PASSWORD:-password}
    volumes:
      - couchdb-data:/opt/couchdb/data
      - ./couchdb-init.sh:/docker-entrypoint-initdb.d/init.sh

  # Add DynamoDB Local for development
  dynamodb-local:
    image: amazon/dynamodb-local
    container_name: gofannon-dynamodb
    ports:
      - "8000:8000"
    command: "-jar DynamoDBLocal.jar -sharedDb"

volumes:
  couchdb-data:
```

## Provider-Specific Configuration

### Memory Database

```bash
DATABASE_PROVIDER=memory
# No additional configuration needed
```

### Apache CouchDB

```bash
DATABASE_PROVIDER=couchdb
COUCHDB_URL=http://localhost:5984
COUCHDB_USER=admin
COUCHDB_PASSWORD=password
```

See [CouchDB Implementation](implementations/couchdb.md) for details.

### Google Cloud Firestore

```bash
DATABASE_PROVIDER=firestore

# Authentication via Firebase Admin SDK:
# - Set GOOGLE_APPLICATION_CREDENTIALS pointing to service account JSON
# - Or use Application Default Credentials in GCP
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

See [Firestore Implementation](implementations/firestore.md) for details.

### AWS DynamoDB

```bash
DATABASE_PROVIDER=dynamodb
DYNAMODB_REGION=us-east-1
DYNAMODB_ENDPOINT_URL=http://localhost:8000  # Optional, for local DynamoDB

# AWS credentials via standard AWS SDK methods:
# - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# - AWS credentials file (~/.aws/credentials)
# - IAM role (when running on EC2/ECS/Lambda)
```

See [DynamoDB Implementation](implementations/dynamodb.md) for details.

## Related Documentation

- [Database Interface](interface.md) - Abstract base class and method specifications
- [Schema](schema.md) - Collection and document schemas
- [Implementations](implementations/) - Provider-specific documentation
- [Database Service README](README.md) - Overview and getting started

---

Last Updated: 2026-01-11
