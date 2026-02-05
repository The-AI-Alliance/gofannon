# Agent Data Store

The Agent Data Store provides persistent key-value storage for agents, enabling them to save and retrieve data across executions.

## Overview

The data store enables:
- **Persistence**: Save results between agent runs
- **Caching**: Avoid redundant expensive operations
- **Cross-agent communication**: Share data between agents
- **Incremental processing**: Build up results over multiple executions

Data is automatically scoped per-user, so agents can only access their owner's data.

## Quick Example

The `data_store` object is automatically available in every agent:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Check cache
    cached = data_store.get("analysis-result")
    if cached:
        return {"result": cached, "source": "cache"}
    
    # Compute and cache
    result = await expensive_analysis()
    data_store.set("analysis-result", result)
    
    return {"result": result, "source": "computed"}
```

## Documentation

Detailed documentation is available in the [data-store](data-store/README.md) directory:

- **[Quick Start](data-store/quickstart.md)** - Get started in 5 minutes
- **[API Reference](data-store/api.md)** - Complete method documentation
- **[Schema](data-store/schema.md)** - Document structure
- **[Namespaces](data-store/namespaces.md)** - Organizing data
- **[Patterns](data-store/patterns.md)** - Common usage recipes
- **[Cross-Agent Workflows](data-store/cross-agent.md)** - Multi-agent data sharing
- **[Troubleshooting](data-store/troubleshooting.md)** - Common issues
- **[Administration](data-store/administration.md)** - Database management

## Key Features

### Namespaces

Organize data into logical groups:

```python
# Different namespaces for different purposes
files = data_store.use_namespace(f"files:{repo}")
summaries = data_store.use_namespace(f"summary:{repo}")
cache = data_store.use_namespace("api-cache")
```

### Namespace Discovery

Find what data exists:

```python
namespaces = data_store.list_namespaces()
# Returns: ["default", "files:my-repo", "cache:github", ...]
```

### Batch Operations

Efficient bulk operations:

```python
# Set multiple values
data_store.set_many({"key1": val1, "key2": val2})

# Get multiple values
results = data_store.get_many(["key1", "key2"])
```

## Related Documentation

- [Database Service](database-service.md) - Underlying storage infrastructure
- [Developer Quickstart](developers-quickstart.md) - Getting started with development