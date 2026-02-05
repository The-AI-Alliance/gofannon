# Data Store Patterns

Common patterns and recipes for using the Agent Data Store effectively.

## Caching Patterns

### Cache-Aside (Lazy Loading)

Check cache before expensive operations:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    url = input_dict.get("url")
    cache_key = f"fetch:{url}"
    
    # Check cache first
    cached = data_store.get(cache_key)
    if cached:
        return {"data": cached, "source": "cache"}
    
    # Fetch if not cached
    response = await fetch_url(url)
    
    # Cache for future use
    data_store.set(cache_key, response, metadata={"cached_at": datetime.now().isoformat()})
    
    return {"data": response, "source": "fetched"}
```

### Write-Through Cache

Cache results as you compute them:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    file_path = input_dict.get("file")
    
    # Always compute (or could check cache first)
    analysis = await analyze_file(file_path)
    
    # Always cache the result
    cache = data_store.use_namespace("analysis-cache")
    cache.set(file_path, analysis)
    
    return analysis
```

### Cache with TTL Check

Implement manual TTL checking:

```python
from datetime import datetime, timedelta

async def run(input_dict: dict, tools: dict) -> dict:
    key = input_dict.get("key")
    cache = data_store.use_namespace("timed-cache")
    
    cached = cache.get(key)
    if cached:
        cached_at = datetime.fromisoformat(cached.get("_cached_at", "1970-01-01"))
        if datetime.now() - cached_at < timedelta(hours=1):
            return {"data": cached["value"], "source": "cache"}
    
    # Cache expired or missing
    fresh_data = await fetch_fresh_data(key)
    cache.set(key, {
        "value": fresh_data,
        "_cached_at": datetime.now().isoformat()
    })
    
    return {"data": fresh_data, "source": "fresh"}
```

## Accumulation Patterns

### Running Counter

Track counts across executions:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    counter_key = "processed-count"
    
    current = data_store.get(counter_key, default=0)
    current += 1
    data_store.set(counter_key, current)
    
    return {"run_number": current}
```

### Append to List

Build up a list across runs:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    new_item = input_dict.get("item")
    
    # Get existing list
    items = data_store.get("collected-items", default=[])
    
    # Append new item
    items.append({
        "value": new_item,
        "added_at": datetime.now().isoformat()
    })
    
    # Save updated list
    data_store.set("collected-items", items)
    
    return {"total_items": len(items), "latest": new_item}
```

### Aggregate Statistics

Maintain running statistics:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    new_value = input_dict.get("value")
    
    stats = data_store.get("statistics", default={
        "count": 0,
        "sum": 0,
        "min": None,
        "max": None
    })
    
    stats["count"] += 1
    stats["sum"] += new_value
    stats["min"] = min(stats["min"], new_value) if stats["min"] else new_value
    stats["max"] = max(stats["max"], new_value) if stats["max"] else new_value
    stats["average"] = stats["sum"] / stats["count"]
    
    data_store.set("statistics", stats)
    
    return stats
```

## Organization Patterns

### Hierarchical Keys

Use key prefixes for organization:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    project = input_dict.get("project")
    
    # Store with hierarchical keys
    data_store.set(f"project:{project}:config", config)
    data_store.set(f"project:{project}:status", "active")
    data_store.set(f"project:{project}:files:main.py", main_content)
    data_store.set(f"project:{project}:files:utils.py", utils_content)
    
    # Query by prefix
    all_files = data_store.list_keys(prefix=f"project:{project}:files:")
    
    return {"project": project, "files": all_files}
```

### Dynamic Namespaces

Create namespaces based on input:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    repo = input_dict.get("repo")
    branch = input_dict.get("branch", "main")
    
    # Namespace per repo/branch combination
    ns = f"repo:{repo}:{branch}"
    store = data_store.use_namespace(ns)
    
    # Store branch-specific data
    store.set("commit", latest_commit)
    store.set("files", file_list)
    
    return {"namespace": ns, "files_stored": len(file_list)}
```

### Namespace Discovery

Find and process all related namespaces:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    pattern = input_dict.get("pattern", "repo:")
    
    all_namespaces = data_store.list_namespaces()
    matching = [ns for ns in all_namespaces if ns.startswith(pattern)]
    
    summary = {}
    for ns in matching:
        store = data_store.use_namespace(ns)
        keys = store.list_keys()
        summary[ns] = {
            "key_count": len(keys),
            "keys": keys[:5]  # First 5
        }
    
    return {"pattern": pattern, "matches": len(matching), "summary": summary}
```

## State Machine Pattern

