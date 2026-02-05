# Agent Data Store Documentation

## Overview

The Agent Data Store provides persistent key-value storage for agents, enabling them to save and retrieve data across executions. Data is scoped per-user, allowing multi-agent workflows where agents share information through a common data layer.

**Key Features:**
- Persistent storage across agent executions
- User-level data isolation
- Namespace organization for logical grouping
- Namespace discovery for dynamic data access
- Batch operations for efficiency
- Automatic access tracking and metadata

## Documentation Structure

This documentation is organized into several focused guides:

### Core Documentation

1. **[Quick Start](quickstart.md)** - Get started with the data store in 5 minutes
2. **[API Reference](api.md)** - Complete method specifications
3. **[Schema](schema.md)** - Data model and document structure

### Usage Guides

4. **[Namespaces](namespaces.md)** - Organizing data with namespaces
5. **[Patterns](patterns.md)** - Common usage patterns and recipes
6. **[Cross-Agent Workflows](cross-agent.md)** - Sharing data between agents

### Operations

7. **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
8. **[Administration](administration.md)** - Database inspection and management

## Quick Start

The `data_store` object is automatically available in every agent sandbox:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Store a value
    data_store.set("my-key", {"result": "some data"})
    
    # Retrieve a value
    value = data_store.get("my-key")
    
    # List all keys
    keys = data_store.list_keys()
    
    return {"stored_keys": keys}
```

No setup required—just use `data_store` in your agent code.

## Key Concepts

### User Isolation

All data is scoped to the current user. Agents can only access data belonging to their user:

```
User A's agents → User A's data (isolated)
User B's agents → User B's data (isolated)
```

### Namespaces

Namespaces organize data by purpose. The default namespace is `"default"`:

```python
# Default namespace
data_store.set("key", value)

# Custom namespace
cache = data_store.use_namespace("api-cache")
cache.set("user-123", user_data)
```

Common namespace patterns:
- `files:{repo}` - Repository file contents
- `summary:{repo}` - File summaries
- `cache:{service}` - API response caching
- `results:{job}` - Job results

### Namespace Discovery

Find what data exists before querying:

```python
# Discover all namespaces with data
namespaces = data_store.list_namespaces()
# Returns: ["default", "files:my-repo", "cache:github", ...]

# Search for specific namespaces
for ns in namespaces:
    if ns.startswith("files:"):
        files = data_store.use_namespace(ns)
        print(f"{ns}: {len(files.list_keys())} files")
```

### Data Model

Each stored record contains:

| Field | Type | Description |
|-------|------|-------------|
| `userId` | string | Owner of the data (automatic) |
| `namespace` | string | Logical grouping |
| `key` | string | Your key name |
| `value` | any | Your stored data (JSON-serializable) |
| `metadata` | object | Optional metadata dict |
| `createdByAgent` | string | Agent that created the record |
| `lastAccessedByAgent` | string | Last agent to access |
| `accessCount` | integer | Number of accesses |
| `createdAt` | datetime | Creation timestamp |
| `updatedAt` | datetime | Last update timestamp |

## Common Tasks

### Cache Expensive Operations

```python
cached = data_store.get("expensive-result")
if cached:
    return {"result": cached, "source": "cache"}

# Compute expensive result
result = await expensive_operation()
data_store.set("expensive-result", result)
return {"result": result, "source": "computed"}
```

### Build Results Across Runs

```python
summaries = data_store.use_namespace("code-summaries")
summaries.set(input_dict["file"], analysis)

# Get accumulated results
all_keys = summaries.list_keys()
return {"total_analyzed": len(all_keys)}
```

### Share Data Between Agents

**Producer Agent:**
```python
shared = data_store.use_namespace("shared-reports")
shared.set("quarterly-report", report)
```

**Consumer Agent:**
```python
shared = data_store.use_namespace("shared-reports")
report = shared.get("quarterly-report")
```

### Discover and Search Data

```python
namespaces = data_store.list_namespaces()
results = []

for ns in namespaces:
    if "summary" in ns:
        store = data_store.use_namespace(ns)
        for key in store.list_keys():
            if query in str(store.get(key)):
                results.append({"namespace": ns, "key": key})
```

## API Summary

### Basic Operations

| Method | Description |
|--------|-------------|
| `get(key, default=None)` | Retrieve a value |
| `set(key, value, metadata=None)` | Store a value |
| `delete(key)` | Delete a value |
| `list_keys(prefix=None)` | List keys in current namespace |

### Namespace Operations

| Method | Description |
|--------|-------------|
| `list_namespaces()` | List all namespaces with data |
| `use_namespace(namespace)` | Get proxy for different namespace |
| `clear()` | Delete all data in current namespace |

### Batch Operations

| Method | Description |
|--------|-------------|
| `get_many(keys)` | Retrieve multiple values |
| `set_many(items, metadata=None)` | Store multiple values |

See [API Reference](api.md) for complete documentation.

## Storage Backend

The data store uses the same database backend as the rest of Gofannon (CouchDB, Firestore, or DynamoDB). Documents are stored in a dedicated `agent_data_store` collection/database.

Document IDs are constructed as: `{user_id}:{namespace}:{base64_encoded_key}`

## Limitations

- **JSON only**: Values must be JSON-serializable (no binary data)
- **User scoped**: Agents cannot access other users' data
- **No TTL**: Data persists until explicitly deleted
- **No transactions**: Concurrent writes use last-write-wins
- **Size limits**: Individual values should be under 1MB

## Related Documentation

- [Database Service](../database-service/README.md) - Underlying storage infrastructure
- [Agent Code Execution](../developers/agent-sandbox.md) - Sandbox environment
- [LLM Provider Configuration](../llm-provider-configuration.md) - Model configuration

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Verify data with [Administration](administration.md) commands
3. Open an issue on GitHub

---

**Documentation Version**: 1.0
**Last Updated**: 2026-02-05
**Maintainer**: Gofannon Development Team