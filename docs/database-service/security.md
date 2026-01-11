# Security Best Practices

## General Security Principles

1. **Authentication**: Always require credentials for production databases
2. **Encryption**: Use TLS/SSL for connections
3. **Least Privilege**: Database user should have minimal required permissions
4. **Secrets Management**: Use environment variables or secret managers, never hardcode credentials
5. **Input Validation**: Validate document IDs and data before database operations
6. **Audit Logging**: Enable audit logs for compliance
7. **Network Security**: Restrict database access to application servers only
8. **Regular Updates**: Keep database software and client libraries updated

## Authentication and Authorization

### CouchDB Security

#### Enable Authentication

Never use admin party mode in production:

```bash
# Create admin user
curl -X PUT http://localhost:5984/_node/_local/_config/admins/admin \
  -d '"secure_password"'

# Verify authentication required
curl http://localhost:5984/_all_dbs
# Should return: {"error":"unauthorized","reason":"Authentication required."}
```

#### Create Application User

Don't use admin credentials for application:

```bash
# Create database-specific user
curl -X PUT http://admin:password@localhost:5984/_users/org.couchdb.user:app_user \
  -H "Content-Type: application/json" \
  -d '{
    "name": "app_user",
    "password": "app_password",
    "roles": ["app_role"],
    "type": "user"
  }'

# Grant permissions to database
curl -X PUT http://admin:password@localhost:5984/agents/_security \
  -H "Content-Type: application/json" \
  -d '{
    "admins": {
      "names": [],
      "roles": ["admin"]
    },
    "members": {
      "names": ["app_user"],
      "roles": ["app_role"]
    }
  }'
```

#### Use HTTPS

Configure reverse proxy (nginx) for TLS:

```nginx
server {
    listen 443 ssl;
    server_name couchdb.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5984;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Firestore Security

#### Service Account Security

Secure service account credentials:

```bash
# Store credentials securely
chmod 600 /path/to/service-account-key.json

# Use environment variable (don't hardcode path)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# In Kubernetes, use secrets
kubectl create secret generic firestore-key \
  --from-file=key.json=/path/to/service-account-key.json
```

#### IAM Roles

Use least privilege principle:

```bash
# Grant only required permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:SERVICE_ACCOUNT_EMAIL \
  --role=roles/datastore.user

# Don't use roles/owner or roles/editor
```

#### Firestore Security Rules

Implement granular access control:

```javascript
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth.uid == userId;
    }

    // Agents readable by authenticated users
    match /agents/{agentId} {
      allow read: if request.auth != null;
      allow write: if request.auth.token.admin == true;
    }

    // Service account has full access
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

#### VPC Service Controls

Restrict access to specific networks:

```bash
# Create service perimeter
gcloud access-context-manager perimeters create firestore-perimeter \
  --title="Firestore Access" \
  --resources=projects/PROJECT_ID \
  --restricted-services=firestore.googleapis.com
```

### DynamoDB Security

#### IAM Policies

Use least privilege IAM policies:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/agents",
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/users",
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/sessions"
      ]
    }
  ]
}
```

Attach to application role:
```bash
aws iam put-role-policy \
  --role-name app-role \
  --policy-name dynamodb-access \
  --policy-document file://policy.json
```

#### Use IAM Roles (Not Access Keys)

For EC2/ECS/Lambda:

```bash
# Create IAM role with DynamoDB policy
aws iam create-role \
  --role-name gofannon-app-role \
  --assume-role-policy-document file://trust-policy.json

# Attach DynamoDB policy
aws iam put-role-policy \
  --role-name gofannon-app-role \
  --policy-name dynamodb-access \
  --policy-document file://dynamodb-policy.json

# Attach role to EC2 instance
aws ec2 associate-iam-instance-profile \
  --instance-id i-1234567890abcdef0 \
  --iam-instance-profile Name=gofannon-app-role
```

#### Enable Encryption at Rest

Encryption is enabled by default, but you can use customer-managed keys:

```bash
aws dynamodb create-table \
  --table-name agents \
  --attribute-definitions AttributeName=_id,AttributeType=S \
  --key-schema AttributeName=_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/my-key
