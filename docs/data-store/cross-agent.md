# Cross-Agent Data Sharing

The data store enables multi-agent workflows where agents share data through a common storage layer.

## How It Works

All agents running for the same user share the same data store. Data written by one agent is immediately available to other agents.

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   Agent A   │────▶│   Data Store    │◀────│   Agent B   │
│  (Producer) │     │  (User Scoped)  │     │  (Consumer) │
└─────────────┘     └─────────────────┘     └─────────────┘
       │                    ▲                      │
       │                    │                      │
       └────── writes ──────┴────── reads ─────────┘
```

## Basic Pattern

### Producer Agent

Generates and stores data:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Analyze something
    report = await generate_analysis(input_dict.get("data"))
    
    # Store for other agents
    shared = data_store.use_namespace("shared")
    shared.set("latest-report", report)
    
    return {"status": "report generated", "key": "latest-report"}
```

### Consumer Agent

Reads and uses the data:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    shared = data_store.use_namespace("shared")
    
    # Read data from producer
    report = shared.get("latest-report")
    
    if not report:
        return {"error": "No report found. Run the analysis agent first."}
    
    # Use the data
    summary = await summarize(report)
    return {"summary": summary}
```

## Common Workflows

### Pipeline Pattern

Sequential processing where each agent builds on the previous:

```
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│  Fetcher  │───▶│  Parser   │───▶│ Analyzer  │───▶│ Reporter  │
└───────────┘    └───────────┘    └───────────┘    └───────────┘
     │                │                │                │
     ▼                ▼                ▼                ▼
  raw:data      parsed:data     analysis:data    report:final
```

**Agent 1: Fetcher**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    url = input_dict.get("url")
    raw_data = await fetch_data(url)
    
    pipeline = data_store.use_namespace("pipeline:job-123")
    pipeline.set("raw", raw_data)
    pipeline.set("status", {"stage": "fetched", "timestamp": now()})
    
    return {"stage": "fetched", "next": "parser"}
```

**Agent 2: Parser**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    pipeline = data_store.use_namespace("pipeline:job-123")
    
    raw = pipeline.get("raw")
    if not raw:
        return {"error": "No raw data. Run fetcher first."}
    
    parsed = parse_data(raw)
    pipeline.set("parsed", parsed)
    pipeline.set("status", {"stage": "parsed", "timestamp": now()})
    
    return {"stage": "parsed", "next": "analyzer"}
```

**Agent 3: Analyzer**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    pipeline = data_store.use_namespace("pipeline:job-123")
    
    parsed = pipeline.get("parsed")
    if not parsed:
        return {"error": "No parsed data. Run parser first."}
    
    analysis = await analyze(parsed)
    pipeline.set("analysis", analysis)
    pipeline.set("status", {"stage": "analyzed", "timestamp": now()})
    
    return {"stage": "analyzed", "next": "reporter"}
```

**Agent 4: Reporter**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    pipeline = data_store.use_namespace("pipeline:job-123")
    
    analysis = pipeline.get("analysis")
    if not analysis:
        return {"error": "No analysis. Run analyzer first."}
    
    report = generate_report(analysis)
    pipeline.set("final_report", report)
    pipeline.set("status", {"stage": "complete", "timestamp": now()})
    
    return {"report": report}
```

### Fan-Out Pattern

One agent triggers multiple parallel workers:

```
                    ┌──────────┐
                    │ Splitter │
                    └────┬─────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       ┌─────────┐  ┌─────────┐  ┌─────────┐
       │Worker 1 │  │Worker 2 │  │Worker 3 │
       └────┬────┘  └────┬────┘  └────┬────┘
            │            │            │
            └────────────┴────────────┘
                         │
                         ▼
                   ┌───────────┐
                   │ Collector │
                   └───────────┘
```

**Splitter Agent**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    items = input_dict.get("items", [])
    job_id = input_dict.get("job_id")
    
    work = data_store.use_namespace(f"fanout:{job_id}")
    
    # Distribute work
    for i, item in enumerate(items):
        work.set(f"task:{i}", {
            "item": item,
            "status": "pending"
        })
    
    work.set("meta", {
        "total_tasks": len(items),
        "completed": 0
    })
    
    return {"job_id": job_id, "tasks_created": len(items)}
```

**Worker Agent** (run multiple times)
```python
async def run(input_dict: dict, tools: dict) -> dict:
    job_id = input_dict.get("job_id")
    task_id = input_dict.get("task_id")
    
    work = data_store.use_namespace(f"fanout:{job_id}")
    
    # Get task
    task = work.get(f"task:{task_id}")
    if not task or task["status"] != "pending":
        return {"error": "Task not available"}
    
    # Mark in progress
    task["status"] = "processing"
    work.set(f"task:{task_id}", task)
    
    # Do work
    result = await process_item(task["item"])
    
    # Store result
    task["status"] = "complete"
    task["result"] = result
    work.set(f"task:{task_id}", task)
    
    # Update meta
    meta = work.get("meta")
    meta["completed"] += 1
    work.set("meta", meta)
    
    return {"task_id": task_id, "result": result}
```

