# Data Store Troubleshooting

Solutions to common issues when using the Agent Data Store.

## Common Issues

### "name 'data_store' is not defined"

**Problem:** Agent code fails with `NameError: name 'data_store' is not defined`

**Cause:** The data store wasn't injected into the agent sandbox.

**Solutions:**

1. Verify `dependencies.py` includes the data store injection:
```python
from services.data_store_service import DataStoreService, AgentDataStoreProxy, get_data_store_service

# In _execute_agent_code():
data_store_service = get_data_store_service(db)
data_store_proxy = AgentDataStoreProxy(
    service=data_store_service,
    user_id=user_id,
    agent_name=agent_name or "unknown",
    default_namespace="default"
)

exec_globals = {
    # ... other globals ...
    "data_store": data_store_proxy,
}
```

2. Restart the API service after changes

### Data Not Found After Storage

**Problem:** `data_store.get()` returns `None` even after calling `set()`

**Possible Causes:**

1. **Different namespaces:**
```python
# Agent A stores in custom namespace
cache = data_store.use_namespace("my-cache")
cache.set("key", value)

# Agent B looks in default namespace - won't find it!
data_store.get("key")  # Returns None

# Fix: Use the same namespace
cache = data_store.use_namespace("my-cache")
cache.get("key")  # Found!
```

2. **Different users:**
Data is isolated per user. Agents running as different users can't see each other's data.

3. **Key mismatch:**
```python
data_store.set("my-key", value)
data_store.get("my_key")  # Wrong! Different key (underscore vs hyphen)
```

**Debug steps:**
```python
# List all namespaces
namespaces = data_store.list_namespaces()
print(f"Available namespaces: {namespaces}")

# List keys in each namespace
for ns in namespaces:
    store = data_store.use_namespace(ns)
    keys = store.list_keys()
    print(f"{ns}: {keys}")
```

### Data Store Operations Slow

**Problem:** `get()` and `set()` operations take a long time

**Possible Causes:**

1. **Large values:** Keep individual values under 1MB
2. **Many keys:** Use batch operations (`get_many`, `set_many`)
3. **Database issues:** Check database health

**Solutions:**

1. **Use batch operations:**
```python
# Instead of
for key in keys:
    data_store.get(key)

# Use
results = data_store.get_many(keys)
```

2. **Check database connectivity:**
```bash
# For CouchDB
curl -s http://localhost:5984/_up
```

### TypeError: Object is not JSON serializable

**Problem:** `data_store.set()` fails with serialization error

**Cause:** Value contains non-JSON-serializable types

**Common culprits:**
- `datetime` objects
- Custom class instances
- Lambda functions
- File handles
- `bytes` objects

**Solutions:**

```python
# Convert datetime to string
from datetime import datetime

# DON'T
data_store.set("timestamp", datetime.now())

# DO
data_store.set("timestamp", datetime.now().isoformat())

# Convert bytes to base64
import base64

# DON'T
data_store.set("binary", b"raw bytes")

# DO
data_store.set("binary", base64.b64encode(b"raw bytes").decode())

# Convert custom objects to dicts
class MyResult:
    def __init__(self, score):
        self.score = score

# DON'T
data_store.set("result", MyResult(95))

# DO
data_store.set("result", {"score": 95})
```

### Namespace Not Appearing in list_namespaces()

**Problem:** Created namespace doesn't appear in `list_namespaces()`

**Cause:** Empty namespaces aren't tracked

**Solution:** Namespaces only appear after you store at least one key:

```python
# This namespace won't appear yet
cache = data_store.use_namespace("new-namespace")
print(data_store.list_namespaces())  # Doesn't include "new-namespace"

# After storing data
cache.set("first-key", "value")
print(data_store.list_namespaces())  # Now includes "new-namespace"
```

### Data Persists After delete()

**Problem:** Deleted data still appears

**Cause:** Caching or stale references

**Solutions:**

1. **Verify deletion:**
```python
deleted = data_store.delete("key")
print(f"Was deleted: {deleted}")

# Double-check
exists = data_store.get("key")
print(f"Still exists: {exists is not None}")
```

2. **Clear entire namespace:**
```python
count = data_store.clear()
print(f"Deleted {count} keys")
```

## Debugging Techniques

### Print Available Data

Add debugging to your agent:

```python
async def run(input_dict: dict, tools: dict) -> dict:
    # Debug: Show all available data
    namespaces = data_store.list_namespaces()
    debug_info = {"namespaces": namespaces}
    
    for ns in namespaces:
        store = data_store.use_namespace(ns)
        keys = store.list_keys()
        debug_info[ns] = {
            "key_count": len(keys),
            "keys": keys[:10]  # First 10
        }
    
    return {"debug": debug_info, "actual_result": "..."}
```

### Check CouchDB Directly

```bash
# List all documents
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | jq '.rows | length'

# View specific user's data
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  jq '.rows[] | select(.doc.userId == "YOUR_USER_ID") | .doc'

# List namespaces
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "import sys,json; docs=json.load(sys.stdin)['rows']; \
  print(sorted(set(d['doc'].get('namespace','default') for d in docs if 'doc' in d)))"
```

### Enable Debug Logging

In the API service:

```python
import logging
logging.getLogger("services.data_store_service").setLevel(logging.DEBUG)
```

## Database-Specific Issues

### CouchDB

**Connection refused:**
```bash
# Check if CouchDB is running
docker ps | grep couchdb

# Check logs
docker logs docker-couchdb-1 --tail 50

# Verify connectivity
curl http://localhost:5984/
```

**Database doesn't exist:**
```bash
# Create the database
curl -X PUT http://admin:password@localhost:5984/agent_data_store
```

### Firestore

**Permission denied:**
- Check service account credentials
- Verify Firestore rules allow access

### DynamoDB

**Table doesn't exist:**
```bash
# Create table with AWS CLI
aws dynamodb create-table \
  --table-name agent_data_store \
  --attribute-definitions AttributeName=_id,AttributeType=S \
  --key-schema AttributeName=_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

## Getting Help

If you can't resolve an issue:

1. Collect debug information:
   - Error message and stack trace
   - Agent code (sanitized)
   - Database type and configuration
   - Output of `list_namespaces()` and `list_keys()`

2. Check existing issues on GitHub

3. Open a new issue with the collected information

## Related Documentation

- [Administration](administration.md) - Database inspection commands
- [Schema](schema.md) - Document structure
- [Database Troubleshooting](../database-service/troubleshooting.md) - General database issues