```

#### VPC Endpoints

Keep traffic within AWS network:

```bash
# Create VPC endpoint for DynamoDB
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-12345678 \
  --service-name com.amazonaws.us-east-1.dynamodb \
  --route-table-ids rtb-12345678
```

## Secrets Management

### Environment Variables

Never hardcode credentials:

```python
# Bad
db = CouchDBService("http://localhost:5984", "admin", "password")

# Good
import os
db = CouchDBService(
    os.environ["COUCHDB_URL"],
    os.environ["COUCHDB_USER"],
    os.environ["COUCHDB_PASSWORD"]
)
```

### AWS Secrets Manager

Store credentials in AWS Secrets Manager:

```python
import boto3
import json

def get_database_credentials():
    """Retrieve credentials from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-east-1')

    response = client.get_secret_value(SecretId='gofannon/database')
    secret = json.loads(response['SecretString'])

    return secret

# Usage
credentials = get_database_credentials()
db = CouchDBService(
    credentials['url'],
    credentials['username'],
    credentials['password']
)
```

### Google Secret Manager

Store credentials in Google Secret Manager:

```python
from google.cloud import secretmanager

def get_database_credentials():
    """Retrieve credentials from Google Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()

    name = "projects/PROJECT_ID/secrets/database-credentials/versions/latest"
    response = client.access_secret_version(request={"name": name})

    import json
    return json.loads(response.payload.data.decode('UTF-8'))

# Usage
credentials = get_database_credentials()
# Use credentials
```

### Kubernetes Secrets

Store credentials in Kubernetes secrets:

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: database-credentials
type: Opaque
stringData:
  couchdb-url: http://couchdb:5984
  couchdb-user: admin
  couchdb-password: secure_password
```

Use in deployment:
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gofannon-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: gofannon-api:latest
        env:
        - name: DATABASE_PROVIDER
          value: couchdb
        - name: COUCHDB_URL
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: couchdb-url
        - name: COUCHDB_USER
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: couchdb-user
        - name: COUCHDB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: database-credentials
              key: couchdb-password
```

## Input Validation

### Validate Document IDs

Prevent injection attacks:

```python
import re
from fastapi import HTTPException

def validate_document_id(doc_id: str) -> str:
    """Validate document ID format."""
    # Only allow alphanumeric, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9_-]+$', doc_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID format"
        )

    # Limit length
    if len(doc_id) > 100:
        raise HTTPException(
            status_code=400,
            detail="Document ID too long"
        )

    return doc_id

# Usage in API endpoint
@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str, db: DatabaseService = Depends(get_db)):
    agent_id = validate_document_id(agent_id)
    return db.get("agents", agent_id)
```

### Validate Collection Names

```python
ALLOWED_COLLECTIONS = ["agents", "deployments", "users", "sessions", "tickets", "demos"]

def validate_collection_name(collection: str) -> str:
    """Validate collection name is allowed."""
    if collection not in ALLOWED_COLLECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid collection: {collection}"
        )
    return collection
