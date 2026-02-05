# Database Configuration

## Environment Variables

Configuration is managed through environment variables in `config/__init__.py`.

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_PROVIDER` | Provider selection: `memory`, `couchdb`, `firestore`, `dynamodb` | `memory` |

### CouchDB

| Variable | Description | Required |
|----------|-------------|----------|
| `COUCHDB_URL` | Server URL (e.g., `http://localhost:5984`) | Yes |
| `COUCHDB_USER` | Admin username | Yes |
| `COUCHDB_PASSWORD` | Admin password | Yes |

### Firestore

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Yes |
| `FIRESTORE_PROJECT_ID` | GCP project ID | Optional (auto-detected) |

### DynamoDB

| Variable | Description | Required |
|----------|-------------|----------|
| `DYNAMODB_REGION` | AWS region | Yes (default: `us-east-1`) |
| `DYNAMODB_ENDPOINT_URL` | Custom endpoint (for local dev) | No |
| `AWS_ACCESS_KEY_ID` | AWS credentials | Yes* |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | Yes* |

*Can also use IAM roles, AWS credentials file, or other standard AWS auth methods.

## Configuration Examples

### Memory (Development)

```bash
# No configuration needed - this is the default
DATABASE_PROVIDER=memory
```

### CouchDB (Recommended for Production)

```bash
DATABASE_PROVIDER=couchdb
COUCHDB_URL=http://localhost:5984
COUCHDB_USER=admin
COUCHDB_PASSWORD=your-secure-password
```

### Firestore

```bash
DATABASE_PROVIDER=firestore
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### DynamoDB

```bash
DATABASE_PROVIDER=dynamodb
DYNAMODB_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# Optional: Local DynamoDB for development
DYNAMODB_ENDPOINT_URL=http://localhost:8000
```

## Docker Compose Setup

The default `docker-compose.yml` includes CouchDB:

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

  api:
    environment:
      - DATABASE_PROVIDER=couchdb
      - COUCHDB_URL=http://couchdb:5984
      - COUCHDB_USER=${COUCHDB_USER:-admin}
      - COUCHDB_PASSWORD=${COUCHDB_PASSWORD:-password}

volumes:
  couchdb-data:
```

Create a `.env` file in `webapp/infra/docker/`:

```bash
# Required
COUCHDB_USER=admin
COUCHDB_PASSWORD=your-secure-password

# At least one LLM provider
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

## Factory Function

The factory in `services/database_service/__init__.py` creates the appropriate instance:

```python
def get_database_service(settings) -> DatabaseService:
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
    else:
        _db_instance = MemoryDatabaseService()
    
    return _db_instance
```

## Validation

Missing required configuration raises a `ValueError` at startup:

```python
# Example output
ValueError: CouchDB requires COUCHDB_URL, COUCHDB_USER, and COUCHDB_PASSWORD
```

## Switching Providers

1. Set the `DATABASE_PROVIDER` environment variable
2. Add provider-specific credentials
3. Restart the application

**Note:** Data does not automatically migrate between providers. See the troubleshooting guide for migration options.