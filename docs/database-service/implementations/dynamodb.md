# AWS DynamoDB

**File**: [dynamodb.py](../../../webapp/packages/api/user-service/services/database_service/dynamodb.py)

**Purpose**: Serverless NoSQL database for AWS deployments

## Implementation Details

```python
class DynamoDBService(DatabaseService):
    def __init__(self, region_name: str = "us-east-1", endpoint_url: str = None):
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=region_name,
            endpoint_url=endpoint_url  # For local DynamoDB
        )
        self.tables: Dict[str, Any] = {}
```

## Characteristics

- **Storage**: Cloud-native key-value and document database
- **Persistence**: Automatic with multi-AZ replication
- **Performance**: Single-digit millisecond latency
- **Revision Tracking**: Placeholder `"dynamodb-rev"` (uses conditional writes)
- **Auto-initialization**: Creates tables on first access with on-demand billing

## Configuration

```bash
# .env or environment variables
DATABASE_PROVIDER=dynamodb
DYNAMODB_REGION=us-east-1
DYNAMODB_ENDPOINT_URL=http://localhost:8000  # Optional, for local DynamoDB

# AWS credentials via standard AWS SDK methods:
# - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# - AWS credentials file (~/.aws/credentials)
# - IAM role (when running on EC2/ECS/Lambda)
```

## Local Development Setup

### Using DynamoDB Local

```bash
# Install DynamoDB Local with Docker
docker run -p 8000:8000 amazon/dynamodb-local

# Configure endpoint
export DYNAMODB_ENDPOINT_URL=http://localhost:8000
```

### AWS Credentials Setup

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Option 2: AWS CLI configuration
aws configure

