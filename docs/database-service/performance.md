# Performance Considerations

## General Guidelines

1. **Connection Pooling**: Reuse database connections
2. **Batch Operations**: Implement batch read/write if supported
3. **Indexing**: Add indexes for frequently queried fields
4. **Caching**: Consider caching frequently accessed documents
5. **Pagination**: Implement pagination for `list_all()` on large collections

## Database-Specific Optimizations

### CouchDB

#### Views for Complex Queries

Use views for frequently executed queries:

```javascript
// Example design document for querying agents by name
{
  "_id": "_design/agents",
  "views": {
    "by_name": {
      "map": "function(doc) { if(doc.name) { emit(doc.name, doc); } }"
    },
    "by_created_at": {
      "map": "function(doc) { if(doc.created_at) { emit(doc.created_at, doc); } }"
    }
  }
}
```

Query the view:
```python
# Instead of scanning all documents
results = db.view("_design/agents/_view/by_name", key="MyAgent")
```

#### Enable Compression

For large documents, enable compression:
```ini
# local.ini
[httpd]
compression = gzip
```

#### Configure Compaction Schedule

Regular compaction prevents disk bloat:
```ini
# local.ini
[compactions]
_default = [{db_fragmentation, "70%"}, {view_fragmentation, "60%"}]
```

#### Use Replication for Read Scaling

Set up read replicas for load distribution:
```bash
curl -X POST http://admin:password@localhost:5984/_replicate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "http://primary:5984/agents",
    "target": "http://replica:5984/agents",
    "continuous": true
  }'
```

### Firestore

#### Minimize Document Reads

Each read counts toward quota and costs money:

```python
# Bad: Reading document multiple times
agent = db.get("agents", "agent-1")
agent = db.get("agents", "agent-1")  # Duplicate read

# Good: Read once and cache
agent = db.get("agents", "agent-1")
# Use cached agent
```

#### Batch Writes

Batch up to 500 operations in a single request:

```python
batch = self.db.batch()

for i in range(100):
    doc_ref = self.db.collection("agents").document(f"agent-{i}")
    batch.set(doc_ref, {"name": f"Agent {i}"})

# Commit all at once
batch.commit()
```

#### Use Collection Group Queries

For cross-collection queries:

```python
# Query all subcollections named "messages"
query = self.db.collection_group("messages").where("read", "==", False)
```

#### Use Server Timestamps

Avoid clock skew issues:

```python
from google.cloud.firestore import SERVER_TIMESTAMP

doc_ref.set({
    "name": "Agent",
    "created_at": SERVER_TIMESTAMP
})
```

#### Composite Indexes

Create indexes for complex queries:

```json
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

### DynamoDB

#### Use Batch Operations

Batch get items (up to 100):

```python
response = dynamodb.batch_get_item(
    RequestItems={
        'agents': {
            'Keys': [
                {'_id': 'agent-1'},
                {'_id': 'agent-2'},
                {'_id': 'agent-3'}
            ]
        }
    }
)
```

Batch write items (up to 25):

```python
with table.batch_writer() as batch:
    for i in range(25):
        batch.put_item(Item={'_id': f'agent-{i}', 'name': f'Agent {i}'})
