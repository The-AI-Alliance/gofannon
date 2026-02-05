# Database Service

The Gofannon database service provides a flexible, abstraction-based approach to data persistence. It supports multiple database backends through a common interface, allowing you to switch between providers without changing application code.

## Supported Databases

| Database | Best For | Setup Complexity |
|----------|----------|------------------|
| **In-Memory** | Development, testing | None |
| **CouchDB** | Self-hosted production | Low (included in Docker Compose) |
| **Firestore** | Google Cloud deployments | Medium |
| **DynamoDB** | AWS deployments | Medium |

## Quick Start

### Development (In-Memory)

No configuration needed—just start the server:

```bash
cd webapp/packages/api/user-service
uvicorn main:app --reload
```

### Production (CouchDB)

The Docker Compose setup includes CouchDB:

```bash
cd webapp/infra/docker

# Create .env file
cat > .env << EOF
COUCHDB_USER=admin
COUCHDB_PASSWORD=your-secure-password
OPENAI_API_KEY=sk-...
EOF

docker-compose up
```

See [Configuration](configuration.md) for all providers.

## Architecture

### Database Abstraction

All implementations inherit from `DatabaseService` and provide four core methods:

```python
class DatabaseService(ABC):
    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]
    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]
    def delete(self, db_name: str, doc_id: str) -> None
    def list_all(self, db_name: str) -> List[Dict[str, Any]]
```

### Factory Pattern

A factory function instantiates the correct implementation based on `DATABASE_PROVIDER`:

```python
from services.database_service import get_database_service
from config import Settings

settings = Settings()
db = get_database_service(settings)

# Works with any provider
doc = db.get("agents", "agent-id")
db.save("agents", "agent-id", {"name": "MyAgent", ...})
```

**Note:** The factory uses a singleton pattern. Changing providers requires an application restart.

### Collections

| Collection | Purpose |
|------------|---------|
| `agents` | AI agent definitions and code |
| `deployments` | Friendly name → agent ID mappings |
| `users` | User profiles and billing |
| `sessions` | Chat conversation history |
| `tickets` | Async job tracking |
| `demos` | Demo application configs |
| `agent_data_store` | Agent key-value storage |

See [Schema](schema.md) for detailed document structures.

## Implementing a New Database

1. Create a class inheriting from `DatabaseService`:

```python
# services/database_service/my_db.py
from .base import DatabaseService

class MyDatabaseService(DatabaseService):
    def __init__(self, connection_string: str):
        self.client = MyDBClient(connection_string)
    
    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        doc = self.client.find(db_name, doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        doc["_id"] = doc_id
        return doc
    
    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc["_id"] = doc_id
        self.client.upsert(db_name, doc_id, doc)
        return doc
    
    def delete(self, db_name: str, doc_id: str) -> None:
        self.client.remove(db_name, doc_id)
    
    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        return self.client.find_all(db_name) or []
```

2. Register in the factory (`services/database_service/__init__.py`):

```python
elif provider == "mydb":
    from .my_db import MyDatabaseService
    _db_instance = MyDatabaseService(settings.MYDB_CONNECTION_STRING)
```

3. Add configuration to `config/__init__.py`:

```python
MYDB_CONNECTION_STRING: str | None = os.getenv("MYDB_CONNECTION_STRING")
```

### Implementation Requirements

- **get()**: Return document with `_id` field, raise `HTTPException(404)` if not found
- **save()**: Upsert document, return saved document with `_id`
- **delete()**: Remove document silently (no error if missing)
- **list_all()**: Return empty list `[]` if collection doesn't exist

## Documentation

- [Configuration](configuration.md) - Environment variables and provider setup
- [Schema](schema.md) - Document structures and field specifications
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

## External Resources

- [CouchDB Documentation](https://docs.couchdb.org/)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)