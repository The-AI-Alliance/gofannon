# Testing

## Unit Tests

Unit tests are located in:
```
webapp/packages/api/user-service/tests/unit/services/
├── test_database_service_base.py       # Abstract interface tests
└── test_memory_database_service.py     # Memory implementation tests
```

### Running Unit Tests

```bash
cd webapp/packages/api/user-service

# Run all database tests
pytest tests/unit/services/test_*database*.py -v

# Run specific test file
pytest tests/unit/services/test_memory_database_service.py -v

# Run specific test
pytest tests/unit/services/test_memory_database_service.py::TestMemoryDatabaseService::test_save_and_get -v

# Run with coverage
pytest tests/unit/services/ --cov=services/database_service --cov-report=html
```

### Test Structure

Tests validate:

1. **CRUD Operations**:
   - Creating documents with `save()`
   - Reading documents with `get()`
   - Updating documents with `save()`
   - Deleting documents with `delete()`

2. **Error Handling**:
   - 404 errors for missing documents
   - Conflict handling (if applicable)
   - Invalid input handling

3. **Collection Operations**:
   - Listing all documents with `list_all()`
   - Collection isolation
   - Empty collection handling

4. **Edge Cases**:
   - Updating non-existent documents
   - Deleting non-existent documents
   - Special characters in IDs
   - Large documents

### Example Test

```python
def test_save_and_get(db_service):
    """Test saving and retrieving a document."""
    doc = {"name": "Test Agent", "description": "A test agent"}

    # Save document
    result = db_service.save("agents", "test-id", doc)
    assert result["id"] == "test-id"
    assert "rev" in result

    # Retrieve document
    retrieved = db_service.get("agents", "test-id")
    assert retrieved["_id"] == "test-id"
    assert retrieved["name"] == "Test Agent"
```

## Integration Tests

Integration tests verify the database service works with the full API:

```bash
# Start the application with your database
export DATABASE_PROVIDER=couchdb
uvicorn main:app --reload

# In another terminal, run integration tests
pytest tests/integration/ -v
```

## Manual Testing

Use the API endpoints to test database operations:

```bash
# Create an agent
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Agent", "code": "print(\"hello\")"}'

# Get the agent
curl http://localhost:8000/agents/{agent_id}

# Update the agent
curl -X PUT http://localhost:8000/agents/{agent_id} \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Agent", "code": "print(\"updated\")"}'

# Delete the agent
curl -X DELETE http://localhost:8000/agents/{agent_id}

# List all agents
curl http://localhost:8000/agents
```

## Testing Different Database Providers

### Memory Database

```bash
# Set provider
export DATABASE_PROVIDER=memory

# Run tests
pytest tests/unit/services/test_memory_database_service.py -v
```

### CouchDB

```bash
# Start CouchDB
docker run -d -p 5984:5984 \
  -e COUCHDB_USER=admin \
  -e COUCHDB_PASSWORD=password \
  couchdb:latest

# Set provider
export DATABASE_PROVIDER=couchdb
export COUCHDB_URL=http://localhost:5984
export COUCHDB_USER=admin
export COUCHDB_PASSWORD=password

# Run tests
pytest tests/unit/services/test_couchdb_database_service.py -v
```

### Firestore

```bash
# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Set provider
export DATABASE_PROVIDER=firestore

# Run tests
pytest tests/unit/services/test_firestore_database_service.py -v
```

### DynamoDB

```bash
# Start DynamoDB Local
docker run -d -p 8000:8000 amazon/dynamodb-local

# Set provider
export DATABASE_PROVIDER=dynamodb
export DYNAMODB_REGION=us-east-1
export DYNAMODB_ENDPOINT_URL=http://localhost:8000

# Run tests
pytest tests/unit/services/test_dynamodb_database_service.py -v
```

## Test Fixtures

### Memory Database Fixture

```python
import pytest
from services.database_service.memory import MemoryDatabaseService

@pytest.fixture
def db_service():
    """Create a fresh memory database for each test."""
    return MemoryDatabaseService()

def test_example(db_service):
    # Test uses fresh database
    db_service.save("agents", "test-id", {"name": "Test"})
    assert db_service.get("agents", "test-id")["name"] == "Test"
```

### CouchDB Fixture

```python
import pytest
from services.database_service.couchdb import CouchDBService

@pytest.fixture
def db_service():
    """Create a CouchDB service with cleanup."""
    service = CouchDBService(
        url="http://localhost:5984",
        username="admin",
        password="password"
    )
    yield service

    # Cleanup: Delete test databases
    for db_name in ["agents", "users", "sessions"]:
        if db_name in service.couch:
            service.couch.delete(db_name)
```

### Firestore Fixture

```python
import pytest
from services.database_service.firestore import FirestoreService

@pytest.fixture
def db_service():
    """Create a Firestore service with cleanup."""
    service = FirestoreService()
    yield service

    # Cleanup: Delete test collections
    for collection in ["agents", "users", "sessions"]:
        docs = service.db.collection(collection).stream()
        for doc in docs:
            doc.reference.delete()
```

### DynamoDB Fixture

```python
import pytest
from services.database_service.dynamodb import DynamoDBService

@pytest.fixture
def db_service():
    """Create a DynamoDB service with cleanup."""
    service = DynamoDBService(
        region_name="us-east-1",
        endpoint_url="http://localhost:8000"
    )
    yield service

    # Cleanup: Delete test tables
    for table_name in ["agents", "users", "sessions"]:
        if table_name in service.tables:
            service.tables[table_name].delete()
```

## Test Coverage

