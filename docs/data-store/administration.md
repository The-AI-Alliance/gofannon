# Data Store Administration

Commands and procedures for managing the Agent Data Store.

## Database Inspection

### CouchDB Commands

**View all documents:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | jq
```

**Count total documents:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs | jq '.total_rows'
```

**List all namespaces:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json
docs = json.load(sys.stdin)['rows']
namespaces = sorted(set(d['doc'].get('namespace', 'default') for d in docs if 'doc' in d))
for ns in namespaces:
    count = sum(1 for d in docs if d.get('doc', {}).get('namespace') == ns)
    print(f'{ns}: {count} keys')
"
```

**List all users with data:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json
docs = json.load(sys.stdin)['rows']
users = sorted(set(d['doc'].get('userId') for d in docs if 'doc' in d and d['doc'].get('userId')))
for user in users:
    count = sum(1 for d in docs if d.get('doc', {}).get('userId') == user)
    print(f'{user}: {count} keys')
"
```

**View data for specific user:**
```bash
USER_ID="your-user-id"
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  jq --arg uid "$USER_ID" '.rows[] | select(.doc.userId == $uid) | .doc'
```

**View data in specific namespace:**
```bash
NAMESPACE="files:my-repo"
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  jq --arg ns "$NAMESPACE" '.rows[] | select(.doc.namespace == $ns) | .doc'
```

**Get specific document by key:**
```bash
# First, find the document ID (base64 encoded key)
USER_ID="your-user-id"
NAMESPACE="default"
KEY="my-key"
KEY_B64=$(echo -n "$KEY" | base64)
DOC_ID="${USER_ID}:${NAMESPACE}:${KEY_B64}"

curl -s "http://localhost:5984/agent_data_store/${DOC_ID}" | jq
```

### Database Statistics

**Database size and document count:**
```bash
curl -s http://localhost:5984/agent_data_store | jq '{
  db_name: .db_name,
  doc_count: .doc_count,
  disk_size: .sizes.file,
  data_size: .sizes.active
}'
```

**Storage used by namespace:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json

docs = json.load(sys.stdin)['rows']
ns_sizes = {}

for row in docs:
    doc = row.get('doc', {})
    ns = doc.get('namespace', 'default')
    size = len(json.dumps(doc.get('value', '')))
    ns_sizes[ns] = ns_sizes.get(ns, 0) + size

for ns, size in sorted(ns_sizes.items(), key=lambda x: -x[1]):
    print(f'{ns}: {size:,} bytes')
"
```

## Data Management

### Delete User's Data

**Delete all data for a user:**
```bash
USER_ID="user-to-delete"

# List documents to delete
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  jq --arg uid "$USER_ID" '.rows[] | select(.doc.userId == $uid) | {id: .id, rev: .doc._rev}'

# Delete each document (requires admin credentials)
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json, requests

docs = json.load(sys.stdin)['rows']
user_id = '$USER_ID'
deleted = 0

for row in docs:
    doc = row.get('doc', {})
    if doc.get('userId') == user_id:
        doc_id = row['id']
        rev = doc['_rev']
        resp = requests.delete(
            f'http://admin:password@localhost:5984/agent_data_store/{doc_id}?rev={rev}'
        )
        if resp.ok:
            deleted += 1
            print(f'Deleted: {doc_id}')
        else:
            print(f'Failed: {doc_id} - {resp.text}')

print(f'Total deleted: {deleted}')
"
```

### Delete Namespace

**Delete all data in a namespace:**
```bash
NAMESPACE="namespace-to-delete"

curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json, requests

docs = json.load(sys.stdin)['rows']
namespace = '$NAMESPACE'
deleted = 0

for row in docs:
    doc = row.get('doc', {})
    if doc.get('namespace') == namespace:
        doc_id = row['id']
        rev = doc['_rev']
        resp = requests.delete(
            f'http://admin:password@localhost:5984/agent_data_store/{doc_id}?rev={rev}'
        )
        if resp.ok:
            deleted += 1

print(f'Deleted {deleted} documents from namespace {namespace}')
"
```

### Export Data

**Export all data to JSON:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  jq '.rows | map(.doc) | map(del(._rev))' > data_store_export.json
```

**Export specific user's data:**
```bash
USER_ID="user-id"
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  jq --arg uid "$USER_ID" '[.rows[] | .doc | select(.userId == $uid) | del(._rev)]' \
  > user_data_export.json
```

