# Google Cloud Firestore

**File**: [firestore.py](../../../webapp/packages/api/user-service/services/database_service/firestore.py)

**Purpose**: Serverless NoSQL database for Google Cloud deployments

## Implementation Details

```python
class FirestoreService(DatabaseService):
    def __init__(self, project_id: str = None):
        firebase_admin.initialize_app()
        self.db = firestore.client()
```

## Characteristics

- **Storage**: Cloud-native distributed database
- **Persistence**: Automatic with multi-region replication
- **Performance**: Low-latency worldwide access
- **Revision Tracking**: Placeholder `"firestore-rev"` (uses server-side versioning)
- **Auto-initialization**: Collections created on first write

## Configuration

```bash
# .env or environment variables
DATABASE_PROVIDER=firestore

# Authentication via Firebase Admin SDK:
# - Set GOOGLE_APPLICATION_CREDENTIALS pointing to service account JSON
# - Or use Application Default Credentials in GCP
```

## Authentication Setup

### 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select an existing one
3. Enable Firestore Database (Native mode recommended)

### 2. Generate Service Account Key

1. Go to Project Settings > Service Accounts
2. Click "Generate New Private Key"
3. Download the JSON key file
4. Store it securely (DO NOT commit to version control)

### 3. Set Environment Variable

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 4. Alternative: Application Default Credentials

When running on Google Cloud Platform (GCP), you can use Application Default Credentials:

```bash
# No GOOGLE_APPLICATION_CREDENTIALS needed
# The SDK automatically uses the service account of the GCP resource
```

## Special Considerations

### 1. Collection Auto-Creation

Collections are created implicitly on first document write:
- No need to pre-create collections
- No "create database" equivalent

### 2. Document Structure

Firestore uses collections and documents:
- `db_name` parameter maps to collection name
- `doc_id` parameter is the document ID within that collection

### 3. ID Field

Implementation adds `_id` to returned documents:

```python
def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
    doc_ref = self.db.collection(db_name).document(doc_id)
    doc = doc_ref.get()
    data = doc.to_dict()
    data["_id"] = doc.id  # Add ID to document
    return data
```

### 4. Listing Documents

Streams all documents in collection:

```python
docs = self.db.collection(db_name).stream()
for doc in docs:
    data = doc.to_dict()
    data["_id"] = doc.id
    documents.append(data)
```

### 5. Revision Information

Returns placeholder revision:
- Firestore handles versioning server-side
- Application doesn't need to track revisions

## Production Recommendations

- Use security rules to restrict access
- Enable audit logging for compliance
- Use composite indexes for complex queries (if needed)
- Monitor quota usage (reads/writes/deletes)
- Consider Firestore Native mode over Datastore mode
- Use multi-region for high availability

## Cost Considerations

- **Charged per document read/write/delete**
- **Free tier**: 50K reads, 20K writes, 20K deletes per day
- **Storage**: $0.18/GB/month
- **Network egress charges apply**

### Cost Optimization Tips

1. Minimize document reads by caching
2. Use batch operations when possible
3. Structure data to reduce document count
4. Monitor usage in Firebase Console

## Example Usage

```python
from services.database_service import get_database_service
from config import Settings
import os

# Set credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/key.json"

settings = Settings(DATABASE_PROVIDER="firestore")
db = get_database_service(settings)

# Save a document
result = db.save("agents", "agent-1", {"name": "My Agent", "code": "..."})
print(result)  # {"id": "agent-1", "rev": "firestore-rev"}

# Retrieve the document
agent = db.get("agents", "agent-1")
print(agent)  # {"_id": "agent-1", "name": "My Agent", "code": "..."}

# List all agents
all_agents = db.list_all("agents")

# Delete the agent
db.delete("agents", "agent-1")
```

## Common Operations

### Setting Up Firestore Security Rules

```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow authenticated users to read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth.uid == userId;
    }

    // Allow service account full access (for backend)
    match /{document=**} {
      allow read, write: if request.auth.token.email == "service-account@project.iam.gserviceaccount.com";
    }
  }
}
```

Deploy rules:
```bash
firebase deploy --only firestore:rules
```

### Creating Composite Indexes

If you need complex queries, create indexes in Firebase Console or via CLI:

```bash
# firestore.indexes.json
{
  "indexes": [
    {
      "collectionGroup": "agents",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "created_at", "order": "DESCENDING"},
        {"fieldPath": "name", "order": "ASCENDING"}
      ]
    }
  ]
}
```

Deploy indexes:
```bash
firebase deploy --only firestore:indexes
```

### Monitoring Usage

View usage in Firebase Console:
1. Go to Firestore Database
2. Click "Usage" tab
3. Monitor reads, writes, deletes, and storage

## Troubleshooting

### Authentication Failed

**Error**: `DefaultCredentialsError: Could not automatically determine credentials`

**Solutions**:
- Set GOOGLE_APPLICATION_CREDENTIALS environment variable
- Verify the service account key file exists and is valid
- Check file permissions: `ls -l /path/to/key.json`
- Ensure the service account has Firestore permissions

### Permission Denied

**Error**: `PermissionDenied: Missing or insufficient permissions`

**Solutions**:
- Verify service account has "Cloud Datastore User" role
- Check Firestore security rules
- Ensure Firestore is enabled in Firebase Console
- Grant appropriate IAM permissions in GCP Console

### Document Not Found

**Error**: `HTTPException: Document not found`

**Solutions**:
- Verify the document exists in Firebase Console
- Check collection and document ID spelling
- Ensure you're using the correct Firebase project

### Quota Exceeded

**Error**: `ResourceExhausted: Quota exceeded`

**Solutions**:
- Check usage in Firebase Console
- Upgrade to Blaze plan for higher quotas
- Optimize code to reduce reads/writes
- Implement caching to reduce database calls

## Performance Tuning

### Batch Operations

Use batch writes for multiple documents (up to 500 operations):

```python
batch = self.db.batch()

# Add multiple operations
for i in range(100):
    doc_ref = self.db.collection("agents").document(f"agent-{i}")
    batch.set(doc_ref, {"name": f"Agent {i}"})

# Commit all at once
batch.commit()
```

### Pagination

Implement pagination for large collections:

```python
# Get first page
query = self.db.collection("agents").limit(100)
docs = query.stream()

# Get next page using last document as cursor
last_doc = None
for doc in docs:
    last_doc = doc
    # Process document

# Next page
if last_doc:
    next_query = self.db.collection("agents").start_after(last_doc).limit(100)
    next_docs = next_query.stream()
```

### Server Timestamps

Use server timestamps instead of client timestamps:

```python
from google.cloud.firestore import SERVER_TIMESTAMP

doc_ref.set({
    "name": "Agent",
    "created_at": SERVER_TIMESTAMP
})
```

## Security Best Practices

1. **Service Account Security**: Store credentials securely, never in version control
2. **IAM Roles**: Use least privilege principle for service accounts
3. **Security Rules**: Implement granular access control
4. **Audit Logging**: Enable Cloud Audit Logs
5. **VPC Service Controls**: Restrict Firestore access to specific networks
6. **Data Encryption**: Firestore encrypts data at rest by default

## Migration from Another Database

```python
from services.database_service import get_database_service
from config import Settings
import os

# Source: CouchDB
source_settings = Settings(
    DATABASE_PROVIDER="couchdb",
    COUCHDB_URL="http://localhost:5984",
    COUCHDB_USER="admin",
    COUCHDB_PASSWORD="password"
)
source_db = get_database_service(source_settings)

# Target: Firestore
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/key.json"
target_settings = Settings(DATABASE_PROVIDER="firestore")
target_db = get_database_service(target_settings)

# Migrate all collections
collections = ["agents", "deployments", "users", "sessions", "tickets", "demos"]
for collection in collections:
    print(f"Migrating {collection}...")
    documents = source_db.list_all(collection)

    for doc in documents:
        doc_id = doc.pop("_id")
        # Remove source-specific fields
        doc.pop("_rev", None)

        # Save to Firestore
        target_db.save(collection, doc_id, doc)
        print(f"  Migrated {doc_id}")

    print(f"Completed {collection}: {len(documents)} documents")
```

## Related Documentation

- [Configuration](../configuration.md) - Database provider configuration
- [Schema](../schema.md) - Collection and document schemas
- [Testing](../testing.md) - Testing strategies
- [Troubleshooting](../troubleshooting.md) - Common issues and solutions
- [Firebase Admin SDK Documentation](https://firebase.google.com/docs/admin/setup)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)

---

Last Updated: 2026-01-11