# Option 3: IAM role (automatic on EC2/ECS/Lambda)
# No configuration needed
```

## Special Considerations

### 1. Table Auto-Creation

Creates tables on first access if they don't exist:

```python
def _ensure_table_exists(self, db_name: str):
    if db_name in self.tables:
        return

    try:
        table = self.dynamodb.Table(db_name)
        table.load()
        self.tables[db_name] = table
    except ClientError:
        # Table doesn't exist, create it
        table = self.dynamodb.create_table(
            TableName=db_name,
            KeySchema=[{"AttributeName": "_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        table.wait_until_exists()
        self.tables[db_name] = table
```

### 2. Partition Key

All tables use `_id` as the partition key:
- Hash-based distribution
- Single-attribute key (no sort key)

### 3. Billing Mode

Uses on-demand (PAY_PER_REQUEST) pricing:
- No capacity planning required
- Charged per request
- Alternative: provisioned capacity with auto-scaling

### 4. Decimal Conversion

DynamoDB requires Decimal for floating-point numbers:

```python
def _convert_floats_to_decimal(self, obj):
    """Recursively convert floats to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [self._convert_floats_to_decimal(item) for item in obj]
    return obj
```

### 5. Pagination

Handles large result sets in `list_all()`:

```python
response = table.scan()
items = response.get("Items", [])

# Handle pagination
while "LastEvaluatedKey" in response:
    response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
    items.extend(response.get("Items", []))
```

### 6. Type Conversions

DynamoDB uses custom types (boto3 handles this):
- Numbers: Stored as `Decimal`
- Binary: Stored as `Binary`
- Sets: Stored as DynamoDB sets
- Application sees standard Python types

## Production Recommendations

- Use IAM roles instead of access keys
- Enable point-in-time recovery (PITR) for backups
- Enable DynamoDB Streams for change data capture
- Use global tables for multi-region replication
- Monitor throttling metrics
- Consider provisioned capacity with auto-scaling for predictable workloads
- Use DAX (DynamoDB Accelerator) for read-heavy caching

## Cost Considerations

### On-Demand Pricing
- **Write Requests**: $1.25 per million write requests
- **Read Requests**: $0.25 per million read requests
- **Storage**: $0.25/GB/month
- **Free tier**: 25GB storage, 25 WCU, 25 RCU

### Provisioned Pricing
- **Write Capacity**: ~$0.47/month per WCU
- **Read Capacity**: ~$0.09/month per RCU
- **Storage**: $0.25/GB/month

### Cost Optimization Tips
1. Use on-demand for unpredictable workloads
2. Use provisioned for predictable workloads
3. Implement caching to reduce reads
4. Use batch operations to reduce request count
5. Monitor usage with CloudWatch

## Example Usage

```python
from services.database_service import get_database_service
from config import Settings

settings = Settings(
    DATABASE_PROVIDER="dynamodb",
    DYNAMODB_REGION="us-east-1"
)
db = get_database_service(settings)

# Save a document
result = db.save("agents", "agent-1", {
    "name": "My Agent",
    "code": "...",
    "usage_count": 42.5  # Will be converted to Decimal
})
print(result)  # {"id": "agent-1", "rev": "dynamodb-rev"}

# Retrieve the document
agent = db.get("agents", "agent-1")
print(agent)  # {"_id": "agent-1", "name": "My Agent", "usage_count": Decimal('42.5')}

# List all agents
all_agents = db.list_all("agents")

# Delete the agent
db.delete("agents", "agent-1")
```

## Common Operations

### Creating a Table Manually

```bash
aws dynamodb create-table \
  --table-name agents \
  --attribute-definitions AttributeName=_id,AttributeType=S \
  --key-schema AttributeName=_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Listing Tables

```bash
aws dynamodb list-tables --region us-east-1
```

### Describing a Table

```bash
aws dynamodb describe-table --table-name agents --region us-east-1
```

### Querying a Table

```bash
aws dynamodb get-item \
  --table-name agents \
  --key '{"_id": {"S": "agent-1"}}' \
  --region us-east-1
```

### Enabling Point-in-Time Recovery

```bash
aws dynamodb update-continuous-backups \
  --table-name agents \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --region us-east-1
```

### Enabling DynamoDB Streams

```bash
aws dynamodb update-table \
  --table-name agents \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --region us-east-1
```

## Troubleshooting

### Credentials Not Found

**Error**: `NoCredentialsError: Unable to locate credentials`

**Solutions**:
- Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
- Run `aws configure` to set up credentials
- Verify credentials file exists: `~/.aws/credentials`
- Use IAM role when running on AWS infrastructure

### Access Denied

**Error**: `AccessDeniedException: User is not authorized`

**Solutions**:
- Verify IAM permissions include DynamoDB access
- Check if user/role has `dynamodb:*` or specific permissions
- Ensure table exists in the correct region
- Verify endpoint URL is correct (for local DynamoDB)

### Table Already Exists

**Error**: `ResourceInUseException: Table already exists`

**Solutions**:
- This is handled automatically by the implementation
- If you see this error, the table may be in CREATING state
- Wait for table to be ACTIVE before retrying

### Provisioned Throughput Exceeded

**Error**: `ProvisionedThroughputExceededException: Throttled`

**Solutions**:
- Increase provisioned capacity (if using provisioned mode)
- Switch to on-demand billing mode
- Implement exponential backoff retry logic
- Use batch operations to reduce request count
- Monitor CloudWatch metrics for throttling

### Invalid Attribute Value

**Error**: `ValidationException: One or more parameter values were invalid`

**Solutions**:
- Ensure floats are converted to Decimal (implementation handles this)
- Check for empty string values (not allowed in DynamoDB)
- Verify attribute types match schema
- Check for null values in required fields

## Performance Tuning

### Batch Operations

Implement batch reads (up to 100 items):

```python
# Get multiple items at once
response = self.dynamodb.batch_get_item(
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

Implement batch writes (up to 25 items):

```python
# Put multiple items at once
with table.batch_writer() as batch:
    for i in range(25):
        batch.put_item(Item={'_id': f'agent-{i}', 'name': f'Agent {i}'})
```

### Use Query Instead of Scan

For better performance, use query() with indexes:

```python
# Create a GSI (Global Secondary Index)
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

# Query using GSI
response = table.query(
    IndexName='created_at-index',
    KeyConditionExpression=Key('created_at').eq('2024-01-15')
)
```

### Use DAX for Caching

Enable DAX for read-heavy workloads:

```python
import amazondax

# Connect to DAX cluster
dax = amazondax.AmazonDaxClient(
    endpoint_url='dax-cluster-endpoint:8111',
    region_name='us-east-1'
)

# Use DAX client instead of DynamoDB client
table = dax.Table('agents')
```

### Pagination for Large Scans

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

## Security Best Practices

1. **IAM Roles**: Use IAM roles instead of access keys
2. **Least Privilege**: Grant minimum required permissions
3. **Encryption**: Enable encryption at rest (default) and in transit (TLS)
4. **VPC Endpoints**: Use VPC endpoints to keep traffic private
5. **Audit Logging**: Enable CloudTrail for API logging
6. **Backup**: Enable point-in-time recovery
7. **Access Control**: Use IAM policies and resource-based policies
8. **Monitoring**: Set up CloudWatch alarms for anomalies

## Migration from Another Database

```python
from services.database_service import get_database_service
from config import Settings

# Source: CouchDB
source_settings = Settings(
    DATABASE_PROVIDER="couchdb",
    COUCHDB_URL="http://localhost:5984",
    COUCHDB_USER="admin",
    COUCHDB_PASSWORD="password"
)
source_db = get_database_service(source_settings)

# Target: DynamoDB
target_settings = Settings(
    DATABASE_PROVIDER="dynamodb",
    DYNAMODB_REGION="us-east-1"
)
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

        # Save to DynamoDB
        target_db.save(collection, doc_id, doc)
        print(f"  Migrated {doc_id}")

    print(f"Completed {collection}: {len(documents)} documents")
```

## Related Documentation

- [Configuration](../configuration.md) - Database provider configuration
- [Schema](../schema.md) - Collection and document schemas
- [Testing](../testing.md) - Testing strategies
- [Troubleshooting](../troubleshooting.md) - Common issues and solutions
- [Performance](../performance.md) - Performance optimization
- [AWS DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Boto3 DynamoDB Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html)

---

Last Updated: 2026-01-11
