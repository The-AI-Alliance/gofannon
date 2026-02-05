# Database Troubleshooting

## Common Issues

### "Database provider not found"

**Error:** `ValueError: Unknown database provider: xyz`

**Solution:**
- Check `DATABASE_PROVIDER` environment variable
- Must be one of: `memory`, `couchdb`, `firestore`, `dynamodb`

```bash
echo $DATABASE_PROVIDER
export DATABASE_PROVIDER=couchdb
```

### "Connection refused"

**Error:** `ConnectionError: Failed to connect to database`

**Solution:**
1. Verify the database service is running
2. Check the connection URL is correct
3. Ensure firewall/network allows the connection
4. For Docker: verify containers are on the same network

```bash
# Test CouchDB
curl http://localhost:5984

# Check Docker containers
docker ps | grep couchdb
docker network inspect gofannon-network
```

### "Document not found" on list_all

**Issue:** `list_all()` raises 404 instead of returning empty list

**Cause:** Implementation incorrectly handles missing collections

**Fix:** Ensure implementation returns `[]` for non-existent collections:
```python
def list_all(self, db_name: str) -> List[Dict[str, Any]]:
    try:
        return self._fetch_all(db_name)
    except CollectionNotFoundError:
        return []  # Don't raise, return empty list
```

### "Missing _id field"

**Issue:** Documents don't have required `_id` field

**Fix:** Add `_id` in the `save()` method:
```python
def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]):
    doc["_id"] = doc_id  # Always set _id
    # ... rest of implementation
```

## Provider-Specific Issues

### CouchDB

#### Authentication Failed

**Error:** `Unauthorized: You are not a server admin`

**Solution:**
```bash
# Verify credentials
curl -u admin:password http://localhost:5984/_all_dbs

# Check environment variables
echo $COUCHDB_USER
echo $COUCHDB_PASSWORD
```

#### Revision Conflict

**Error:** `409 Conflict: Document update conflict`

**Cause:** CouchDB requires `_rev` field for updates

**Solution:**
```python
try:
    existing = db[doc_id]
    doc["_rev"] = existing["_rev"]
except ResourceNotFound:
    pass  # New document, no revision needed
db[doc_id] = doc
```

#### Slow Performance / Disk Growing

**Solution:** Run compaction
```bash
# Compact a specific database
curl -X POST http://admin:password@localhost:5984/agents/_compact

# Compact all databases
for db in agents users sessions deployments tickets demos; do
  curl -X POST http://admin:password@localhost:5984/${db}/_compact
done
```

### Firestore

#### Authentication Failed

**Error:** `DefaultCredentialsError: Could not automatically determine credentials`

**Solution:**
```bash
# Set credentials path
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Verify file exists and is readable
cat $GOOGLE_APPLICATION_CREDENTIALS | head -5
```

#### "Permission denied" on Collection

**Solution:** Check Firestore security rules allow read/write for your service account.

### DynamoDB

#### Float Serialization Error

**Error:** `TypeError: Float types are not supported`

**Cause:** DynamoDB requires Decimal instead of float

**Solution:**
```python
from decimal import Decimal

def _convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats(item) for item in obj]
    return obj
```

#### Table Not Found

**Error:** `ResourceNotFoundException: Requested resource not found`

**Solution:** Tables are created on first access. Check IAM permissions include `dynamodb:CreateTable`.

#### Provisioned Throughput Exceeded

**Error:** `ProvisionedThroughputExceededException`

**Solution:**
- Increase read/write capacity units
- Enable auto-scaling
- Use on-demand capacity mode

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.getLogger("services.database_service").setLevel(logging.DEBUG)
```

### Test Connection Manually

```python
from config import Settings
from services.database_service import get_database_service

settings = Settings()
db = get_database_service(settings)

# Test basic operations
try:
    db.save("test", "test-doc", {"hello": "world"})
    doc = db.get("test", "test-doc")
    print(f"Success: {doc}")
    db.delete("test", "test-doc")
except Exception as e:
    print(f"Error: {e}")
```

### Inspect CouchDB Data

```bash
# List all databases
curl -u admin:password http://localhost:5984/_all_dbs

# View documents in a database
curl -u admin:password http://localhost:5984/agents/_all_docs?include_docs=true

# Get a specific document
curl -u admin:password http://localhost:5984/agents/AGENT_ID
```

## Data Migration

To migrate data between providers:

```python
from config import Settings
from services.database_service.couchdb import CouchDBService
from services.database_service.dynamodb import DynamoDBService

# Setup
source = CouchDBService(url, user, password)
target = DynamoDBService(region="us-east-1")

# Migrate each collection
for collection in ["agents", "users", "sessions", "deployments", "tickets", "demos"]:
    docs = source.list_all(collection)
    for doc in docs:
        target.save(collection, doc["_id"], doc)
    print(f"Migrated {len(docs)} documents from {collection}")
```

**Note:** Test thoroughly in a staging environment before migrating production data.