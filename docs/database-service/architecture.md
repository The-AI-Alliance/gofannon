# Database Service Architecture

## Overview

The Gofannon database service uses an abstraction layer to support multiple database backends through a unified interface. This design allows the application to remain database-agnostic while supporting different deployment scenarios.

## Directory Structure

```
webapp/packages/api/user-service/services/database_service/
├── __init__.py      # Factory function and singleton management
├── base.py          # Abstract base class defining the interface
├── memory.py        # In-memory implementation
├── couchdb.py       # Apache CouchDB implementation
├── firestore.py     # Google Cloud Firestore implementation
└── dynamodb.py      # AWS DynamoDB implementation
```

## Design Patterns

### Abstract Factory Pattern

The database service implements the **Abstract Factory Pattern** to provide a consistent interface across different database implementations.

**Components:**

1. **Abstract Product** (`DatabaseService` in [base.py](../../webapp/packages/api/user-service/services/database_service/base.py))
   - Defines the interface all implementations must follow
   - Uses Python's `abc.ABC` (Abstract Base Class)
   - Declares four abstract methods: `get()`, `save()`, `delete()`, `list_all()`

2. **Concrete Products** (Implementation files)
   - `MemoryDatabaseService` - In-memory dictionary storage
   - `CouchDBService` - CouchDB client wrapper
   - `FirestoreService` - Firebase Admin SDK wrapper
   - `DynamoDBService` - Boto3 DynamoDB wrapper

3. **Factory Function** (`get_database_service()` in [__init__.py](../../webapp/packages/api/user-service/services/database_service/__init__.py:33-69))
   - Reads configuration to determine which implementation to use
   - Instantiates and returns the appropriate concrete product
   - Validates required configuration before instantiation

**Benefits:**
- Application code is decoupled from specific database implementations
- Easy to add new database backends
- Can switch databases via configuration without code changes
- Consistent error handling across implementations

### Singleton Pattern

The database service uses the **Singleton Pattern** to ensure only one database connection exists throughout the application lifecycle.

**Implementation:**

```python
_db_instance: DatabaseService | None = None

def get_database_service(settings) -> DatabaseService:
    """Factory function returns singleton instance."""
    global _db_instance

    if _db_instance is not None:
        return _db_instance

    # Create instance based on settings
    provider = settings.DATABASE_PROVIDER.lower()

    if provider == "couchdb":
        _db_instance = CouchDBService(...)
    elif provider == "firestore":
        _db_instance = FirestoreService(...)
    # ... etc

    return _db_instance
```

**Benefits:**
- Single connection pool/client instance
- Reduced memory usage
- Consistent state across the application
- Avoids connection overhead

**Location:** [__init__.py](../../webapp/packages/api/user-service/services/database_service/__init__.py:11-69)

## Dependency Injection

The database service is injected into API endpoints using **FastAPI's Dependency Injection** system.

### Dependency Definition

```python
# dependencies.py
from services.database_service import get_database_service
from config import get_settings

def get_db() -> DatabaseService:
    """Dependency that provides the database service."""
    settings = get_settings()
    return get_database_service(settings)
```

**Location:** [dependencies.py](../../webapp/packages/api/user-service/dependencies.py:27-30)

### Usage in Endpoints

```python
# routes.py
from fastapi import Depends, APIRouter
from dependencies import get_db
from services.database_service.base import DatabaseService

router = APIRouter()

@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: str,
    db: DatabaseService = Depends(get_db)
):
    """Retrieve an agent by ID."""
    return db.get("agents", agent_id)
```

**Benefits:**
- Testable (can inject mock database)
- Consistent across all endpoints
- Automatic lifecycle management
- Type hints for IDE support

## Data Flow

### Request Flow

```
Client Request
    ↓
FastAPI Route Handler
    ↓
Depends(get_db) - Dependency Injection
    ↓
get_database_service() - Factory Function
    ↓
Singleton Instance (CouchDB/Firestore/DynamoDB/Memory)
    ↓
Database Method (get/save/delete/list_all)
    ↓
Actual Database
    ↓
Response to Client
```

### Example: Creating an Agent

```
POST /agents
    ↓
create_agent(agent_data, db=Depends(get_db))
    ↓
db.save("agents", agent_id, agent_data)
    ↓
CouchDBService.save()  [or other implementation]
    ↓
CouchDB HTTP API
    ↓
{"id": "...", "rev": "..."}
    ↓
Return to client
```

## Component Interactions

### Configuration Layer

```
Environment Variables (.env)
    ↓
Settings Class (config/__init__.py)
    ↓
get_settings() - Cached settings instance
    ↓
Provides to Factory Function
```

### Service Layer

```
Abstract Base Class (base.py)
    ↑ extends
    |
Concrete Implementations (memory.py, couchdb.py, etc.)
    ↑ instantiates
    |
Factory Function (__init__.py)
    ↑ calls
    |
Dependency Function (dependencies.py)
    ↑ uses
    |
API Routes (routes.py)
```

## Extension Points

The architecture is designed to be extensible:

### Adding a New Database

1. **Create Implementation File**
   - Inherit from `DatabaseService`
   - Implement abstract methods
   - Place in `database_service/` directory

