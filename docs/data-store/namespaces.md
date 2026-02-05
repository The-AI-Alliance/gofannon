# Data Store Namespaces

Namespaces organize data into logical groups, enabling clean separation between different types of data and use cases.

## Overview

A namespace is a string that groups related keys together. Every data store operation happens within a namespace. The default namespace is `"default"`.

```python
# Default namespace
data_store.set("key", value)  # Stored in "default" namespace

# Custom namespace
cache = data_store.use_namespace("api-cache")
cache.set("key", value)  # Stored in "api-cache" namespace
```

## Namespace Isolation

Keys are unique within a namespace but can repeat across namespaces:

```python
# These are three different keys
data_store.set("config", {"theme": "dark"})                    # default:config
data_store.use_namespace("user-a").set("config", {"lang": "en"})  # user-a:config
data_store.use_namespace("user-b").set("config", {"lang": "fr"})  # user-b:config
```

## Naming Conventions

### Recommended Patterns

| Pattern | Example | Use Case |
|---------|---------|----------|
| `type:identifier` | `files:my-repo` | Scoped by resource |
| `purpose` | `cache` | Simple categorization |
| `source:type` | `github:repos` | External data sources |
| `feature:scope` | `analysis:quarterly` | Feature-specific data |

### Examples

```python
# Repository data
files = data_store.use_namespace(f"files:{repo}")
summaries = data_store.use_namespace(f"summary:{repo}")

# API caching
github_cache = data_store.use_namespace("cache:github")
stripe_cache = data_store.use_namespace("cache:stripe")

# Feature-specific
search_index = data_store.use_namespace("index:search")
user_prefs = data_store.use_namespace("prefs")
```

### Naming Rules

- Use lowercase letters, numbers, hyphens, and colons
- Avoid spaces and special characters
- Keep names descriptive but concise
- Use colons to create hierarchy

```python
# Good
"files:apache/my-repo"
"cache:api-responses"
"analysis:2026-q1"

# Avoid
"Files For My Repo"     # Spaces, mixed case
"cache/responses"       # Slashes
"temp_data!!!"          # Special characters
```

## Dynamic Namespaces

Create namespaces based on runtime values:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    repo = input_dict.get("repo")
    branch = input_dict.get("branch", "main")
    
    # Dynamic namespace from input
    ns = f"repo:{repo}:{branch}"
    store = data_store.use_namespace(ns)
    
    # Store branch-specific data
    store.set("head_commit", commit_sha)
    store.set("file_count", len(files))
    
    return {"namespace": ns}
```

## Namespace Discovery

### List All Namespaces

```python
namespaces = data_store.list_namespaces()
# Returns: ["default", "cache:github", "files:repo-a", "files:repo-b", ...]
```

### Find Namespaces by Pattern

```python
namespaces = data_store.list_namespaces()

# Find all file namespaces
file_namespaces = [ns for ns in namespaces if ns.startswith("files:")]

# Find all cache namespaces
cache_namespaces = [ns for ns in namespaces if ns.startswith("cache:")]

# Find namespaces containing a term
repo_namespaces = [ns for ns in namespaces if "my-repo" in ns]
```

### Inventory All Data

```python
async def run(input_dict: dict, tools: dict) -> dict:
    inventory = {}
    
    for ns in data_store.list_namespaces():
        store = data_store.use_namespace(ns)
        keys = store.list_keys()
        inventory[ns] = {
            "key_count": len(keys),
            "sample_keys": keys[:5]
        }
    
    return {"inventory": inventory}
```

## Cross-Namespace Operations

### Search Across Namespaces

```python
async def run(input_dict: dict, tools: dict) -> dict:
    query = input_dict.get("query", "").lower()
    results = []
    
    for ns in data_store.list_namespaces():
        if not ns.startswith("summary:"):
            continue
            
        store = data_store.use_namespace(ns)
        for key in store.list_keys():
            value = store.get(key)
            if query in str(value).lower():
                results.append({
                    "namespace": ns,
                    "key": key,
                    "match": value
                })
    
    return {"query": query, "matches": len(results), "results": results}
```

### Copy Between Namespaces

```python
async def run(input_dict: dict, tools: dict) -> dict:
    source_ns = input_dict.get("source")
    target_ns = input_dict.get("target")
    
    source = data_store.use_namespace(source_ns)
    target = data_store.use_namespace(target_ns)
    
    copied = 0
    for key in source.list_keys():
        value = source.get(key)
        target.set(key, value)
        copied += 1
    
    return {"copied": copied, "from": source_ns, "to": target_ns}
```

### Aggregate Across Namespaces

```python
async def run(input_dict: dict, tools: dict) -> dict:
    stats = {"total_keys": 0, "namespaces": 0}
    
    for ns in data_store.list_namespaces():
        store = data_store.use_namespace(ns)
        key_count = len(store.list_keys())
        stats["total_keys"] += key_count
        stats["namespaces"] += 1
        stats[ns] = key_count
    
    return stats
```

## Namespace Lifecycle

### Creation

Namespaces are created implicitly when you first store data:

```python
# Namespace "new-ns" doesn't exist yet
new_store = data_store.use_namespace("new-ns")
print(data_store.list_namespaces())  # "new-ns" not listed

# First write creates the namespace
new_store.set("first-key", "value")
print(data_store.list_namespaces())  # "new-ns" now listed
```

### Deletion

Delete all keys to effectively remove a namespace:

```python
# Clear all data in namespace
temp = data_store.use_namespace("temporary")
deleted = temp.clear()
print(f"Deleted {deleted} keys")

# Namespace no longer appears (it's empty)
print(data_store.list_namespaces())  # "temporary" not listed
```

## Best Practices

### 1. Use Descriptive Names

```python
# Good: Clear purpose
data_store.use_namespace("analysis:code-quality")

# Bad: Unclear
data_store.use_namespace("ns1")
```

### 2. Include Context in Dynamic Names

```python
# Good: Context included
ns = f"files:{owner}/{repo}:{branch}"

# Bad: Ambiguous
ns = f"files:{repo}"  # What if repos have same name?
```

### 3. Separate Concerns

```python
# Good: Different types of data in different namespaces
files = data_store.use_namespace(f"files:{repo}")
summaries = data_store.use_namespace(f"summary:{repo}")
cache = data_store.use_namespace("cache")

# Bad: Everything in default namespace
data_store.set(f"file:{repo}:{path}", content)
data_store.set(f"summary:{repo}:{path}", summary)
data_store.set(f"cache:{url}", response)
```

### 4. Document Your Namespace Schema

Keep a record of namespace patterns used in your project:

```
Namespace Schema:
- files:{owner}/{repo}     - Raw file contents
- summary:{owner}/{repo}   - AI-generated summaries
- cache:github             - GitHub API response cache
- cache:llm                - LLM response cache
- index:search             - Search index data
- metrics:daily            - Daily metrics
```

### 5. Clean Up Temporary Namespaces

```python
# Use clear() for temporary processing
temp = data_store.use_namespace("temp:job-123")
try:
    # ... processing ...
finally:
    temp.clear()
```

## Related Documentation

- [API Reference](api.md) - Complete method documentation
- [Patterns](patterns.md) - Usage patterns and recipes
- [Cross-Agent Workflows](cross-agent.md) - Sharing data between agents