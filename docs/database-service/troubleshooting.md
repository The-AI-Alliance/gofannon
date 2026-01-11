# Troubleshooting

## Common Issues

### 1. "Database provider not found"

**Error**: `ValueError: Unknown database provider: xyz`

**Solution**:
- Check `DATABASE_PROVIDER` environment variable
- Ensure it matches one of: `memory`, `couchdb`, `firestore`, `dynamodb`
- Verify the provider is imported in `__init__.py`

**Example**:
```bash
# Check current value
echo $DATABASE_PROVIDER

# Set to valid provider
export DATABASE_PROVIDER=couchdb
```

### 2. "Connection refused"

**Error**: `ConnectionError: Failed to connect to database`

**Solution**:
- Verify database service is running
- Check connection string/URL is correct
- Ensure firewall allows connection
- For Docker: verify service is in same network

**Example**:
```bash
# Test CouchDB connection
curl http://localhost:5984

# Check if Docker container is running
docker ps | grep couchdb

# Check Docker network
docker network inspect gofannon-network
```

### 3. "Document not found" on list_all

**Issue**: `list_all()` raises 404 instead of returning empty list

**Solution**: Ensure implementation returns `[]` for non-existent collections:
```python
def list_all(self, db_name: str) -> List[Dict[str, Any]]:
    try:
        # ... implementation
    except CollectionNotFoundError:
        return []  # Don't raise exception
```

### 4. "Missing _id field"

**Issue**: Documents don't have `_id` field

**Solution**: Add `_id` to document in `save()` method:
```python
def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]):
    doc["_id"] = doc_id  # Ensure _id is present
    # ... rest of implementation
```

### 5. "Float can't be serialized" (DynamoDB)

**Issue**: `TypeError: Float types are not supported`

**Solution**: Convert floats to Decimal:
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

### 6. "Revision conflict" (CouchDB)

**Issue**: `409 Conflict: Document update conflict`

**Solution**: Fetch current revision before update:
```python
try:
    existing = db[doc_id]
    doc["_rev"] = existing["_rev"]
except ResourceNotFound:
    pass  # New document, no revision needed
```

## Provider-Specific Issues

### CouchDB Issues

#### Admin Party Mode Disabled

**Error**: `Unauthorized: You are not a server admin`

**Solution**:
- CouchDB requires authentication by default
- Set COUCHDB_USER and COUCHDB_PASSWORD
- Verify credentials are correct

```bash
# Test authentication
curl -u admin:password http://localhost:5984/_all_dbs
```

#### Database Compaction Needed

**Issue**: Disk space growing, slow performance

**Solution**: Run compaction
```bash
curl -X POST http://admin:password@localhost:5984/agents/_compact
```

#### View Building Slow

**Issue**: First query on a view is slow

**Solution**: Views are built on first access. Consider:
- Pre-building views after data import
- Using built-in views like `_all_docs`
- Creating indexes for frequently queried fields

### Firestore Issues

#### Authentication Failed

**Error**: `DefaultCredentialsError: Could not automatically determine credentials`

**Solution**:
- Set GOOGLE_APPLICATION_CREDENTIALS environment variable
- Verify the service account key file exists
- Check file permissions

```bash
# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Verify file exists
ls -l $GOOGLE_APPLICATION_CREDENTIALS
```

#### Permission Denied

**Error**: `PermissionDenied: Missing or insufficient permissions`

**Solution**:
- Verify service account has "Cloud Datastore User" role
- Check Firestore security rules
- Ensure Firestore is enabled in Firebase Console

```bash
# Check IAM permissions in GCP Console
gcloud projects get-iam-policy PROJECT_ID

# Add Firestore user role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
  --role=roles/datastore.user
```

#### Quota Exceeded

**Error**: `ResourceExhausted: Quota exceeded`

**Solution**:
- Check usage in Firebase Console
- Upgrade to Blaze plan for higher quotas
- Optimize code to reduce reads/writes
- Implement caching

### DynamoDB Issues

#### Credentials Not Found

**Error**: `NoCredentialsError: Unable to locate credentials`

**Solution**:
- Set AWS credentials environment variables
- Run `aws configure`
- Use IAM role when running on AWS

```bash
# Set credentials
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Or configure via AWS CLI
aws configure
```

#### Access Denied

**Error**: `AccessDeniedException: User is not authorized`

**Solution**:
- Verify IAM permissions include DynamoDB access
- Check if user/role has required permissions

