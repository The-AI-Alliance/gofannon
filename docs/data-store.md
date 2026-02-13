# Agent Data Store

The Agent Data Store provides persistent key-value storage for agents, enabling them to save and retrieve data across executions. Data is scoped per-user, allowing multi-agent workflows where agents share information.

## Quick Start

The `data_store` object is automatically available in every agent sandbox:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Store data
    data_store.set("my-key", {"result": "some value"})
    
    # Retrieve data
    value = data_store.get("my-key")
    
    # List all keys
    keys = data_store.list_keys()
    
    return {"stored_keys": keys}
```

## Basic Operations

```python
# Store any JSON-serializable data
data_store.set("key", {"data": [1, 2, 3]})

# Retrieve (returns None if not found)
value = data_store.get("key")

# Retrieve with default
value = data_store.get("key", default={})

# Delete
data_store.delete("key")

# List all keys in current namespace
keys = data_store.list_keys()

# List keys with prefix filter
keys = data_store.list_keys(prefix="file:")
```

## Namespaces

Organize data into logical groups:

```python
# Default namespace
data_store.set("key", value)

# Custom namespace
cache = data_store.use_namespace("api-cache")
cache.set("user-123", user_data)
cache.get("user-123")

# Dynamic namespace names (common pattern)
repo = input_dict.get("repo")
files = data_store.use_namespace(f"files:{repo}")
files.set("src/main.py", content)
```

### Discovering Namespaces

```python
# List all namespaces that have data
namespaces = data_store.list_namespaces()
# Returns: ["default", "files:my-repo", "cache:github", ...]

# Search across namespaces
for ns in namespaces:
    if ns.startswith("files:"):
        store = data_store.use_namespace(ns)
        print(f"{ns}: {len(store.list_keys())} files")
```

## Batch Operations

```python
# Set multiple values atomically
data_store.set_many({
    "key1": "value1",
    "key2": "value2",
    "key3": {"nested": "data"},
})

# Get multiple values
results = data_store.get_many(["key1", "key2", "key3"])
# Returns: {"key1": "value1", "key2": "value2", "key3": {"nested": "data"}}

# Clear all data in current namespace
data_store.clear()
```

## Common Patterns

### Caching Expensive Operations

```python
async def run(input_dict: dict, tools: dict) -> dict:
    url = input_dict["url"]
    cache_key = f"fetch:{url}"
    
    # Check cache first
    cached = data_store.get(cache_key)
    if cached:
        return {"data": cached, "source": "cache"}
    
    # Fetch and cache
    result = await fetch_url(url)
    data_store.set(cache_key, result)
    return {"data": result, "source": "fetched"}
```

### Cross-Agent Data Sharing

**Producer Agent:**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    analysis = await analyze_data(input_dict["data"])
    
    # Store in shared namespace
    shared = data_store.use_namespace("shared")
    shared.set("latest-analysis", analysis)
    
    return {"status": "complete"}
```

**Consumer Agent:**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    shared = data_store.use_namespace("shared")
    analysis = shared.get("latest-analysis")
    
    if not analysis:
        return {"error": "No analysis available"}
    
    return {"analysis": analysis}
```

### Repository Ingestion

```python
async def run(input_dict: dict, tools: dict) -> dict:
    repo = input_dict["repo"]
    
    # Organize into namespaces by type
    files = data_store.use_namespace(f"files:{repo}")
    summaries = data_store.use_namespace(f"summary:{repo}")
    
    for path, content in await fetch_repo_files(repo):
        files.set(path, content)
        summaries.set(path, await summarize(content))
    
    return {
        "repo": repo,
        "files_processed": len(files.list_keys())
    }
```

### Search Agent Using Ingested Data

```python
async def run(input_dict: dict, tools: dict) -> dict:
    query = input_dict["query"]
    
    # Find available repositories
    namespaces = data_store.list_namespaces()
    repos = [ns.replace("files:", "") for ns in namespaces if ns.startswith("files:")]
    
    results = []
    for repo in repos:
        files = data_store.use_namespace(f"files:{repo}")
        summaries = data_store.use_namespace(f"summary:{repo}")
        
        for key in files.list_keys():
            summary = summaries.get(key)
            if query.lower() in summary.lower():
                results.append({"repo": repo, "file": key, "summary": summary})
    
    return {"results": results}
```

## API Reference

| Method | Description |
|--------|-------------|
| `get(key, default=None)` | Retrieve a value by key |
| `set(key, value, metadata=None)` | Store a value |
| `delete(key)` | Delete a value |
| `list_keys(prefix=None)` | List keys in current namespace |
| `list_namespaces()` | List all namespaces with data |
| `get_many(keys)` | Retrieve multiple values |
| `set_many(items, metadata=None)` | Store multiple values |
| `clear()` | Delete all data in current namespace |
| `use_namespace(namespace)` | Get proxy for a different namespace |

## Limitations

- **JSON only**: Values must be JSON-serializable (no bytes, functions, etc.)
- **User scoped**: Agents can only access data owned by the same user
- **No TTL**: Data persists until explicitly deleted
- **No transactions**: Concurrent writes use last-write-wins semantics

## Debugging

### View Data in CouchDB

```bash
# List all documents
curl -s -u admin:password \
  http://localhost:5984/agent_data_store/_all_docs?include_docs=true | jq

# Count documents
curl -s -u admin:password \
  http://localhost:5984/agent_data_store | jq '.doc_count'

# List unique namespaces
curl -s -u admin:password \
  http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "import sys,json; docs=json.load(sys.stdin)['rows']; \
  print(sorted(set(d['doc'].get('namespace','default') for d in docs if 'doc' in d)))"
```

### Check Agent Has Access

```python
# In agent code, verify data_store is available
async def run(input_dict: dict, tools: dict) -> dict:
    print(f"data_store available: {'data_store' in dir()}")
    print(f"Namespaces: {data_store.list_namespaces()}")
    return {}
```

## Related Documentation

- [Database Configuration](database/README.md) - Storage backend setup