2. **Update Factory**
   - Add import statement
   - Add conditional branch in `get_database_service()`
   - Add validation logic

3. **Update Configuration**
   - Add settings to `Settings` class
   - Document required environment variables

4. **Write Tests**
   - Unit tests for implementation
   - Integration tests with API

See [Implementing a New Database](implementing-new-database.md) for detailed guide.

### Adding New Methods

If you need to add new database operations:

1. Add abstract method to `DatabaseService` base class
2. Implement in all concrete implementations
3. Update tests to cover new functionality

**Example:**

```python
# base.py
@abc.abstractmethod
def query(self, db_name: str, filter: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Query documents matching filter criteria."""
    pass
```

## Error Handling Strategy

### Consistent HTTP Exceptions

All implementations use FastAPI's `HTTPException` for errors:

```python
from fastapi import HTTPException

# Document not found
raise HTTPException(status_code=404, detail="Document not found")

# Conflict (CouchDB)
raise HTTPException(status_code=409, detail="Document conflict")

# Internal errors
raise HTTPException(status_code=500, detail="Database error")
```

### Error Translation

Each implementation translates database-specific errors to HTTP exceptions:

```python
try:
    # Database operation
    result = db_client.get(doc_id)
except DatabaseNotFoundError:
    raise HTTPException(status_code=404, detail="Document not found")
except DatabaseConflictError:
    raise HTTPException(status_code=409, detail="Conflict")
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

## Performance Considerations

### Connection Management

- **Singleton Pattern**: Single connection per application instance
- **Connection Pooling**: Some implementations use connection pools internally
- **Lazy Initialization**: Connections created on first use

### Caching

- **Settings Cache**: Configuration cached via `@lru_cache`
- **Table/Collection Cache**: DynamoDB caches table objects
- **Document Cache**: Not implemented (can be added at application level)

### Concurrency

- **Thread Safety**: Implementations must be thread-safe
- **Async Support**: Currently synchronous (async can be added)
- **Connection Pools**: Used by CouchDB and DynamoDB clients

## Testing Architecture

### Test Structure

```
tests/unit/services/
├── test_database_service_base.py       # Abstract interface tests
├── test_memory_database_service.py     # Memory implementation tests
├── test_couchdb_service.py             # CouchDB tests (with mocks)
├── test_firestore_service.py           # Firestore tests (with mocks)
└── test_dynamodb_service.py            # DynamoDB tests (with mocks)
```

### Test Strategies

1. **Unit Tests**: Test each implementation in isolation
2. **Interface Tests**: Verify all implementations follow the contract
3. **Integration Tests**: Test with actual database instances
4. **Mocking**: Use mocks for external dependencies in unit tests

See [Testing Guide](testing.md) for details.

## Security Architecture

### Authentication Flow

```
Application
    ↓
Database Service
    ↓
[Authentication Layer]
    ├─ CouchDB: HTTP Basic Auth
    ├─ Firestore: Service Account Key
    ├─ DynamoDB: AWS Credentials (IAM)
    └─ Memory: None (local only)
    ↓
Database
```

### Credential Management

- **Environment Variables**: Primary method
- **Secret Managers**: Supported via env var injection
- **IAM Roles**: Used for DynamoDB in AWS environments
- **Service Accounts**: Used for Firestore in GCP

See [Security Guide](security.md) for best practices.

## Monitoring and Observability

### Logging

The database service can integrate with application logging:

```python
import logging

logger = logging.getLogger(__name__)

class CouchDBService(DatabaseService):
    def get(self, db_name: str, doc_id: str):
        logger.info(f"Retrieving document {doc_id} from {db_name}")
        # ... implementation
```

### Metrics

Key metrics to monitor:

- Request latency per operation
- Error rates per operation type
- Connection pool utilization
- Database-specific metrics (throughput, storage, costs)

### Tracing

Can integrate with distributed tracing systems:

- OpenTelemetry
- AWS X-Ray (for DynamoDB)
- Google Cloud Trace (for Firestore)

## Design Decisions

### Why Synchronous?

The current implementation is synchronous rather than async:

**Rationale:**
- Simpler implementation
- Many database clients don't support async
- FastAPI can run sync functions in thread pool
- Can be migrated to async incrementally

**Future Consideration:**
- Async implementations can be added alongside sync
- Would require async versions of abstract methods

### Why No Query Interface?

The service only provides key-value operations (get/save/delete/list_all):

**Rationale:**
- Different databases have vastly different query capabilities
- Hard to create unified query interface
- Application-level filtering is simpler for small datasets
- Can add database-specific query methods if needed

**Current Approach:**
- Use `list_all()` and filter in application code
- For large datasets, implement database-specific query methods

### Why Document ID as Parameter?

The `save()` method takes `doc_id` as a separate parameter:

**Rationale:**
- Makes ID management explicit
- Some databases don't auto-generate IDs
- Application controls ID generation (UUIDs)
- Clearer API contract

## Related Documentation

- [Database Interface](interface.md) - Detailed method specifications
- [Configuration](configuration.md) - Setup and environment variables
- [Implementing a New Database](implementing-new-database.md) - Extension guide

---

**Last Updated**: 2026-01-11
