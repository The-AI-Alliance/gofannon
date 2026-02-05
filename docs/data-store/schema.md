# Data Store Schema

## Collection

The data store uses a dedicated collection/database:

| Collection Name | Purpose | Primary Key |
|-----------------|---------|-------------|
| `agent_data_store` | Agent-accessible key-value storage | `_id` (composite) |

## Document ID Structure

Document IDs are constructed as:

```
{user_id}:{namespace}:{base64_encoded_key}
```

**Components:**
- `user_id`: The owner's user ID (e.g., `user_google_123456789`)
- `namespace`: The logical namespace (e.g., `default`, `files:my-repo`)
- `base64_encoded_key`: URL-safe base64 encoding of the original key

**Example:**
```
user_google_123456789:files:my-repo:c3JjL21haW4ucHk=
                                    ^-- base64("src/main.py")
```

The base64 encoding ensures keys with special characters (slashes, colons, etc.) are safe for document IDs.

## Document Schema

### Data Store Entry

```python
{
    "_id": "user_123:default:bXkta2V5",      # Composite ID
    "_rev": "1-abc123def456",                 # CouchDB revision (if using CouchDB)
    
    # Identity fields
    "userId": "user_123",                     # Owner's user ID
    "namespace": "default",                   # Namespace name
    "key": "my-key",                          # Original key (decoded)
    
    # Data fields
    "value": {                                # Any JSON-serializable data
        "result": "analysis complete",
        "score": 95,
        "items": ["a", "b", "c"]
    },
    "metadata": {                             # Optional user-provided metadata
        "version": "1.0",
        "source": "analyzer-agent"
    },
    
    # Agent tracking
    "createdByAgent": "data-processor",       # Agent that created this entry
    "lastAccessedByAgent": "report-generator", # Last agent to read/write
    "accessCount": 5,                         # Total number of accesses
    
    # Timestamps (ISO 8601 format)
    "createdAt": "2026-02-01T10:30:00Z",
    "updatedAt": "2026-02-05T14:22:00Z",
    "lastAccessedAt": "2026-02-05T14:22:00Z"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | string | Yes | Composite document ID |
| `userId` | string | Yes | Owner's user ID |
| `namespace` | string | Yes | Namespace (default: `"default"`) |
| `key` | string | Yes | Original key name |
| `value` | any | Yes | Stored data (JSON-serializable) |
| `metadata` | object | No | User-provided metadata |
| `createdByAgent` | string | No | Agent that created this entry |
| `lastAccessedByAgent` | string | No | Last agent to access this entry |
| `accessCount` | integer | No | Number of times accessed |
| `createdAt` | string | Yes | ISO 8601 creation timestamp |
| `updatedAt` | string | Yes | ISO 8601 last update timestamp |
| `lastAccessedAt` | string | No | ISO 8601 last access timestamp |

### Value Field

The `value` field accepts any JSON-serializable data:

```python
# Primitives
"value": "string value"
"value": 42
"value": 3.14
"value": true
"value": null

# Arrays
"value": [1, 2, 3, "mixed", {"nested": "object"}]

# Objects
"value": {
    "nested": {
        "deeply": {
            "data": [1, 2, 3]
        }
    }
}
```

**Limitations:**
- Maximum recommended size: 1MB
- No binary data (use base64 encoding if needed)
- No circular references
- No custom class instances (use dicts)

### Metadata Field

The `metadata` field stores user-provided context:

```python
"metadata": {
    "version": "1.0",
    "format": "json",
    "source_url": "https://api.example.com/data",
    "processed_by": ["agent-a", "agent-b"],
    "tags": ["important", "quarterly"],
    "custom_field": "any_value"
}
```

Metadata is merged on updates—new fields are added, existing fields are overwritten:

```python
# Original metadata
{"version": "1.0", "author": "alice"}

# Update with
{"version": "2.0", "reviewer": "bob"}