```

#### Implement Pagination

Handle large result sets efficiently:

```python
def list_all_paginated(self, db_name: str, page_size: int = 100):
    """List all documents with pagination."""
    table = self.tables[db_name]
    response = table.scan(Limit=page_size)

    items = response.get("Items", [])
    yield items

    while "LastEvaluatedKey" in response:
        response = table.scan(
            Limit=page_size,
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items = response.get("Items", [])
        yield items
```

#### Use Query Instead of Scan

Queries are more efficient than scans:

```python
# Bad: Scan entire table
response = table.scan(
    FilterExpression=Attr('name').eq('MyAgent')
)

# Good: Query with partition key
response = table.query(
    KeyConditionExpression=Key('_id').eq('agent-1')
)
```

#### Consider Provisioned Capacity

For predictable workloads:

```python
table = dynamodb.create_table(
    TableName=db_name,
    KeySchema=[{"AttributeName": "_id", "KeyType": "HASH"}],
    AttributeDefinitions=[{"AttributeName": "_id", "AttributeType": "S"}],
    ProvisionedThroughput={
        'ReadCapacityUnits': 100,
        'WriteCapacityUnits': 50
    }
)

# Enable auto-scaling
dynamodb_client.register_scalable_target(
    ServiceNamespace='dynamodb',
    ResourceId=f'table/{table_name}',
    ScalableDimension='dynamodb:table:ReadCapacityUnits',
    MinCapacity=10,
    MaxCapacity=1000
)
```

#### Use DAX for Caching

DynamoDB Accelerator provides microsecond latency:

```python
import amazondax

dax = amazondax.AmazonDaxClient(
    endpoint_url='dax-cluster-endpoint:8111',
    region_name='us-east-1'
)

table = dax.Table('agents')
# Reads are cached
agent = table.get_item(Key={'_id': 'agent-1'})
```

#### Create Global Secondary Indexes

For alternative query patterns:

```python
table.update(
    AttributeDefinitions=[
        {'AttributeName': 'created_at', 'AttributeType': 'S'}
    ],
    GlobalSecondaryIndexUpdates=[
        {
            'Create': {
                'IndexName': 'created_at-index',
                'KeySchema': [
                    {'AttributeName': 'created_at', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'},
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            }
        }
    ]
)
```

## Connection Pooling

### Implementation Example

```python
class DatabaseServiceWithPool(DatabaseService):
    def __init__(self, connection_string: str, pool_size: int = 10):
        self.pool = ConnectionPool(
            connection_string,
            max_connections=pool_size,
            min_connections=2,
            max_idle_time=300  # 5 minutes
        )

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        with self.pool.get_connection() as conn:
            return conn.get(db_name, doc_id)

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        with self.pool.get_connection() as conn:
            return conn.save(db_name, doc_id, doc)
```

### Benefits

- Reduces connection overhead
- Improves throughput
- Prevents connection exhaustion
- Better resource utilization

## Caching Strategies

### In-Memory Cache

```python
from functools import lru_cache
import time

class CachedDatabaseService(DatabaseService):
    def __init__(self, base_service: DatabaseService, ttl: int = 300):
        self.base_service = base_service
        self.cache = {}
        self.ttl = ttl

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        cache_key = f"{db_name}:{doc_id}"

        # Check cache
        if cache_key in self.cache:
            cached_doc, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.ttl:
                return cached_doc

        # Cache miss, fetch from database
        doc = self.base_service.get(db_name, doc_id)

        # Update cache
        self.cache[cache_key] = (doc, time.time())
        return doc

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        result = self.base_service.save(db_name, doc_id, doc)

        # Invalidate cache
        cache_key = f"{db_name}:{doc_id}"
        if cache_key in self.cache:
            del self.cache[cache_key]

        return result
```

### Redis Cache

```python
import redis
import json

class RedisCachedDatabaseService(DatabaseService):
    def __init__(self, base_service: DatabaseService, redis_url: str, ttl: int = 300):
        self.base_service = base_service
        self.redis = redis.from_url(redis_url)
        self.ttl = ttl

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        cache_key = f"{db_name}:{doc_id}"

        # Check Redis cache
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # Cache miss, fetch from database
        doc = self.base_service.get(db_name, doc_id)

        # Update Redis cache
        self.redis.setex(cache_key, self.ttl, json.dumps(doc))
        return doc
```

## Monitoring

### Metrics to Track

1. **Latency Metrics**:
   - P50, P95, P99 latency for each operation
   - Average latency over time
   - Latency by collection

2. **Throughput Metrics**:
   - Requests per second (read/write)
   - Documents processed per second
   - Batch operation sizes

3. **Error Metrics**:
   - Error rate (percentage)
   - Error types distribution
   - Timeout errors

4. **Resource Metrics**:
   - Connection pool usage
   - Memory usage
   - CPU usage
   - Network bandwidth

5. **Database-Specific Metrics**:
   - CouchDB: Disk usage, compaction status
   - Firestore: Read/write/delete counts, quota usage
   - DynamoDB: Throttled requests, consumed capacity

### Monitoring Implementation

```python
import time
from typing import Dict, Any

class MonitoredDatabaseService(DatabaseService):
    def __init__(self, base_service: DatabaseService):
        self.base_service = base_service
        self.metrics = {
            'get_count': 0,
            'save_count': 0,
            'delete_count': 0,
            'list_all_count': 0,
            'get_latency': [],
            'save_latency': [],
        }

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        start = time.time()
        try:
            result = self.base_service.get(db_name, doc_id)
            self.metrics['get_count'] += 1
            self.metrics['get_latency'].append(time.time() - start)
            return result
        except Exception as e:
            self.metrics['get_errors'] = self.metrics.get('get_errors', 0) + 1
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Return collected metrics."""
        return {
            'operations': {
                'get_count': self.metrics['get_count'],
                'save_count': self.metrics['save_count'],
                'delete_count': self.metrics['delete_count'],
            },
            'latency': {
                'get_avg': sum(self.metrics['get_latency']) / len(self.metrics['get_latency']) if self.metrics['get_latency'] else 0,
                'get_p95': self._calculate_percentile(self.metrics['get_latency'], 95),
            }
        }

    def _calculate_percentile(self, values, percentile):
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[index]
```

## Benchmarking

### Simple Benchmark Script

```python
import time
from services.database_service import get_database_service
from config import Settings

def benchmark_operations(db_service, num_operations=1000):
    """Benchmark database operations."""

    # Benchmark saves
    start = time.time()
    for i in range(num_operations):
        db_service.save("benchmark", f"doc-{i}", {"value": i})
    save_time = time.time() - start

    # Benchmark gets
    start = time.time()
    for i in range(num_operations):
        db_service.get("benchmark", f"doc-{i}")
    get_time = time.time() - start

    # Benchmark list_all
    start = time.time()
    docs = db_service.list_all("benchmark")
    list_time = time.time() - start

    # Benchmark deletes
    start = time.time()
    for i in range(num_operations):
        db_service.delete("benchmark", f"doc-{i}")
    delete_time = time.time() - start

    return {
        'save': {
            'total_time': save_time,
            'ops_per_sec': num_operations / save_time,
            'avg_latency': save_time / num_operations * 1000,  # ms
        },
        'get': {
            'total_time': get_time,
            'ops_per_sec': num_operations / get_time,
            'avg_latency': get_time / num_operations * 1000,  # ms
        },
        'list_all': {
            'total_time': list_time,
            'document_count': len(docs),
        },
        'delete': {
            'total_time': delete_time,
            'ops_per_sec': num_operations / delete_time,
            'avg_latency': delete_time / num_operations * 1000,  # ms
        }
    }

# Run benchmark
settings = Settings()
db = get_database_service(settings)
results = benchmark_operations(db, 1000)
print(f"Benchmark Results:\n{results}")
```

## Performance Best Practices

1. **Avoid N+1 Queries**: Use batch operations to fetch multiple documents
2. **Implement Pagination**: Don't fetch entire collections at once
3. **Use Indexes**: Add indexes for frequently queried fields
4. **Cache Hot Data**: Cache frequently accessed documents
5. **Connection Pooling**: Reuse connections to reduce overhead
6. **Batch Operations**: Group multiple operations when possible
7. **Monitor Performance**: Track metrics and set up alerts
8. **Optimize Document Size**: Keep documents small and focused
9. **Asynchronous Operations**: Use async I/O for concurrent requests
10. **Database-Specific Features**: Leverage native optimizations

## Performance Targets

### Latency Targets

| Operation | Target P50 | Target P95 | Target P99 |
|-----------|-----------|-----------|-----------|
| get() | < 10ms | < 50ms | < 100ms |
| save() | < 20ms | < 100ms | < 200ms |
| delete() | < 10ms | < 50ms | < 100ms |
| list_all() (100 docs) | < 50ms | < 200ms | < 500ms |

### Throughput Targets

| Operation | Target |
|-----------|--------|
| Reads/sec | > 1000 |
| Writes/sec | > 500 |
| Mixed workload | > 750 |

## Related Documentation

- [Configuration](configuration.md) - Database provider configuration
- [Testing](testing.md) - Performance testing strategies
- [Troubleshooting](troubleshooting.md) - Performance issues
- [Implementations](implementations/) - Provider-specific optimizations
- [Database Service README](README.md) - Overview

---

Last Updated: 2026-01-11
