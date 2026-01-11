# Memory Database (Default)

**File**: [memory.py](../../../webapp/packages/api/user-service/services/database_service/memory.py)

**Purpose**: In-memory storage for testing and development

## Implementation Details

```python
class MemoryDatabaseService(DatabaseService):
    def __init__(self):
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # Structure: {db_name: {doc_id: document}}
```

## Characteristics

- **Storage**: Python dictionary in RAM
- **Persistence**: None (data lost on restart)
- **Performance**: Extremely fast (no I/O)
- **Revision Tracking**: Returns placeholder `"memory-rev"`
- **Auto-initialization**: No setup required

## When to Use

- Unit testing
- Local development without external dependencies
- CI/CD pipelines
- Prototype/demo environments

## Configuration

```bash
# .env or environment variables
DATABASE_PROVIDER=memory
# No additional configuration needed
```

## Special Considerations

- No persistence across restarts
- Single-process only (no shared state)
- No concurrency control
- Unlimited storage (until RAM exhausted)

## Example Usage

```python
from services.database_service import get_database_service
from config import Settings

settings = Settings(DATABASE_PROVIDER="memory")
db = get_database_service(settings)

# Save a document
db.save("agents", "agent-1", {"name": "Test Agent"})

# Retrieve it
agent = db.get("agents", "agent-1")
print(agent)  # {"_id": "agent-1", "name": "Test Agent"}

# List all agents
all_agents = db.list_all("agents")

# Delete the agent
db.delete("agents", "agent-1")
```

## Testing

Memory database is the default for all unit tests:

```python
import pytest
from services.database_service.memory import MemoryDatabaseService

@pytest.fixture
def db_service():
    """Create a fresh memory database for each test."""
    return MemoryDatabaseService()

def test_save_and_get(db_service):
    doc = {"name": "Test Agent"}
    db_service.save("agents", "test-id", doc)

    retrieved = db_service.get("agents", "test-id")
    assert retrieved["name"] == "Test Agent"
```

## Advantages

1. **Zero Configuration**: Works out of the box
2. **Fast**: No network or disk I/O overhead
3. **Isolation**: Each instance is independent
4. **Predictable**: No external dependencies to fail
5. **Clean State**: Easy to reset between tests

## Limitations

1. **No Persistence**: Data lost on application restart
2. **Memory Bound**: Limited by available RAM
3. **Single Process**: Cannot share state between processes
4. **No Transactions**: No ACID guarantees
5. **No Concurrency**: Not thread-safe without additional locking

## Production Use

**NOT RECOMMENDED** for production environments. Use a persistent database like:
- [CouchDB](couchdb.md) for self-hosted deployments
- [Firestore](firestore.md) for Google Cloud
- [DynamoDB](dynamodb.md) for AWS

## Related Documentation

- [Configuration](../configuration.md) - Database provider configuration
- [Schema](../schema.md) - Collection and document schemas
- [Testing](../testing.md) - Testing strategies
- [Database Service README](../README.md) - Overview

---

Last Updated: 2026-01-11