**Collector Agent**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    job_id = input_dict.get("job_id")
    
    work = data_store.use_namespace(f"fanout:{job_id}")
    meta = work.get("meta")
    
    if meta["completed"] < meta["total_tasks"]:
        return {
            "status": "in_progress",
            "completed": meta["completed"],
            "total": meta["total_tasks"]
        }
    
    # Collect all results
    results = []
    for i in range(meta["total_tasks"]):
        task = work.get(f"task:{i}")
        results.append(task["result"])
    
    return {"status": "complete", "results": results}
```

### Repository Ingestion Pattern

Common pattern for processing codebases:

**Ingestion Agent**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    repo = input_dict.get("repo")
    
    files_ns = data_store.use_namespace(f"files:{repo}")
    summary_ns = data_store.use_namespace(f"summary:{repo}")
    
    files = await fetch_repo_files(repo)
    
    for path, content in files.items():
        # Store raw content
        files_ns.set(path, {
            "content": content,
            "size": len(content),
            "type": detect_type(path)
        })
        
        # Generate and store summary
        summary = await summarize_file(content)
        summary_ns.set(path, summary)
    
    # Store metadata
    meta_ns = data_store.use_namespace(f"meta:{repo}")
    meta_ns.set("ingestion", {
        "file_count": len(files),
        "completed_at": datetime.now().isoformat()
    })
    
    return {"repo": repo, "files_processed": len(files)}
```

**Search Agent**
```python
async def run(input_dict: dict, tools: dict) -> dict:
    query = input_dict.get("query")
    
    # Discover all indexed repos
    namespaces = data_store.list_namespaces()
    summary_namespaces = [ns for ns in namespaces if ns.startswith("summary:")]
    
    results = []
    for ns in summary_namespaces:
        repo = ns.replace("summary:", "")
        summaries = data_store.use_namespace(ns)
        
        for path in summaries.list_keys():
            summary = summaries.get(path)
            if query.lower() in str(summary).lower():
                results.append({
                    "repo": repo,
                    "file": path,
                    "summary": summary
                })
    
    return {"query": query, "matches": results}
```

## Coordination Patterns

### Status Tracking

Track multi-agent workflow status:

```python
# Any agent can update status
status = data_store.use_namespace("workflow:status")
status.set("current_stage", "processing")
status.set("last_update", {
    "agent": "analyzer",
    "timestamp": datetime.now().isoformat(),
    "message": "Processing file 45 of 100"
})

# Monitor agent can check status
status = data_store.use_namespace("workflow:status")
current = status.get("current_stage")
update = status.get("last_update")
```

### Handoff Protocol

Explicit handoff between agents:

```python
# Producer signals completion
handoff = data_store.use_namespace("handoff")
handoff.set("data-ready", {
    "producer": "agent-a",
    "data_key": "processed-data",
    "namespace": "results",
    "ready_at": datetime.now().isoformat()
})

# Consumer waits for signal
handoff = data_store.use_namespace("handoff")
signal = handoff.get("data-ready")
if signal:
    results = data_store.use_namespace(signal["namespace"])
    data = results.get(signal["data_key"])
```

### Error Propagation

Share errors across the workflow:

```python
# Agent encounters error
errors = data_store.use_namespace("workflow:errors")
errors.set(f"error:{datetime.now().isoformat()}", {
    "agent": "parser",
    "error": str(e),
    "context": {"file": current_file}
})

# Other agents can check for errors
errors = data_store.use_namespace("workflow:errors")
error_keys = errors.list_keys()
if error_keys:
    return {"status": "workflow_error", "errors": error_keys}
```

## Best Practices

### 1. Use Consistent Namespaces

Document and share namespace conventions:

```python
# Shared constants
NAMESPACE_FILES = lambda repo: f"files:{repo}"
NAMESPACE_SUMMARY = lambda repo: f"summary:{repo}"
NAMESPACE_META = lambda repo: f"meta:{repo}"
```

### 2. Include Metadata

Always include context about who wrote the data:

```python
data_store.set("result", {
    "data": actual_data,
    "_meta": {
        "produced_by": "analyzer-agent",
        "produced_at": datetime.now().isoformat(),
        "version": "1.0"
    }
})
```

### 3. Handle Missing Data Gracefully

```python
data = shared.get("expected-key")
if not data:
    return {
        "error": "Required data not found",
        "expected_key": "expected-key",
        "namespace": "shared",
        "suggestion": "Run the producer agent first"
    }
```

### 4. Clean Up After Workflows

```python
# At workflow end
cleanup_namespaces = [
    f"pipeline:{job_id}",
    f"temp:{job_id}",
    f"handoff:{job_id}"
]

for ns in cleanup_namespaces:
    data_store.use_namespace(ns).clear()
```

### 5. Version Your Data Formats

```python
data_store.set("config", {
    "_version": 2,
    "setting_a": "value",
    "setting_b": "value"
})

# Consumer checks version
config = data_store.get("config")
if config.get("_version", 1) < 2:
    # Handle old format or request re-generation
    pass
```

## Related Documentation

- [Namespaces](namespaces.md) - Namespace patterns
- [Patterns](patterns.md) - General usage patterns
- [API Reference](api.md) - Method documentation