# Result
{"version": "2.0", "author": "alice", "reviewer": "bob"}
```

## Indexes

For optimal query performance, create these indexes:

### CouchDB Design Document

```json
{
    "_id": "_design/data_store",
    "views": {
        "by_user_namespace": {
            "map": "function(doc) { if (doc.userId && doc.namespace) { emit([doc.userId, doc.namespace], null); } }"
        },
        "by_user": {
            "map": "function(doc) { if (doc.userId) { emit(doc.userId, doc.namespace); } }"
        }
    }
}
```

### DynamoDB

| Index Type | Partition Key | Sort Key | Purpose |
|------------|---------------|----------|---------|
| Primary | `_id` | - | Direct document access |
| GSI | `userId` | `namespace` | List keys in namespace |

### Firestore

```
Collection: agent_data_store
  Document ID: {composite_id}
  
Composite Index:
  - userId (Ascending)
  - namespace (Ascending)
```

## Query Patterns

### List Keys in Namespace

```python
# Pseudocode for list_keys(user_id, namespace)
SELECT key FROM agent_data_store
WHERE userId = {user_id} AND namespace = {namespace}
```

### List Namespaces

```python
# Pseudocode for list_namespaces(user_id)
SELECT DISTINCT namespace FROM agent_data_store
WHERE userId = {user_id}
```

### Get Document

```python
# Pseudocode for get(user_id, namespace, key)
doc_id = f"{user_id}:{namespace}:{base64_encode(key)}"
SELECT * FROM agent_data_store WHERE _id = {doc_id}
```

## Migration Considerations

When migrating data between database backends:

1. **Document IDs**: Preserve the composite ID format
2. **Timestamps**: Ensure ISO 8601 format consistency
3. **Metadata merging**: Test that metadata merge logic matches
4. **Access tracking**: `accessCount` may need recalculation

## Example Documents

### Simple String Value

```json
{
    "_id": "user_123:default:Z3JlZXRpbmc=",
    "userId": "user_123",
    "namespace": "default",
    "key": "greeting",
    "value": "Hello, World!",
    "createdByAgent": "hello-agent",
    "accessCount": 1,
    "createdAt": "2026-02-05T10:00:00Z",
    "updatedAt": "2026-02-05T10:00:00Z"
}
```

### File Analysis Result

```json
{
    "_id": "user_123:files:my-repo:c3JjL21haW4ucHk=",
    "userId": "user_123",
    "namespace": "files:my-repo",
    "key": "src/main.py",
    "value": {
        "content": "def main():\n    print('Hello')\n",
        "lines": 2,
        "language": "python",
        "functions": ["main"]
    },
    "metadata": {
        "indexed_at": "2026-02-05T09:00:00Z",
        "file_size": 42,
        "sha256": "abc123..."
    },
    "createdByAgent": "repo-indexer",
    "lastAccessedByAgent": "code-searcher",
    "accessCount": 15,
    "createdAt": "2026-02-05T09:00:00Z",
    "updatedAt": "2026-02-05T09:00:00Z",
    "lastAccessedAt": "2026-02-05T14:30:00Z"
}
```

### Cached API Response

```json
{
    "_id": "user_123:cache:github:cmVwb3M=",
    "userId": "user_123",
    "namespace": "cache:github",
    "key": "repos",
    "value": [
        {"name": "repo-a", "stars": 100},
        {"name": "repo-b", "stars": 50}
    ],
    "metadata": {
        "cached_at": "2026-02-05T12:00:00Z",
        "ttl_seconds": 3600,
        "api_endpoint": "/user/repos"
    },
    "createdByAgent": "github-fetcher",
    "accessCount": 3,
    "createdAt": "2026-02-05T12:00:00Z",
    "updatedAt": "2026-02-05T12:00:00Z"
}
```

## Related Documentation

- [API Reference](api.md) - Method specifications
- [Database Service Schema](../database-service/schema.md) - Other collection schemas
- [Implementing New Database](../database-service/implementing-new-database.md) - Adding database support