Track workflow state across runs:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    job_id = input_dict.get("job_id")
    action = input_dict.get("action", "status")
    
    state = data_store.get(f"job:{job_id}", default={
        "status": "pending",
        "steps_completed": [],
        "current_step": None,
        "result": None
    })
    
    if action == "status":
        return state
    
    elif action == "advance":
        steps = ["fetch", "process", "validate", "complete"]
        current_idx = steps.index(state["current_step"]) if state["current_step"] else -1
        
        if current_idx < len(steps) - 1:
            next_step = steps[current_idx + 1]
            state["current_step"] = next_step
            state["status"] = "in_progress"
            
            # Execute step...
            step_result = await execute_step(next_step, input_dict)
            state["steps_completed"].append({
                "step": next_step,
                "result": step_result,
                "completed_at": datetime.now().isoformat()
            })
            
            if next_step == "complete":
                state["status"] = "completed"
                state["result"] = step_result
        
        data_store.set(f"job:{job_id}", state)
    
    return state
```

## Batch Processing Pattern

Process items in batches with checkpointing:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    items = input_dict.get("items", [])
    batch_size = input_dict.get("batch_size", 10)
    
    # Get checkpoint
    checkpoint = data_store.get("batch-checkpoint", default={"processed": 0, "results": []})
    start_idx = checkpoint["processed"]
    
    # Process next batch
    batch = items[start_idx:start_idx + batch_size]
    for item in batch:
        result = await process_item(item)
        checkpoint["results"].append(result)
        checkpoint["processed"] += 1
    
    # Save checkpoint
    data_store.set("batch-checkpoint", checkpoint)
    
    return {
        "processed": checkpoint["processed"],
        "total": len(items),
        "complete": checkpoint["processed"] >= len(items),
        "batch_results": checkpoint["results"][-batch_size:]
    }
```

## Lock Pattern (Advisory)

Implement simple advisory locking:

```python
import time

async def run(input_dict: dict, tools: dict) -> dict:
    resource = input_dict.get("resource")
    lock_key = f"lock:{resource}"
    
    # Try to acquire lock
    lock = data_store.get(lock_key)
    if lock:
        lock_time = datetime.fromisoformat(lock["acquired_at"])
        if datetime.now() - lock_time < timedelta(minutes=5):
            return {"error": "Resource locked", "locked_by": lock["agent"]}
    
    # Acquire lock
    data_store.set(lock_key, {
        "agent": "current-agent",
        "acquired_at": datetime.now().isoformat()
    })
    
    try:
        # Do work with the resource
        result = await process_resource(resource)
        return {"result": result}
    finally:
        # Release lock
        data_store.delete(lock_key)
```

**Note:** This is advisory only—there's no true locking mechanism. Use for coordination, not security.

## Index Pattern

Build searchable indexes:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    document = input_dict.get("document")
    doc_id = input_dict.get("id")
    
    # Store the document
    docs = data_store.use_namespace("documents")
    docs.set(doc_id, document)
    
    # Build keyword index
    index = data_store.use_namespace("keyword-index")
    keywords = extract_keywords(document["content"])
    
    for keyword in keywords:
        # Get existing doc list for this keyword
        doc_list = index.get(keyword, default=[])
        if doc_id not in doc_list:
            doc_list.append(doc_id)
            index.set(keyword, doc_list)
    
    return {"indexed": doc_id, "keywords": keywords}

# Search using the index
async def search(query):
    index = data_store.use_namespace("keyword-index")
    docs = data_store.use_namespace("documents")
    
    # Find matching doc IDs
    doc_ids = index.get(query.lower(), default=[])
    
    # Retrieve documents
    results = []
    for doc_id in doc_ids:
        doc = docs.get(doc_id)
        if doc:
            results.append({"id": doc_id, "document": doc})
    
    return results
```

## Anti-Patterns

### ❌ Storing Large Binary Data

```python
# DON'T: Binary data isn't JSON-serializable
data_store.set("image", open("image.png", "rb").read())

# DO: Use base64 for small binaries, or store references
import base64
data_store.set("image", {
    "data": base64.b64encode(image_bytes).decode(),
    "mime_type": "image/png"
})
```

### ❌ Using Data Store for Real-time Coordination

```python
# DON'T: Race conditions with concurrent access
count = data_store.get("counter", 0)
count += 1  # Another agent might increment between these lines
data_store.set("counter", count)

# DO: Accept eventual consistency or use external coordination
```

### ❌ Storing Sensitive Credentials

```python
# DON'T: Store secrets in the data store
data_store.set("api_key", "sk-secret-key")

# DO: Use environment variables or secure secret management
```

## Related Documentation

- [API Reference](api.md) - Complete method documentation
- [Cross-Agent Workflows](cross-agent.md) - Multi-agent patterns
- [Namespaces](namespaces.md) - Namespace best practices