# Apache CouchDB

**File**: [couchdb.py](../../../webapp/packages/api/user-service/services/database_service/couchdb.py)

**Purpose**: Production-ready document database with HTTP API

## Implementation Details

```python
class CouchDBService(DatabaseService):
    def __init__(self, url: str, username: str, password: str):
        self.couch = couchdb.Server(url)
        self.couch.resource.credentials = (username, password)
```

## Characteristics

- **Storage**: Disk-based B-tree
- **Persistence**: Full durability with append-only writes
- **Performance**: Good for document-oriented workloads
- **Revision Tracking**: Native `_rev` field with MVCC
- **Auto-initialization**: Creates databases on first access

## Configuration

```bash
# .env or environment variables
DATABASE_PROVIDER=couchdb
COUCHDB_URL=http://localhost:5984
COUCHDB_USER=admin
COUCHDB_PASSWORD=password
```

## Docker Setup

```yaml
# docker-compose.yml includes:
services:
  couchdb:
    image: couchdb:latest
    ports:
      - "5984:5984"
    environment:
      - COUCHDB_USER=admin
      - COUCHDB_PASSWORD=password
```

## Special Considerations

### 1. Database Creation

Automatically creates databases if they don't exist:

```python
# In save() method:
if db_name not in self.couch:
    self.couch.create(db_name)
```

### 2. Revision Conflicts

CouchDB uses MVCC (Multi-Version Concurrency Control):
- Must include current `_rev` when updating documents
- Returns 409 status on conflict
- Implementation handles this by fetching current `_rev` before update:

```python
try:
    existing = db[doc_id]
    doc["_rev"] = existing["_rev"]
except couchdb.http.ResourceNotFound:
    pass  # New document, no _rev needed
```

### 3. Listing Documents

Uses `_all_docs` view with `include_docs=True`:

```python
for row in db.view("_all_docs", include_docs=True):
    documents.append(row.doc)
```

### 4. ID Storage

Stores document ID in both:
- CouchDB's native `_id` field
- Application's `_id` field (for consistency)

## Production Recommendations

- Enable authentication (never use admin party mode)
- Configure replication for high availability
- Set up regular backups (CouchDB replication protocol)
- Monitor disk space (compaction needed periodically)
- Use clustering for horizontal scaling

## Example Usage

```python
from services.database_service import get_database_service
from config import Settings

settings = Settings(
    DATABASE_PROVIDER="couchdb",
    COUCHDB_URL="http://localhost:5984",
    COUCHDB_USER="admin",
    COUCHDB_PASSWORD="password"
)
db = get_database_service(settings)

# Save a document
result = db.save("agents", "agent-1", {"name": "My Agent", "code": "..."})
print(result)  # {"id": "agent-1", "rev": "1-abc123..."}

# Update the document
agent = db.get("agents", "agent-1")
agent["name"] = "Updated Agent"
result = db.save("agents", "agent-1", agent)
print(result)  # {"id": "agent-1", "rev": "2-def456..."}
```

## Common Operations

### Starting CouchDB with Docker

```bash
# Start CouchDB
docker run -d \
  --name gofannon-couchdb \
  -p 5984:5984 \
  -e COUCHDB_USER=admin \
  -e COUCHDB_PASSWORD=password \
  couchdb:latest

# Verify it's running
curl http://admin:password@localhost:5984/
```

### Accessing Fauxton UI

Open http://localhost:5984/_utils in your browser to access the Fauxton web interface.

### Creating a Database Manually

```bash
curl -X PUT http://admin:password@localhost:5984/agents
```

### Viewing Documents

```bash
curl http://admin:password@localhost:5984/agents/_all_docs?include_docs=true
```

## Troubleshooting

### Connection Refused

**Error**: `ConnectionError: Failed to connect to CouchDB`

**Solutions**:
- Verify CouchDB is running: `curl http://localhost:5984`
- Check the URL in your configuration
- Ensure Docker container is running: `docker ps | grep couchdb`

### Authentication Failed

**Error**: `Unauthorized: Invalid credentials`

**Solutions**:
- Verify COUCHDB_USER and COUCHDB_PASSWORD are correct
- Check CouchDB logs: `docker logs gofannon-couchdb`
- Ensure admin party mode is disabled

### Document Conflict

**Error**: `409 Conflict: Document update conflict`

**Solutions**:
- Implementation automatically handles this by fetching current `_rev`
- If you still see this, verify you're using the latest version of the code
- Manually fetch the document and retry the update

### Disk Space Issues

**Error**: Database writes failing or slow

**Solutions**:
- Check disk space: `df -h`
- Run compaction: `curl -X POST http://admin:password@localhost:5984/agents/_compact`
- Set up automatic compaction in CouchDB configuration

## Performance Tuning

### Views and Indexes

Create views for common query patterns:

```javascript
// Example design document for querying agents by name
{
  "_id": "_design/agents",
  "views": {
    "by_name": {
      "map": "function(doc) { if(doc.name) { emit(doc.name, doc); } }"
    }
  }
}
```

### Compaction

Set up automatic compaction in `local.ini`:

```ini
[compactions]
_default = [{db_fragmentation, "70%"}, {view_fragmentation, "60%"}]
```

### Replication

Set up replication for high availability:

```bash
curl -X POST http://admin:password@localhost:5984/_replicate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "http://localhost:5984/agents",
    "target": "http://backup-server:5984/agents",
    "continuous": true
  }'
```

## Security Best Practices

1. **Authentication**: Always require authentication
2. **SSL/TLS**: Use HTTPS in production (configure with reverse proxy)
3. **Least Privilege**: Create application-specific users with limited permissions
4. **Firewall**: Restrict access to CouchDB ports
5. **Audit Logging**: Enable audit logging for compliance
6. **Regular Updates**: Keep CouchDB updated with security patches

## Migration from Memory Database

```python
from services.database_service import get_database_service
from config import Settings

# Source: Memory
source_settings = Settings(DATABASE_PROVIDER="memory")
source_db = get_database_service(source_settings)

# Target: CouchDB
target_settings = Settings(
    DATABASE_PROVIDER="couchdb",
    COUCHDB_URL="http://localhost:5984",
    COUCHDB_USER="admin",
    COUCHDB_PASSWORD="password"
)
target_db = get_database_service(target_settings)

# Migrate all collections
collections = ["agents", "deployments", "users", "sessions", "tickets", "demos"]
for collection in collections:
    documents = source_db.list_all(collection)
    for doc in documents:
        doc_id = doc.pop("_id")
        target_db.save(collection, doc_id, doc)
```

## Related Documentation

- [Configuration](../configuration.md) - Database provider configuration
- [Schema](../schema.md) - Collection and document schemas
- [Testing](../testing.md) - Testing strategies
- [Troubleshooting](../troubleshooting.md) - Common issues and solutions
- [CouchDB Official Documentation](https://docs.couchdb.org/)

---

Last Updated: 2026-01-11
