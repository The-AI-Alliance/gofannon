# Data Store API Reference

Complete API documentation for the Agent Data Store.

## Overview

The data store is accessed through the `data_store` object, which is automatically available in every agent's sandbox environment. This object is an instance of `AgentDataStoreProxy`, pre-configured with the current user's ID and agent name.

## Basic Operations

### `get(key, default=None)`

Retrieve a value from the data store.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `key` | string | Yes | The key to retrieve |
| `default` | any | No | Value to return if key not found (default: `None`) |

**Returns:** The stored value, or `default` if the key doesn't exist.

**Example:**
```python
# Simple get
value = data_store.get("my-key")

# With default
config = data_store.get("config", default={"timeout": 30})

# Check existence
if data_store.get("processed-flag"):
    return {"status": "already processed"}
```

### `set(key, value, metadata=None)`

Store a value in the data store.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `key` | string | Yes | The key to store under |
| `value` | any | Yes | JSON-serializable value to store |
| `metadata` | dict | No | Optional metadata to attach |

**Returns:** `None`

**Example:**
```python
# Simple set
data_store.set("result", {"score": 95, "passed": True})

# With metadata
data_store.set("report", report_data, metadata={
    "version": "1.0",
    "generated_by": "analyzer-v2",
    "expires": "2026-03-01"
})
```

**Notes:**
- If the key exists, the value is overwritten
- Metadata is merged with existing metadata on update
- Timestamps (`createdAt`, `updatedAt`) are managed automatically

### `delete(key)`

Delete a value from the data store.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `key` | string | Yes | The key to delete |

**Returns:** `True` if deleted, `False` if key didn't exist.

**Example:**
```python
# Delete a key
deleted = data_store.delete("temporary-data")

if deleted:
    print("Cleaned up temporary data")
else:
    print("Key didn't exist")
```

### `list_keys(prefix=None)`

List all keys in the current namespace.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `prefix` | string | No | Filter keys by prefix |

**Returns:** List of key strings (sorted).

**Example:**
```python
# List all keys
all_keys = data_store.list_keys()
# Returns: ["analysis:file1", "analysis:file2", "config", "status"]

# Filter by prefix
analysis_keys = data_store.list_keys(prefix="analysis:")
# Returns: ["analysis:file1", "analysis:file2"]
```

## Namespace Operations

### `list_namespaces()`

List all namespaces that contain data for the current user.

**Parameters:** None

**Returns:** List of namespace strings (sorted).

**Example:**
```python
namespaces = data_store.list_namespaces()
# Returns: ["default", "files:repo-a", "files:repo-b", "cache:api"]

# Find specific namespaces
file_namespaces = [ns for ns in namespaces if ns.startswith("files:")]
```

**Notes:**
- Only returns namespaces with at least one key
- Includes the `"default"` namespace if it has data

### `use_namespace(namespace)`

Get a data store proxy for a different namespace.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `namespace` | string | Yes | Target namespace name |

**Returns:** New `AgentDataStoreProxy` instance scoped to the specified namespace.

**Example:**
```python
# Work with a specific namespace
cache = data_store.use_namespace("api-cache")
cache.set("user-123", user_data)
cache.get("user-123")

# Dynamic namespace names
repo = input_dict.get("repo")
files = data_store.use_namespace(f"files:{repo}")
files.set("src/main.py", content)

# Chain namespace operations
summaries = data_store.use_namespace(f"summary:{repo}")
for file_key in files.list_keys():
    content = files.get(file_key)
    summary = await summarize(content)
    summaries.set(file_key, summary)
```

**Notes:**
- Returns a new proxy; original `data_store` is unchanged
- Namespace is created implicitly on first write
- Empty namespaces don't appear in `list_namespaces()`

### `clear()`

Delete all data in the current namespace.

**Parameters:** None

**Returns:** Number of keys deleted.

**Example:**
```python
# Clear a temporary namespace
temp = data_store.use_namespace("temp-processing")
temp.set("step1", result1)
temp.set("step2", result2)

# ... do processing ...

# Clean up
deleted_count = temp.clear()
print(f"Cleaned up {deleted_count} temporary keys")
```

**Warning:** This permanently deletes all data in the namespace. Use with caution.

## Batch Operations

### `get_many(keys)`

Retrieve multiple values in one operation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `keys` | list | Yes | List of keys to retrieve |

**Returns:** Dictionary mapping keys to values. Missing keys are omitted.

**Example:**
```python
# Get multiple keys
results = data_store.get_many(["file1", "file2", "file3"])
# Returns: {"file1": {...}, "file2": {...}}
# Note: "file3" omitted if it doesn't exist

# Process all retrieved values
for key, value in results.items():
    print(f"{key}: {value}")
```

### `set_many(items, metadata=None)`

Store multiple values in one operation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `items` | dict | Yes | Dictionary of key-value pairs |
| `metadata` | dict | No | Metadata to attach to all items |

**Returns:** Number of items stored.

**Example:**
```python
# Store multiple values
count = data_store.set_many({
    "file:a.py": {"lines": 100, "functions": 5},
    "file:b.py": {"lines": 200, "functions": 10},
    "file:c.py": {"lines": 50, "functions": 2},
})
print(f"Stored {count} files")

# With shared metadata
data_store.set_many(analysis_results, metadata={
    "batch_id": "batch-123",
    "analyzed_at": "2026-02-05"
})
```

## Complete Example

```python
async def run(input_dict: dict, tools: dict) -> dict:
    repo = input_dict.get("repo")
    query = input_dict.get("query", "")
    
    # Check if repo is already indexed
    namespaces = data_store.list_namespaces()
    files_ns = f"files:{repo}"
    
    if files_ns not in namespaces:
        return {"error": f"Repository {repo} not indexed. Run indexer first."}
    
    # Access the indexed files
    files = data_store.use_namespace(files_ns)
    summaries = data_store.use_namespace(f"summary:{repo}")
    
    # Search through summaries
    results = []
    for key in summaries.list_keys():
        summary = summaries.get(key)
        if query.lower() in str(summary).lower():
            results.append({
                "file": key,
                "summary": summary,
                "content_preview": files.get(key, {}).get("content", "")[:200]
            })
    
    # Cache search results
    cache = data_store.use_namespace("search-cache")
    cache.set(f"{repo}:{query}", {
        "results": results,
        "count": len(results)
    })
    
    return {
        "repo": repo,
        "query": query,
        "matches": len(results),
        "results": results[:10]  # Limit response size
    }
```

## Error Handling

The data store methods handle errors gracefully:

| Scenario | Behavior |
|----------|----------|
| Key not found | `get()` returns `default` |
| Delete non-existent key | `delete()` returns `False` |
| Invalid value (not JSON-serializable) | Raises `TypeError` |
| Database unavailable | Raises `HTTPException` |

**Example error handling:**
```python
try:
    # This might fail if value isn't JSON-serializable
    data_store.set("key", some_object)
except TypeError as e:
    return {"error": f"Cannot store value: {e}"}
```

## Thread Safety

The data store proxy is not thread-safe. In async contexts, avoid concurrent modifications to the same key. Use unique keys or namespaces for parallel operations.

## Related Documentation

- [Schema](schema.md) - Document structure details
- [Namespaces](namespaces.md) - Namespace patterns and best practices
- [Patterns](patterns.md) - Common usage recipes