Generate coverage reports:

```bash
# Run tests with coverage
pytest tests/unit/services/ \
  --cov=services/database_service \
  --cov-report=html \
  --cov-report=term

# View HTML report
open htmlcov/index.html
```

Target coverage goals:
- **Line Coverage**: > 90%
- **Branch Coverage**: > 80%
- **Critical paths**: 100%

## Performance Testing

Test performance with large datasets:

```python
import pytest
import time

def test_bulk_insert_performance(db_service):
    """Test performance of bulk inserts."""
    start = time.time()

    for i in range(1000):
        db_service.save("agents", f"agent-{i}", {"name": f"Agent {i}"})

    elapsed = time.time() - start
    print(f"Inserted 1000 documents in {elapsed:.2f} seconds")

    # Assert reasonable performance
    assert elapsed < 10.0  # Should complete in under 10 seconds

def test_list_all_performance(db_service):
    """Test performance of listing large collections."""
    # Insert test data
    for i in range(1000):
        db_service.save("agents", f"agent-{i}", {"name": f"Agent {i}"})

    start = time.time()
    documents = db_service.list_all("agents")
    elapsed = time.time() - start

    print(f"Listed {len(documents)} documents in {elapsed:.2f} seconds")
    assert len(documents) == 1000
    assert elapsed < 5.0  # Should complete in under 5 seconds
```

## Load Testing

Use tools like Locust for load testing:

```python
# locustfile.py
from locust import HttpUser, task, between

class DatabaseServiceUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_agent(self):
        self.client.get("/agents/agent-1")

    @task(3)
    def list_agents(self):
        self.client.get("/agents")

    @task
    def create_agent(self):
        self.client.post("/agents", json={
            "name": "Test Agent",
            "code": "print('hello')"
        })
```

Run load test:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test Database Service

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      couchdb:
        image: couchdb:latest
        ports:
          - 5984:5984
        env:
          COUCHDB_USER: admin
          COUCHDB_PASSWORD: password

      dynamodb:
        image: amazon/dynamodb-local
        ports:
          - 8000:8000

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          cd webapp/packages/api/user-service
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Test Memory Database
        run: |
          cd webapp/packages/api/user-service
          export DATABASE_PROVIDER=memory
          pytest tests/unit/services/test_memory_database_service.py -v

      - name: Test CouchDB
        run: |
          cd webapp/packages/api/user-service
          export DATABASE_PROVIDER=couchdb
          export COUCHDB_URL=http://localhost:5984
          export COUCHDB_USER=admin
          export COUCHDB_PASSWORD=password
          pytest tests/unit/services/test_couchdb_database_service.py -v

      - name: Test DynamoDB
        run: |
          cd webapp/packages/api/user-service
          export DATABASE_PROVIDER=dynamodb
          export DYNAMODB_REGION=us-east-1
          export DYNAMODB_ENDPOINT_URL=http://localhost:8000
          pytest tests/unit/services/test_dynamodb_database_service.py -v

      - name: Generate Coverage Report
        run: |
          cd webapp/packages/api/user-service
          pytest tests/unit/services/ \
            --cov=services/database_service \
            --cov-report=xml

      - name: Upload Coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

## Testing Best Practices

1. **Use Test Fixtures**: Create reusable test database instances
2. **Isolate Tests**: Each test should clean up after itself
3. **Test Error Paths**: Verify proper exception handling
4. **Mock External Services**: Don't require real database connections for unit tests (when appropriate)
5. **Test Concurrency**: Verify thread-safety if applicable
6. **Performance Tests**: Ensure operations complete in reasonable time
7. **Integration Tests**: Test with actual database instances in CI/CD
8. **Document Tests**: Add docstrings explaining what each test validates
9. **Use Descriptive Names**: Test names should clearly indicate what they test
10. **Test Edge Cases**: Empty collections, special characters, large documents, etc.

## Common Test Patterns

### Testing Document Updates

```python
def test_document_update(db_service):
    """Test that document updates preserve ID and update content."""
    # Create initial document
    doc = {"name": "Original", "value": 1}
    db_service.save("agents", "test-id", doc)

    # Update document
    updated_doc = {"name": "Updated", "value": 2}
    db_service.save("agents", "test-id", updated_doc)

    # Verify update
    retrieved = db_service.get("agents", "test-id")
    assert retrieved["_id"] == "test-id"
    assert retrieved["name"] == "Updated"
    assert retrieved["value"] == 2
```

### Testing Error Cases

```python
def test_get_nonexistent(db_service):
    """Test that getting a non-existent document raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        db_service.get("agents", "nonexistent-id")
    assert exc_info.value.status_code == 404

def test_delete_nonexistent(db_service):
    """Test that deleting a non-existent document raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        db_service.delete("agents", "nonexistent-id")
    assert exc_info.value.status_code == 404
```

### Testing Collection Isolation

```python
def test_collection_isolation(db_service):
    """Test that different collections don't interfere with each other."""
    # Same ID in different collections
    db_service.save("agents", "id-1", {"type": "agent"})
    db_service.save("users", "id-1", {"type": "user"})

    # Verify they're separate
    agent = db_service.get("agents", "id-1")
    user = db_service.get("users", "id-1")

    assert agent["type"] == "agent"
    assert user["type"] == "user"
```

## Related Documentation

- [Database Interface](interface.md) - Abstract base class and method specifications
- [Implementing New Database](implementing-new-database.md) - Guide for adding new databases
- [Configuration](configuration.md) - Database provider configuration
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Database Service README](README.md) - Overview

---

Last Updated: 2026-01-11
