# Data Store Quick Start

Get started with the Agent Data Store in 5 minutes.

## Prerequisites

- A working Gofannon webapp installation
- At least one agent created

## Step 1: Basic Storage

The `data_store` object is automatically available in every agent. Create an agent with this code:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Store a value
    data_store.set("greeting", "Hello, World!")
    
    # Retrieve it back
    value = data_store.get("greeting")
    
    return {"stored_value": value}
```

Run the agent—it will store and retrieve the value in the same execution.

## Step 2: Persistent Storage

The power of the data store is persistence across runs. Create a "counter" agent:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Get current count (default to 0)
    count = data_store.get("run-count", default=0)
    
    # Increment and save
    count += 1
    data_store.set("run-count", count)
    
    return {"run_number": count}
```

Run this agent multiple times—the count persists between executions:
- First run: `{"run_number": 1}`
- Second run: `{"run_number": 2}`
- Third run: `{"run_number": 3}`

## Step 3: Structured Data

Store complex data structures:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Store structured data
    data_store.set("analysis", {
        "file": input_dict.get("file_path"),
        "lines": 150,
        "functions": ["main", "helper", "utils"],
        "score": 85.5,
        "issues": [
            {"line": 10, "message": "Missing docstring"},
            {"line": 45, "message": "Long function"}
        ]
    })
    
    # Retrieve and use
    result = data_store.get("analysis")
    return {"score": result["score"], "issue_count": len(result["issues"])}
```

## Step 4: Using Namespaces

Organize data with namespaces:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    repo = input_dict.get("repo", "default-repo")
    
    # Create namespace for this repo's files
    files = data_store.use_namespace(f"files:{repo}")
    
    # Store file data
    files.set("src/main.py", {"content": "...", "lines": 100})
    files.set("src/utils.py", {"content": "...", "lines": 50})
    
    # List what we stored
    all_files = files.list_keys()
    
    return {"repo": repo, "files_stored": all_files}
```

## Step 5: Discovering Data

Find what data exists across namespaces:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Discover all namespaces
    namespaces = data_store.list_namespaces()
    
    # Build inventory
    inventory = {}
    for ns in namespaces:
        store = data_store.use_namespace(ns)
        keys = store.list_keys()
        inventory[ns] = {"key_count": len(keys), "keys": keys[:5]}  # First 5
    
    return {"namespaces": namespaces, "inventory": inventory}
```

## Step 6: Cross-Agent Workflow

Create two agents that share data:

**Agent A: Data Producer**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Analyze something and store results
    analysis = {"summary": "All tests passed", "score": 100}
    
    shared = data_store.use_namespace("shared")
    shared.set("latest-analysis", analysis)
    
    return {"status": "stored", "data": analysis}
```

**Agent B: Data Consumer**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    shared = data_store.use_namespace("shared")
    
    # Read data from Agent A
    analysis = shared.get("latest-analysis")
    
    if not analysis:
        return {"error": "No analysis found. Run Agent A first."}
    
    return {"retrieved": analysis, "score": analysis.get("score")}
```

Run Agent A, then Agent B—Agent B reads the data Agent A stored.

## Next Steps

- **[API Reference](api.md)** - Complete method documentation
- **[Namespaces](namespaces.md)** - Advanced namespace patterns
- **[Patterns](patterns.md)** - Common usage patterns
- **[Cross-Agent Workflows](cross-agent.md)** - Multi-agent data sharing

## Verification

To verify data was stored, use the administration commands:

```bash
# List all namespaces for a user
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json
docs = json.load(sys.stdin)['rows']
namespaces = sorted(set(d['doc'].get('namespace', 'default') for d in docs if 'doc' in d))
print('Namespaces:', namespaces)
"
```

See [Administration](administration.md) for more commands.