```bash
# Check user permissions
aws iam get-user-policy --user-name USERNAME --policy-name POLICY_NAME

# Attach DynamoDB full access policy
aws iam attach-user-policy \
  --user-name USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

#### Throttling

**Error**: `ProvisionedThroughputExceededException: Throttled`

**Solution**:
- Switch to on-demand billing mode (default in implementation)
- Increase provisioned capacity if using provisioned mode
- Implement exponential backoff retry logic
- Use batch operations

#### Table Already Exists

**Issue**: Table creation fails because table exists

**Solution**: Implementation already handles this. If you see this error:
- Wait for table to be ACTIVE
- Check if table is in CREATING or UPDATING state

```bash
# Check table status
aws dynamodb describe-table --table-name agents
```

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Check Database Logs

Most databases have detailed logs:

**CouchDB**:
- Access Fauxton UI: http://localhost:5984/_utils
- Check logs in Docker: `docker logs gofannon-couchdb`

**Firestore**:
- View logs in Google Cloud Console
- Enable Cloud Audit Logs

**DynamoDB**:
- View logs in CloudWatch Logs
- Enable DynamoDB Streams for change tracking

### 3. Test Connectivity

```bash
# CouchDB
curl http://localhost:5984

# DynamoDB Local
aws dynamodb list-tables --endpoint-url http://localhost:8000

# Firestore (using gcloud)
gcloud firestore databases list
```

### 4. Verify Environment Variables

```bash
# Check all database-related environment variables
env | grep DATABASE
env | grep COUCHDB
env | grep DYNAMODB
env | grep GOOGLE_APPLICATION_CREDENTIALS
```

### 5. Use Database Client Tools

**CouchDB**:
- Fauxton web UI: http://localhost:5984/_utils
- Command line: `curl` commands

**DynamoDB**:
- AWS Console
- NoSQL Workbench for DynamoDB
- AWS CLI

**Firestore**:
- Firebase Console
- Google Cloud Console
- gcloud CLI

## Network Issues

### Docker Networking

**Issue**: Application can't connect to database container

**Solution**:
```bash
# Verify containers are on same network
docker network ls
docker network inspect gofannon-network

# Connect container to network if needed
docker network connect gofannon-network gofannon-couchdb
```

### Firewall Issues

**Issue**: Connection blocked by firewall

**Solution**:
```bash
# Check if port is listening
netstat -tuln | grep 5984

# Test connection
telnet localhost 5984

# For cloud databases, check security groups/firewall rules
```

## Data Issues

### Document ID Mismatch

**Issue**: Document has different ID than expected

**Solution**:
- Always use `_id` field
- Verify ID is set correctly in `save()` method
- Check for ID transformations in database layer

```python
# Correct approach
doc = db.get("agents", "agent-1")
assert doc["_id"] == "agent-1"
```

### Missing Fields

**Issue**: Retrieved documents missing expected fields

**Solution**:
- Check if fields are optional in schema
- Verify data was saved correctly
- Check for field name typos

```python
# Verify saved data
saved = db.save("agents", "test-id", {"name": "Test", "value": 42})
retrieved = db.get("agents", "test-id")
print(retrieved)  # Check all fields are present
```

### Type Conversion Issues

**Issue**: Numeric types don't match expected types

**Solution**:
- DynamoDB converts floats to Decimal (implementation handles this)
- CouchDB preserves Python types
- Firestore preserves Python types
- Handle conversions in your application code if needed

## Performance Issues

### Slow List Operations

**Issue**: `list_all()` is slow on large collections

**Solution**:
- Implement pagination (see [Performance](performance.md))
- Use filters to reduce result set
- Consider using database-specific query capabilities
- Add indexes for frequently queried fields

### Connection Pool Exhausted

**Issue**: Getting connection errors under load

**Solution**:
- Increase connection pool size
- Implement connection pooling if not already present
- Release connections properly after use
- Monitor connection usage

## Error Message Reference

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `ConnectionRefusedError` | Database not running | Start database service |
| `401 Unauthorized` | Invalid credentials | Check username/password |
| `404 Not Found` | Document/collection doesn't exist | Create document/collection |
| `409 Conflict` | Revision mismatch (CouchDB) | Fetch current revision |
| `500 Internal Server Error` | Database error | Check database logs |
| `NoCredentialsError` | AWS credentials not set | Configure AWS credentials |
| `DefaultCredentialsError` | GCP credentials not set | Set GOOGLE_APPLICATION_CREDENTIALS |
| `ProvisionedThroughputExceededException` | DynamoDB throttling | Switch to on-demand or increase capacity |
| `ResourceExhausted` | Quota exceeded | Upgrade plan or optimize usage |

## Getting Help

If you're still experiencing issues:

1. **Check Logs**: Database logs often contain detailed error messages
2. **Enable Debug Logging**: Add verbose logging to your application
3. **Test Manually**: Use database client tools to verify connectivity
4. **Isolate the Issue**: Test with minimal code to reproduce
5. **Review Documentation**: Check provider-specific documentation
6. **Search Issues**: Look for similar issues in project repository
7. **Ask for Help**: Create an issue with:
   - Error message
   - Configuration (redact secrets)
   - Steps to reproduce
   - Database provider and version
   - Environment details

## Related Documentation

- [Configuration](configuration.md) - Database provider configuration
- [Testing](testing.md) - Testing strategies and debugging tests
- [Performance](performance.md) - Performance optimization
- [Security](security.md) - Security best practices
- [Implementations](implementations/) - Provider-specific documentation
- [Database Service README](README.md) - Overview

---

Last Updated: 2026-01-11
