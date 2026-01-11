# Implementing a New Database

This guide provides step-by-step instructions for adding a new database backend to Gofannon.

## Overview

To add a new database backend, you need to:

1. Create an implementation file
2. Implement the DatabaseService interface
3. Add configuration settings
4. Update the factory function
5. Add dependencies
6. Write unit tests
7. Add Docker support (optional)
8. Update documentation
9. Test integration

## Step 1: Create Implementation File

Create a new Python file in the database service directory:

```bash
touch webapp/packages/api/user-service/services/database_service/mynewdb.py
```

## Step 2: Implement the Interface

Implement all four abstract methods from `DatabaseService`:

```python
"""
MyNewDB database service implementation.
"""
from typing import Any, Dict, List
from fastapi import HTTPException
from .base import DatabaseService


class MyNewDBService(DatabaseService):
    """Database service implementation for MyNewDB."""

    def __init__(self, connection_string: str, **options):
        """
        Initialize the MyNewDB connection.

        Args:
            connection_string: Database connection string
            **options: Additional database-specific options
        """
        # Initialize your database connection here
        self.connection_string = connection_string
        self.options = options
        self.client = None  # Your database client

        # Example connection logic:
        # self.client = mynewdb.connect(connection_string, **options)

    def _ensure_collection_exists(self, db_name: str):
        """
        Ensure the collection/table exists.
        Create it if it doesn't exist (if your database requires this).
        """
        # Example:
        # if not self.client.collection_exists(db_name):
        #     self.client.create_collection(db_name)
        pass

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        """
        Retrieve a document by ID.

        Args:
            db_name: Collection/table name
            doc_id: Document identifier

        Returns:
            Document as dictionary

        Raises:
            HTTPException(404): If document not found
        """
        try:
            # Example implementation:
            # collection = self.client.collection(db_name)
            # doc = collection.find_one({"_id": doc_id})
            # if doc is None:
            #     raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
            # return doc

            raise NotImplementedError("Implement document retrieval")

        except Exception as e:
            # Handle database-specific exceptions
            if "not found" in str(e).lower():
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save (create or update) a document.

        Args:
            db_name: Collection/table name
            doc_id: Document identifier
            doc: Document data

        Returns:
            Dictionary with {"id": doc_id, "rev": revision_id}
        """
        try:
            # Ensure collection exists (if needed)
            self._ensure_collection_exists(db_name)

            # Add document ID to the document
            doc["_id"] = doc_id

            # Example implementation:
            # collection = self.client.collection(db_name)
            # result = collection.replace_one(
            #     {"_id": doc_id},
            #     doc,
            #     upsert=True  # Create if doesn't exist
            # )
            #
            # # Get revision/version info if your database supports it
            # rev = result.get("revision") or "v1"
            #
            # return {"id": doc_id, "rev": rev}

            raise NotImplementedError("Implement document save")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save document: {str(e)}")

    def delete(self, db_name: str, doc_id: str) -> None:
        """
        Delete a document by ID.

        Args:
            db_name: Collection/table name
            doc_id: Document identifier

        Raises:
            HTTPException(404): If document not found
        """
        try:
            # Example implementation:
            # collection = self.client.collection(db_name)
            # result = collection.delete_one({"_id": doc_id})
            #
            # if result.deleted_count == 0:
            #     raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

            raise NotImplementedError("Implement document deletion")

        except HTTPException:
            raise  # Re-raise HTTPException
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        """
        List all documents in a collection.

        Args:
            db_name: Collection/table name

        Returns:
            List of documents
        """
        try:
            # Example implementation:
            # collection = self.client.collection(db_name)
            # documents = list(collection.find({}))
            # return documents

            # If collection doesn't exist, return empty list
            # try:
            #     self._ensure_collection_exists(db_name)
            # except:
            #     return []

            raise NotImplementedError("Implement list all documents")

        except Exception as e:
            # Some databases may not have the collection yet
            return []
```

## Step 3: Add Configuration Settings

Update [config/__init__.py](../../webapp/packages/api/user-service/config/__init__.py) to include your database settings:

```python
class Settings:
    # Existing settings...

    # MyNewDB configuration
    MYNEWDB_CONNECTION_STRING: str | None = os.getenv("MYNEWDB_CONNECTION_STRING")
    MYNEWDB_DATABASE: str = os.getenv("MYNEWDB_DATABASE", "gofannon")
    MYNEWDB_OPTION_1: str | None = os.getenv("MYNEWDB_OPTION_1")
    # Add other configuration options as needed
```

## Step 4: Update Factory Function

Update [__init__.py](../../webapp/packages/api/user-service/services/database_service/__init__.py) to include your implementation:

```python
from .mynewdb import MyNewDBService

def get_database_service(settings) -> DatabaseService:
    """Factory function to get the appropriate database service instance."""
    global _db_instance

    if _db_instance is not None:
        return _db_instance

    provider = settings.DATABASE_PROVIDER.lower()

    # Existing implementations...

    elif provider == "mynewdb":
        # Validate required configuration
        if not settings.MYNEWDB_CONNECTION_STRING:
            raise ValueError("MyNewDB requires MYNEWDB_CONNECTION_STRING")

        _db_instance = MyNewDBService(
            connection_string=settings.MYNEWDB_CONNECTION_STRING,
            database=settings.MYNEWDB_DATABASE,
            option_1=settings.MYNEWDB_OPTION_1
        )

    else:
        # Default to memory
        _db_instance = MemoryDatabaseService()

    return _db_instance
```

## Step 5: Add Dependencies

If your database requires additional Python packages, update the requirements:

```bash
# Add to webapp/packages/api/user-service/requirements.txt
mynewdb-client>=1.0.0
```

Or in `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing dependencies
    "mynewdb-client>=1.0.0",
]
```

## Step 6: Write Unit Tests

Create comprehensive tests following the pattern in [test_memory_database_service.py](../../webapp/packages/api/user-service/tests/unit/services/test_memory_database_service.py):

```python
"""
Unit tests for MyNewDB database service implementation.
"""
import pytest
from fastapi import HTTPException
from services.database_service.mynewdb import MyNewDBService


@pytest.fixture
def db_service():
    """Create a MyNewDB service instance for testing."""
    service = MyNewDBService(
        connection_string="test://localhost:1234/testdb"
    )
    yield service
    # Cleanup after tests
    service.client.close()


class TestMyNewDBService:
    """Test suite for MyNewDB database service."""

    def test_save_and_get(self, db_service):
        """Test saving and retrieving a document."""
        doc = {"name": "Test Agent", "value": 42}

        # Save document
        result = db_service.save("agents", "test-id", doc)
        assert result["id"] == "test-id"
        assert "rev" in result

        # Retrieve document
        retrieved = db_service.get("agents", "test-id")
        assert retrieved["_id"] == "test-id"
        assert retrieved["name"] == "Test Agent"
        assert retrieved["value"] == 42

    def test_get_nonexistent_document(self, db_service):
        """Test retrieving a document that doesn't exist."""
        with pytest.raises(HTTPException) as exc_info:
            db_service.get("agents", "nonexistent-id")
        assert exc_info.value.status_code == 404

    def test_update_document(self, db_service):
        """Test updating an existing document."""
        # Create initial document
        doc = {"name": "Original", "value": 1}
        db_service.save("agents", "test-id", doc)

        # Update document
        updated_doc = {"name": "Updated", "value": 2}
        result = db_service.save("agents", "test-id", updated_doc)
        assert result["id"] == "test-id"

        # Verify update
        retrieved = db_service.get("agents", "test-id")
        assert retrieved["name"] == "Updated"
        assert retrieved["value"] == 2

    def test_delete(self, db_service):
        """Test deleting a document."""
        # Create document
        doc = {"name": "To Delete"}
        db_service.save("agents", "test-id", doc)

        # Delete document
        db_service.delete("agents", "test-id")

        # Verify deletion
        with pytest.raises(HTTPException) as exc_info:
            db_service.get("agents", "test-id")
        assert exc_info.value.status_code == 404

    def test_delete_nonexistent_document(self, db_service):
        """Test deleting a document that doesn't exist."""
        with pytest.raises(HTTPException) as exc_info:
            db_service.delete("agents", "nonexistent-id")
        assert exc_info.value.status_code == 404

    def test_list_all(self, db_service):
        """Test listing all documents in a collection."""
        # Create multiple documents
        db_service.save("agents", "id-1", {"name": "Agent 1"})
        db_service.save("agents", "id-2", {"name": "Agent 2"})
        db_service.save("agents", "id-3", {"name": "Agent 3"})

        # List all documents
        documents = db_service.list_all("agents")
        assert len(documents) == 3

        # Verify all documents are present
        ids = {doc["_id"] for doc in documents}
        assert ids == {"id-1", "id-2", "id-3"}

    def test_list_all_empty_collection(self, db_service):
        """Test listing documents from an empty collection."""
        documents = db_service.list_all("empty-collection")
        assert documents == []

    def test_multiple_collections(self, db_service):
        """Test that collections are isolated from each other."""
        # Save to different collections
        db_service.save("agents", "id-1", {"type": "agent"})
        db_service.save("users", "id-1", {"type": "user"})

        # Verify isolation
        agent = db_service.get("agents", "id-1")
        user = db_service.get("users", "id-1")

        assert agent["type"] == "agent"
        assert user["type"] == "user"
```