```

### Sanitize Document Data

```python
def sanitize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Remove potentially dangerous fields."""
    # Remove system fields
    sanitized = {k: v for k, v in doc.items() if not k.startswith('_')}

    # Validate field values
    for key, value in sanitized.items():
        if isinstance(value, str):
            # Limit string length
            if len(value) > 10000:
                raise HTTPException(
                    status_code=400,
                    detail=f"Field {key} exceeds maximum length"
                )

    return sanitized
```

## Network Security

### Firewall Rules

Restrict database access:

```bash
# CouchDB: Allow only application servers
sudo ufw allow from 10.0.1.0/24 to any port 5984

# Block public access
sudo ufw deny 5984
```

### Security Groups (AWS)

```bash
# Create security group for DynamoDB access
aws ec2 create-security-group \
  --group-name gofannon-database \
  --description "Database access for Gofannon"

# Allow outbound HTTPS for DynamoDB
aws ec2 authorize-security-group-egress \
  --group-id sg-12345678 \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### Network Policies (Kubernetes)

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-access
spec:
  podSelector:
    matchLabels:
      app: couchdb
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: gofannon-api
    ports:
    - protocol: TCP
      port: 5984
```

## Audit Logging

### CouchDB Audit Logging

Enable audit logging:

```ini
# local.ini
[log]
level = info
file = /var/log/couchdb/couch.log

[couch_httpd_auth]
secret = CHANGE_THIS_SECRET
timeout = 600

[httpd]
authentication_handlers = {couch_httpd_auth, cookie_authentication_handler}, {couch_httpd_auth, default_authentication_handler}
```

Monitor logs:
```bash
tail -f /var/log/couchdb/couch.log
```

### Firestore Audit Logging

Enable Cloud Audit Logs:

```bash
gcloud logging read "resource.type=cloud_firestore_database" \
  --limit 50 \
  --format json
```

### DynamoDB Audit Logging

Enable CloudTrail:

```bash
# Create trail
aws cloudtrail create-trail \
  --name gofannon-trail \
  --s3-bucket-name my-trail-bucket

# Enable logging for DynamoDB
aws cloudtrail put-event-selectors \
  --trail-name gofannon-trail \
  --event-selectors '[
    {
      "ReadWriteType": "All",
      "IncludeManagementEvents": true,
      "DataResources": [
        {
          "Type": "AWS::DynamoDB::Table",
          "Values": ["arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/*"]
        }
      ]
    }
  ]'
```

## Data Protection

### Encryption at Rest

**CouchDB**: Configure disk encryption at OS level

**Firestore**: Encrypted by default with Google-managed keys

**DynamoDB**: Encrypted by default, optionally use customer-managed keys:

```bash
aws dynamodb update-table \
  --table-name agents \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=alias/my-key
```

### Encryption in Transit

**CouchDB**: Use HTTPS with reverse proxy (nginx/Apache)

**Firestore**: Uses HTTPS by default

**DynamoDB**: Uses HTTPS by default

### Data Masking

Mask sensitive data in logs:

```python
import logging
import re

class MaskingFormatter(logging.Formatter):
    """Formatter that masks sensitive data."""

    PATTERNS = [
        (re.compile(r'"password":\s*"[^"]*"'), '"password": "***"'),
        (re.compile(r'"api_key":\s*"[^"]*"'), '"api_key": "***"'),
        (re.compile(r'[A-Za-z0-9+/]{40,}'), '***'),  # Likely keys/tokens
    ]

    def format(self, record):
        message = super().format(record)
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)
        return message

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(MaskingFormatter('%(levelname)s: %(message)s'))
logger = logging.getLogger()
logger.addHandler(handler)
```

## Backup and Recovery

### Regular Backups

**CouchDB**: Use replication for backups

```bash
curl -X POST http://admin:password@localhost:5984/_replicate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "agents",
    "target": "http://backup-server:5984/agents_backup",
    "create_target": true
  }'
```

**Firestore**: Export to Cloud Storage

```bash
gcloud firestore export gs://backup-bucket/firestore-backup
```

**DynamoDB**: Enable point-in-time recovery

```bash
aws dynamodb update-continuous-backups \
  --table-name agents \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### Test Recovery Procedures

Regularly test backup restoration:

```bash
# Test DynamoDB restore
aws dynamodb restore-table-from-backup \
  --target-table-name agents-restored \
  --backup-arn arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/agents/backup/12345

# Test Firestore import
gcloud firestore import gs://backup-bucket/firestore-backup
```

## Security Checklist

- [ ] Authentication enabled for all databases
- [ ] TLS/SSL configured for connections
- [ ] Least privilege IAM/permissions configured
- [ ] Secrets stored in secret manager (not code)
- [ ] Input validation implemented
- [ ] Audit logging enabled
- [ ] Network access restricted to application servers
- [ ] Regular security updates applied
- [ ] Backups configured and tested
- [ ] Encryption at rest enabled
- [ ] Encryption in transit enabled
- [ ] Security rules/policies configured (Firestore)
- [ ] VPC/network isolation configured
- [ ] Monitoring and alerting set up
- [ ] Incident response plan documented

## Related Documentation

- [Configuration](configuration.md) - Secure configuration practices
- [Troubleshooting](troubleshooting.md) - Security-related issues
- [Implementations](implementations/) - Provider-specific security
- [Database Service README](README.md) - Overview

---

Last Updated: 2026-01-11
