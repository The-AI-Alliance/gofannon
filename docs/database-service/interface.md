# Database Service Interface

## Overview

All database implementations in Gofannon must inherit from the `DatabaseService` abstract base class and implement four core methods. This document provides detailed specifications for the interface.

## Abstract Base Class

**Location:** [base.py](../../webapp/packages/api/user-service/services/database_service/base.py)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class DatabaseService(ABC):
    """Abstract base class for a generic database service."""

    @abstractmethod
    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        """Retrieve a document by ID."""
        pass

    @abstractmethod
    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Save (create or update) a document."""
        pass

    @abstractmethod
    def delete(self, db_name: str, doc_id: str) -> None:
        """Delete a document by ID."""
        pass

    @abstractmethod
    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        """List all documents in a database/collection."""
        pass
```

## Method Specifications

### get()

Retrieve a single document by its identifier.

**Signature:**
```python
def get(self, db_name: str, doc_id: str) -> Dict[str, Any]
```

**Parameters:**
- `db_name` (str): The database/collection/table name
- `doc_id` (str): The unique document identifier

**Returns:**
- `Dict[str, Any]`: Dictionary containing the document data
- Must include `_id` field with the document ID

**Raises:**
- `HTTPException(404)`: If document does not exist

**Example:**
```python
doc = db.get("agents", "550e8400-e29b-41d4-a716-446655440000")
# Returns: {
#     "_id": "550e8400-e29b-41d4-a716-446655440000",
#     "name": "MyAgent",
#     "description": "...",
#     ...
# }
```

**Implementation Requirements:**
1. Check if document exists
2. If not found, raise `HTTPException(status_code=404, detail="Document not found")`
3. Add `_id` field to returned document
4. Return document as dictionary

**Error Handling:**
```python
from fastapi import HTTPException

def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
    doc = self._fetch_from_database(db_name, doc_id)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {doc_id} not found in {db_name}"
        )
    doc["_id"] = doc_id
    return doc
```

---

### save()

Create a new document or update an existing document.

**Signature:**
```python
def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]
```

**Parameters:**
- `db_name` (str): The database/collection/table name
- `doc_id` (str): The unique document identifier
- `doc` (Dict[str, Any]): The document data to save

**Returns:**
- `Dict[str, Any]`: Metadata about the save operation
- Must include at minimum:
  - `"id"`: The document ID (echo of `doc_id` parameter)
  - `"rev"`: Revision identifier (implementation-specific, can be placeholder)

**Raises:**
- `HTTPException(409)`: If there's a conflict (optional, for MVCC databases)
- `HTTPException(500)`: For other errors

**Example:**
```python
doc = {
    "name": "MyAgent",
    "description": "An example agent",
    "code": "def handler(event): return {}"
}
result = db.save("agents", "550e8400-e29b-41d4-a716-446655440000", doc)
# Returns: {"id": "550e8400-e29b-41d4-a716-446655440000", "rev": "1-abc123"}
```

**Implementation Requirements:**
1. Add `_id` field to document: `doc["_id"] = doc_id`
2. Create collection/table if it doesn't exist (database-specific)
3. Handle update vs. insert logic
4. For MVCC databases (like CouchDB), handle revision conflicts
5. Return dictionary with `id` and `rev` fields

**Upsert Behavior:**
The `save()` method should perform an **upsert** operation:
- If document with `doc_id` exists: Update it
- If document doesn't exist: Create it

**Example Implementation:**
```python
def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    # Add ID to document
    doc["_id"] = doc_id

    # Ensure collection exists
    self._ensure_collection_exists(db_name)

    # Perform upsert
    try:
        result = self._upsert_document(db_name, doc_id, doc)
        return {
            "id": doc_id,
            "rev": result.get("revision", "v1")
        }
    except ConflictError:
        raise HTTPException(status_code=409, detail="Document conflict")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Revision Handling (for MVCC databases):**
```python
# CouchDB example
def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]):
    db = self.couch[db_name]
    doc["_id"] = doc_id

    # Get current revision if document exists
    try:
        existing = db[doc_id]
        doc["_rev"] = existing["_rev"]  # Include current revision
    except ResourceNotFound:
        pass  # New document, no revision needed

    doc_id, rev = db.save(doc)
    return {"id": doc_id, "rev": rev}
```

---

### delete()

Delete a document by its identifier.

**Signature:**
```python
def delete(self, db_name: str, doc_id: str) -> None
```

**Parameters:**
- `db_name` (str): The database/collection/table name
- `doc_id` (str): The unique document identifier

**Returns:**
- `None`: No return value on success

**Raises:**
- `HTTPException(404)`: If document does not exist

**Example:**
```python
db.delete("agents", "550e8400-e29b-41d4-a716-446655440000")
# Returns: None (or raises 404 if not found)
```

**Implementation Requirements:**
1. Check if document exists
2. If not found, raise `HTTPException(status_code=404)`
3. Delete the document
4. Return nothing (None)

**Example Implementation:**
```python
def delete(self, db_name: str, doc_id: str) -> None:
    exists = self._document_exists(db_name, doc_id)
    if not exists:
        raise HTTPException(
            status_code=404,
            detail=f"Document {doc_id} not found"
        )

    self._delete_document(db_name, doc_id)
```

**Note on Return Value:**
Unlike `save()`, the `delete()` method returns `None`. The absence of an exception indicates success.

---

### list_all()

List all documents in a collection/table.

**Signature:**
```python
def list_all(self, db_name: str) -> List[Dict[str, Any]]
```

**Parameters:**
- `db_name` (str): The database/collection/table name

**Returns:**
- `List[Dict[str, Any]]`: List of dictionaries, each containing a document
- Each document must include its `_id` field
- Returns empty list `[]` if collection doesn't exist or is empty

**Raises:**
- Generally should not raise exceptions
- Return `[]` for non-existent collections

**Example:**
```python
docs = db.list_all("agents")
# Returns: [
#     {"_id": "id-1", "name": "Agent 1", ...},
#     {"_id": "id-2", "name": "Agent 2", ...},
#     {"_id": "id-3", "name": "Agent 3", ...}
# ]
```

**Implementation Requirements:**
1. Return empty list if collection doesn't exist
2. Return all documents in the collection
3. Each document must include `_id` field
4. Order is not guaranteed (implementation-specific)

**Example Implementation:**
```python
def list_all(self, db_name: str) -> List[Dict[str, Any]]:
    try:
        # Ensure collection exists
        if not self._collection_exists(db_name):
            return []

        # Fetch all documents
        documents = self._fetch_all_documents(db_name)

        # Ensure _id field is present in each document
        for doc in documents:
            if "_id" not in doc:
                doc["_id"] = doc.get("id") or str(uuid.uuid4())

        return documents

    except Exception:
        # For non-existent collections or other errors, return empty list
        return []
```

**Pagination Considerations:**

For large collections, consider implementing pagination internally:

```python
def list_all(self, db_name: str) -> List[Dict[str, Any]]:
    all_docs = []
    page_token = None

    while True:
        # Fetch page of documents
        page, page_token = self._fetch_page(db_name, page_token)
        all_docs.extend(page)

        if page_token is None:
            break  # No more pages

    return all_docs
```

**Performance Warning:**
`list_all()` can be expensive for large collections. Consider:
- Implementing application-level pagination
- Adding optional limit/offset parameters in future
- Warning users about large result sets

---

## Interface Conventions

### Database Name Parameter

The `db_name` parameter represents a **collection** or **table** name, not a database server or instance.

**Mapping by Implementation:**

| Implementation | `db_name` maps to |
|----------------|-------------------|
| Memory | Dictionary key namespace |
| CouchDB | Database name |
| Firestore | Collection name |
| DynamoDB | Table name |

**Example:**
```python
db.get("agents", "doc-id")  # "agents" is the collection/table
db.get("users", "doc-id")   # "users" is a different collection/table
```

### Document ID Field

All documents must include an `_id` field containing their unique identifier.

**Requirements:**
- Field name: `_id` (with underscore prefix)
- Type: `str`
- Must match the `doc_id` parameter
- Present in all returned documents

**Example:**
```python
doc = {
    "_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "MyAgent",
    # ... other fields
}
```

### Error Handling

Use FastAPI's `HTTPException` for all errors:

```python
from fastapi import HTTPException

# Document not found
raise HTTPException(status_code=404, detail="Document not found")

# Conflict (MVCC)
raise HTTPException(status_code=409, detail="Document conflict")

# General errors
raise HTTPException(status_code=500, detail="Database operation failed")
```

**Standard Status Codes:**
- `404`: Document or collection not found
- `409`: Conflict (concurrent modification)
- `500`: Internal database error

### Return Value Contracts

#### get() Returns
```python
{
    "_id": "document-id",
    "field1": "value1",
    "field2": "value2",
    # ... document fields
}
```

#### save() Returns
```python
{
    "id": "document-id",  # Echo of doc_id parameter
    "rev": "revision-id"  # Version/revision identifier
}
```

#### delete() Returns
```python
None  # No return value
```

#### list_all() Returns
```python
[
    {"_id": "id1", "field": "value"},
    {"_id": "id2", "field": "value"},
    # ... more documents
]
```

## Type Annotations

All methods should include proper type hints:

```python
from typing import Any, Dict, List

def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
    pass

def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    pass

def delete(self, db_name: str, doc_id: str) -> None:
    pass

def list_all(self, db_name: str) -> List[Dict[str, Any]]:
    pass
```

## Testing the Interface

Every implementation should pass these interface tests:

```python
def test_interface_compliance(db_service):
    """Test that implementation follows interface contract."""

    # Test save() returns correct format
    result = db_service.save("test", "id1", {"data": "value"})
    assert "id" in result
    assert "rev" in result
    assert result["id"] == "id1"

    # Test get() returns document with _id
    doc = db_service.get("test", "id1")
    assert "_id" in doc
    assert doc["_id"] == "id1"

    # Test delete() returns None
    result = db_service.delete("test", "id1")
    assert result is None

    # Test list_all() returns list
    docs = db_service.list_all("test")
    assert isinstance(docs, list)

    # Test get() raises 404 for non-existent document
    with pytest.raises(HTTPException) as exc:
        db_service.get("test", "nonexistent")
    assert exc.value.status_code == 404

    # Test delete() raises 404 for non-existent document
    with pytest.raises(HTTPException) as exc:
        db_service.delete("test", "nonexistent")
    assert exc.value.status_code == 404
```

## Usage Examples

### Creating a Document

```python
from services.database_service import get_database_service
from config import Settings

settings = Settings()
db = get_database_service(settings)

# Create a new agent
agent = {
    "name": "MyAgent",
    "description": "Example agent",
    "code": "def handler(event): return {'status': 'ok'}"
}

result = db.save("agents", "550e8400-e29b-41d4-a716-446655440000", agent)
print(f"Saved agent with revision: {result['rev']}")
```

### Retrieving a Document

```python
try:
    agent = db.get("agents", "550e8400-e29b-41d4-a716-446655440000")
    print(f"Agent name: {agent['name']}")
except HTTPException as e:
    if e.status_code == 404:
        print("Agent not found")
```

### Updating a Document

```python
# Retrieve, modify, and save
agent = db.get("agents", "550e8400-e29b-41d4-a716-446655440000")
agent["description"] = "Updated description"
db.save("agents", "550e8400-e29b-41d4-a716-446655440000", agent)
```

### Deleting a Document

```python
try:
    db.delete("agents", "550e8400-e29b-41d4-a716-446655440000")
    print("Agent deleted")
except HTTPException as e:
    if e.status_code == 404:
        print("Agent not found")
```

### Listing All Documents

```python
agents = db.list_all("agents")
print(f"Found {len(agents)} agents:")
for agent in agents:
    print(f"  - {agent['_id']}: {agent.get('name', 'Unnamed')}")
```

## Related Documentation

- [Architecture](architecture.md) - System design and patterns
- [Schema](schema.md) - Document structures and collections
- [Implementing a New Database](implementing-new-database.md) - Implementation guide

---

**Last Updated**: 2026-01-11