Run tests:
```bash
cd webapp/packages/api/user-service
pytest tests/unit/services/test_mynewdb_database_service.py -v
```

## Step 7: Add Docker Support (Optional)

If your database requires a service, add it to [docker-compose.yml](../../webapp/infra/docker/docker-compose.yml):

```yaml
services:
  mynewdb:
    image: mynewdb:latest
    container_name: gofannon-mynewdb
    ports:
      - "9999:9999"  # Adjust port as needed
    environment:
      - MYNEWDB_USER=${MYNEWDB_USER:-admin}
      - MYNEWDB_PASSWORD=${MYNEWDB_PASSWORD:-password}
    volumes:
      - mynewdb-data:/var/lib/mynewdb/data
    healthcheck:
      test: ["CMD", "mynewdb-healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mynewdb-data:
```

## Step 8: Update Documentation

Add your database to this documentation:

1. Add a new section under "Existing Database Implementations"
2. Document configuration requirements
3. Add any special considerations
4. Provide setup instructions

## Step 9: Integration Testing

Test your implementation with the full application:

```bash
# Set environment variables
export DATABASE_PROVIDER=mynewdb
export MYNEWDB_CONNECTION_STRING=mynewdb://localhost:9999/gofannon

# Start the application
cd webapp/packages/api/user-service
uvicorn main:app --reload

# Test API endpoints
curl http://localhost:8000/agents
```

## Common Implementation Patterns

### Pattern 1: Auto-Create Collections

Some databases require explicit collection creation:

```python
def _ensure_collection_exists(self, db_name: str):
    """Create collection if it doesn't exist."""
    if not self.client.collection_exists(db_name):
        self.client.create_collection(db_name)
        # Add indexes if needed
        self.client.create_index(db_name, "_id", unique=True)
```

### Pattern 2: Connection Pooling

For production use, implement connection pooling:

```python
def __init__(self, connection_string: str, pool_size: int = 10):
    self.pool = mynewdb.ConnectionPool(
        connection_string,
        max_connections=pool_size,
        min_connections=2
    )

def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
    with self.pool.get_connection() as conn:
        # Use connection
        return conn.get(db_name, doc_id)
```

### Pattern 3: Type Conversion

Handle database-specific type requirements:

```python
def _prepare_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Python types to database-compatible types."""
    prepared = {}
    for key, value in doc.items():
        if isinstance(value, datetime):
            prepared[key] = value.isoformat()
        elif isinstance(value, Decimal):
            prepared[key] = float(value)
        else:
            prepared[key] = value
    return prepared
```

### Pattern 4: Error Mapping

Map database-specific exceptions to HTTP exceptions:

```python
def _handle_error(self, error: Exception, operation: str) -> HTTPException:
    """Map database errors to HTTP exceptions."""
    error_str = str(error).lower()

    if "not found" in error_str or "does not exist" in error_str:
        return HTTPException(status_code=404, detail=f"{operation} failed: not found")

    if "conflict" in error_str or "already exists" in error_str:
        return HTTPException(status_code=409, detail=f"{operation} failed: conflict")

    if "permission" in error_str or "unauthorized" in error_str:
        return HTTPException(status_code=403, detail=f"{operation} failed: permission denied")

    return HTTPException(status_code=500, detail=f"{operation} failed: {str(error)}")
```

## Implementation Checklist

- [ ] Create implementation file in `database_service/`
- [ ] Implement all abstract methods from `DatabaseService`
- [ ] Handle document ID storage (`_id` field)
- [ ] Return proper format from `save()` method
- [ ] Raise `HTTPException(404)` for missing documents
- [ ] Add configuration settings to `config/__init__.py`
- [ ] Update factory function in `__init__.py`
- [ ] Add dependencies to `requirements.txt`
- [ ] Write comprehensive unit tests
- [ ] Test with actual database instance
- [ ] Add Docker Compose service (if applicable)
- [ ] Update this documentation
- [ ] Test integration with API endpoints
- [ ] Verify all six collections work correctly
- [ ] Test error handling and edge cases
- [ ] Document any special considerations

## Example: Complete PostgreSQL Implementation

See the appendix in the main [database-service.md](../database-service.md) for a complete PostgreSQL implementation example.

## Related Documentation

- [Database Interface](interface.md) - Abstract base class and method specifications
- [Configuration](configuration.md) - Database provider configuration
- [Schema](schema.md) - Collection and document schemas
- [Testing](testing.md) - Testing strategies
- [Database Service README](README.md) - Overview

---

Last Updated: 2026-01-11