### Import Data

**Import from JSON export:**
```bash
# Note: This creates new documents; existing ones will conflict
cat data_store_export.json | \
  python3 -c "
import sys, json, requests

docs = json.load(sys.stdin)
for doc in docs:
    doc_id = doc['_id']
    resp = requests.put(
        f'http://admin:password@localhost:5984/agent_data_store/{doc_id}',
        json=doc
    )
    if resp.ok:
        print(f'Imported: {doc_id}')
    else:
        print(f'Failed: {doc_id} - {resp.text}')
"
```

## Maintenance

### Compact Database

CouchDB accumulates deleted document tombstones. Compact periodically:

```bash
curl -X POST http://admin:password@localhost:5984/agent_data_store/_compact
```

### Check Database Health

```bash
# Basic health check
curl -s http://localhost:5984/_up | jq

# Database info
curl -s http://localhost:5984/agent_data_store | jq

# Active tasks (compaction, replication, etc.)
curl -s http://admin:password@localhost:5984/_active_tasks | jq
```

### Backup Database

**CouchDB backup (using replication):**
```bash
# Create backup database
curl -X PUT http://admin:password@localhost:5984/agent_data_store_backup

# Replicate
curl -X POST http://admin:password@localhost:5984/_replicate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "agent_data_store",
    "target": "agent_data_store_backup"
  }'
```

**File-level backup (Docker):**
```bash
# Find volume location
docker volume inspect docker_couchdb-data | jq '.[0].Mountpoint'

# Backup (stop container first for consistency)
docker stop docker-couchdb-1
sudo tar -czf couchdb_backup_$(date +%Y%m%d).tar.gz /var/lib/docker/volumes/docker_couchdb-data
docker start docker-couchdb-1
```

## Monitoring

### Watch for Activity

**Monitor CouchDB changes feed:**
```bash
curl -s "http://localhost:5984/agent_data_store/_changes?feed=continuous&include_docs=true" | \
  while read line; do
    echo "$line" | jq -c '{seq: .seq, id: .id, namespace: .doc.namespace, key: .doc.key}'
  done
```

### Usage Statistics

**Documents per agent:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json
from collections import Counter

docs = json.load(sys.stdin)['rows']
agents = Counter(d['doc'].get('createdByAgent', 'unknown') for d in docs if 'doc' in d)

print('Documents by creating agent:')
for agent, count in agents.most_common():
    print(f'  {agent}: {count}')
"
```

**Most accessed keys:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json

docs = json.load(sys.stdin)['rows']
access_counts = [
    (d['doc'].get('key'), d['doc'].get('accessCount', 0), d['doc'].get('namespace'))
    for d in docs if 'doc' in d
]

print('Most accessed keys:')
for key, count, ns in sorted(access_counts, key=lambda x: -x[1])[:10]:
    print(f'  {ns}/{key}: {count} accesses')
"
```

## Security

### Audit Access

**View recent access patterns:**
```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json
from datetime import datetime

docs = json.load(sys.stdin)['rows']
recent = []

for row in docs:
    doc = row.get('doc', {})
    if doc.get('lastAccessedAt'):
        recent.append({
            'key': doc.get('key'),
            'namespace': doc.get('namespace'),
            'accessed': doc.get('lastAccessedAt'),
            'by': doc.get('lastAccessedByAgent')
        })

recent.sort(key=lambda x: x['accessed'], reverse=True)

print('Recent data access:')
for item in recent[:20]:
    print(f\"  {item['accessed']}: {item['namespace']}/{item['key']} by {item['by']}\")
"
```

### Identify Large Values

```bash
curl -s http://localhost:5984/agent_data_store/_all_docs?include_docs=true | \
  python3 -c "
import sys, json

docs = json.load(sys.stdin)['rows']
sizes = []

for row in docs:
    doc = row.get('doc', {})
    value_size = len(json.dumps(doc.get('value', '')))
    if value_size > 10000:  # 10KB threshold
        sizes.append({
            'key': doc.get('key'),
            'namespace': doc.get('namespace'),
            'size': value_size
        })

sizes.sort(key=lambda x: -x['size'])

print('Large values (>10KB):')
for item in sizes[:20]:
    print(f\"  {item['namespace']}/{item['key']}: {item['size']:,} bytes\")
"
```

## Related Documentation

- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Schema](schema.md) - Document structure
- [Database Service](../database-service/README.md) - Underlying storage