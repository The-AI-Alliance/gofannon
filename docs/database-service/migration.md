# Migration Guide

## Overview

This guide covers migrating data between different database providers in Gofannon. Common scenarios include:

- Moving from development (memory) to production (CouchDB/Firestore/DynamoDB)
- Changing cloud providers
- Testing different database backends
- Backup and restore operations

## Migration Strategies

### 1. Direct Migration

Copy all data from source to target database using the database service API.

**Pros**:
- Simple to implement
- Works across any database pair
- No external dependencies

**Cons**:
- Requires both databases running simultaneously
- Slow for large datasets
- No built-in error recovery

### 2. Export/Import via JSON

Export to JSON files, then import to target database.

**Pros**:
- Databases don't need to be online simultaneously
- Can inspect/modify data between export and import
- Easy to version control small datasets
- Good for backups

**Cons**:
- Requires disk space
- Extra step in the process
- Need to handle large files

### 3. Database-Specific Replication

Use native replication tools when available.

**Pros**:
- Fastest for large datasets
- Built-in error handling
- Can be continuous

**Cons**:
- Only works within same database type
- Requires database-specific knowledge

## Direct Migration Script

### Basic Migration

```python
#!/usr/bin/env python3
"""
Migrate data between Gofannon database providers.

Usage:
    python migrate.py --source memory --target couchdb
    python migrate.py --source couchdb --target dynamodb --collections agents,users
"""

import argparse
from typing import List
from services.database_service import get_database_service
from config import Settings

# All Gofannon collections
ALL_COLLECTIONS = ["agents", "deployments", "users", "sessions", "tickets", "demos"]


def migrate_collection(source_db, target_db, collection: str, dry_run: bool = False):
    """Migrate a single collection."""
    print(f"\nMigrating collection: {collection}")

    # Get all documents from source
    try:
        documents = source_db.list_all(collection)
        print(f"  Found {len(documents)} documents")
    except Exception as e:
        print(f"  Error listing documents: {e}")
        return 0, 0

    if len(documents) == 0:
        print(f"  No documents to migrate")
        return 0, 0

    # Migrate each document
    success_count = 0
    error_count = 0

    for doc in documents:
        doc_id = doc.pop("_id")

        # Remove source-specific fields
        doc.pop("_rev", None)  # CouchDB revision
        doc.pop("_attachments", None)  # CouchDB attachments

        if dry_run:
            print(f"  [DRY RUN] Would migrate: {doc_id}")
            success_count += 1
            continue

        try:
            # Save to target database
            result = target_db.save(collection, doc_id, doc)
            print(f"  ✓ Migrated: {doc_id}")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {doc_id} - {str(e)}")
            error_count += 1

    return success_count, error_count


def migrate_database(
    source_provider: str,
    target_provider: str,
    collections: List[str] = None,
    dry_run: bool = False
):
    """Migrate data between database providers."""
    collections = collections or ALL_COLLECTIONS

    print(f"Migration Plan:")
    print(f"  Source: {source_provider}")
    print(f"  Target: {target_provider}")
    print(f"  Collections: {', '.join(collections)}")
    print(f"  Dry run: {dry_run}")

    # Get database services
    source_settings = Settings(DATABASE_PROVIDER=source_provider)
    target_settings = Settings(DATABASE_PROVIDER=target_provider)

    source_db = get_database_service(source_settings)
    target_db = get_database_service(target_settings)

    # Migrate each collection
    total_success = 0
    total_errors = 0

    for collection in collections:
        success, errors = migrate_collection(
            source_db, target_db, collection, dry_run
        )
        total_success += success
        total_errors += errors

    # Summary
    print(f"\n{'='*60}")
    print(f"Migration {'Plan' if dry_run else 'Complete'}:")
    print(f"  Total documents: {total_success + total_errors}")
    print(f"  Successful: {total_success}")
    print(f"  Failed: {total_errors}")

    if total_errors > 0:
        print(f"\n⚠️  {total_errors} documents failed to migrate")
        return False

    if not dry_run:
        print(f"\n✓ All documents migrated successfully")

    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate Gofannon database")
    parser.add_argument(
        "--source",
        required=True,
        choices=["memory", "couchdb", "firestore", "dynamodb"],
        help="Source database provider"
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=["memory", "couchdb", "firestore", "dynamodb"],
        help="Target database provider"
    )
    parser.add_argument(
        "--collections",
        help="Comma-separated list of collections (default: all)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )

    args = parser.parse_args()

    # Parse collections
    collections = None
    if args.collections:
        collections = [c.strip() for c in args.collections.split(",")]
        # Validate collection names
        invalid = [c for c in collections if c not in ALL_COLLECTIONS]
        if invalid:
            print(f"Error: Invalid collections: {', '.join(invalid)}")
            print(f"Valid collections: {', '.join(ALL_COLLECTIONS)}")
            return 1

    # Run migration
    success = migrate_database(
        args.source,
        args.target,
        collections,
        args.dry_run
    )

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
```

### Usage Examples

```bash
# Dry run to preview migration
python migrate.py --source memory --target couchdb --dry-run

# Migrate all collections from memory to CouchDB
python migrate.py --source memory --target couchdb

# Migrate specific collections
python migrate.py --source couchdb --target dynamodb --collections agents,users

# Migrate from Firestore to DynamoDB
python migrate.py --source firestore --target dynamodb
```

## Export/Import Migration

### Export Script

```python
#!/usr/bin/env python3
"""
Export Gofannon database to JSON files.

Usage:
    python export.py --output backup.json
    python export.py --provider couchdb --output couchdb-backup.json
"""

import argparse
import json
from datetime import datetime
from services.database_service import get_database_service
from config import Settings

ALL_COLLECTIONS = ["agents", "deployments", "users", "sessions", "tickets", "demos"]


def export_database(provider: str, output_file: str, collections: List[str] = None):
    """Export database to JSON file."""
    collections = collections or ALL_COLLECTIONS

    print(f"Exporting database:")
    print(f"  Provider: {provider}")
    print(f"  Output: {output_file}")
    print(f"  Collections: {', '.join(collections)}")

    # Get database service
    settings = Settings(DATABASE_PROVIDER=provider)
    db = get_database_service(settings)

    # Export data
    export_data = {
        "metadata": {
            "provider": provider,
            "exported_at": datetime.utcnow().isoformat(),
            "collections": collections
        },
        "data": {}
    }

    total_docs = 0

    for collection in collections:
        print(f"\nExporting {collection}...")
        try:
            documents = db.list_all(collection)
            print(f"  Found {len(documents)} documents")

            # Remove provider-specific fields
            clean_docs = []
            for doc in documents:
                clean_doc = {k: v for k, v in doc.items() if not k.startswith("_rev")}
                clean_docs.append(clean_doc)

            export_data["data"][collection] = clean_docs
            total_docs += len(documents)
        except Exception as e:
            print(f"  Error: {e}")
            export_data["data"][collection] = []

    # Write to file
    with open(output_file, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"Export complete:")
    print(f"  Total documents: {total_docs}")
    print(f"  Output file: {output_file}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Export Gofannon database")
    parser.add_argument(
        "--provider",
        default="memory",
        choices=["memory", "couchdb", "firestore", "dynamodb"],
        help="Database provider (default: memory)"
    )
    parser.add_argument(
        "--output",
        default="backup.json",
        help="Output file (default: backup.json)"
    )
    parser.add_argument(
        "--collections",
        help="Comma-separated list of collections (default: all)"
    )

    args = parser.parse_args()

    collections = None
    if args.collections:
        collections = [c.strip() for c in args.collections.split(",")]

    export_database(args.provider, args.output, collections)


if __name__ == "__main__":
    main()
```

### Import Script

```python
#!/usr/bin/env python3
"""
Import Gofannon database from JSON files.

Usage:
    python import.py --input backup.json --target couchdb
    python import.py --input backup.json --target dynamodb --collections agents
"""

import argparse
import json
from typing import List
from services.database_service import get_database_service
from config import Settings


def import_database(
    input_file: str,
    target_provider: str,
    collections: List[str] = None,
    dry_run: bool = False
):
    """Import database from JSON file."""
    print(f"Importing database:")
    print(f"  Input: {input_file}")
    print(f"  Target: {target_provider}")
    print(f"  Dry run: {dry_run}")

    # Read import file
    with open(input_file, "r") as f:
        import_data = json.load(f)

    metadata = import_data.get("metadata", {})
    data = import_data.get("data", {})

    print(f"\nImport file metadata:")
    print(f"  Source provider: {metadata.get('provider', 'unknown')}")
    print(f"  Exported at: {metadata.get('exported_at', 'unknown')}")

    # Get target database service
    settings = Settings(DATABASE_PROVIDER=target_provider)
    db = get_database_service(settings)

    # Filter collections if specified
    if collections:
        data = {k: v for k, v in data.items() if k in collections}

    # Import each collection
    total_success = 0
    total_errors = 0

    for collection, documents in data.items():
        print(f"\nImporting {collection}...")
        print(f"  Documents: {len(documents)}")

        for doc in documents:
            doc_id = doc.get("_id")
            if not doc_id:
                print(f"  ✗ Skipping document without _id")
                total_errors += 1
                continue

            # Remove _id from doc for save
            doc_data = {k: v for k, v in doc.items() if k != "_id"}

            if dry_run:
                print(f"  [DRY RUN] Would import: {doc_id}")
                total_success += 1
                continue

            try:
                db.save(collection, doc_id, doc_data)
                print(f"  ✓ Imported: {doc_id}")
                total_success += 1
            except Exception as e:
                print(f"  ✗ Failed: {doc_id} - {str(e)}")
                total_errors += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"Import {'Plan' if dry_run else 'Complete'}:")
    print(f"  Total documents: {total_success + total_errors}")
    print(f"  Successful: {total_success}")
    print(f"  Failed: {total_errors}")

    return total_errors == 0


def main():
    parser = argparse.ArgumentParser(description="Import Gofannon database")
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file"
    )
    parser.add_argument(
        "--target",
        required=True,
        choices=["memory", "couchdb", "firestore", "dynamodb"],
        help="Target database provider"
    )
    parser.add_argument(
        "--collections",
        help="Comma-separated list of collections (default: all in file)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing"
    )

    args = parser.parse_args()

    collections = None
    if args.collections:
        collections = [c.strip() for c in args.collections.split(",")]

    success = import_database(
        args.input,
        args.target,
        collections,
        args.dry_run
    )

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
```

### Usage Examples

```bash
# Export from CouchDB
python export.py --provider couchdb --output couchdb-backup.json

# Import to DynamoDB (dry run first)
python import.py --input couchdb-backup.json --target dynamodb --dry-run

# Import to DynamoDB
python import.py --input couchdb-backup.json --target dynamodb

# Import only specific collections
python import.py --input backup.json --target firestore --collections agents,users
```

## Database-Specific Migration

### CouchDB to CouchDB Replication

```bash
# One-time replication
curl -X POST http://admin:password@source:5984/_replicate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "http://admin:password@source:5984/agents",
    "target": "http://admin:password@target:5984/agents",
    "create_target": true
  }'

# Continuous replication
curl -X POST http://admin:password@source:5984/_replicate \
  -H "Content-Type: application/json" \
  -d '{
    "source": "http://admin:password@source:5984/agents",
    "target": "http://admin:password@target:5984/agents",
    "create_target": true,
    "continuous": true
  }'
```

### Firestore Export/Import

```bash
# Export
gcloud firestore export gs://backup-bucket/$(date +%Y%m%d)

# Import
gcloud firestore import gs://backup-bucket/20240115
```

### DynamoDB Backup/Restore

```bash
# Create on-demand backup
aws dynamodb create-backup \
  --table-name agents \
  --backup-name agents-backup-$(date +%Y%m%d)

# Restore from backup
aws dynamodb restore-table-from-backup \
  --target-table-name agents-restored \
  --backup-arn arn:aws:dynamodb:region:account:table/agents/backup/01234567890
```

## Migration Checklist

Before migration:

- [ ] Backup source database
- [ ] Test migration with dry run
- [ ] Verify target database is accessible
- [ ] Check sufficient resources (disk, memory, network)
- [ ] Plan for downtime if needed
- [ ] Notify users if applicable

During migration:

- [ ] Monitor migration progress
- [ ] Check for errors
- [ ] Verify document counts
- [ ] Sample check migrated data

After migration:

- [ ] Verify all collections migrated
- [ ] Compare document counts between source and target
- [ ] Run application tests against new database
- [ ] Update application configuration
- [ ] Monitor application performance
- [ ] Keep source database as backup (temporarily)
- [ ] Update documentation

## Rollback Plan

If migration fails or issues are discovered:

1. **Stop Application**: Prevent writes to target database
2. **Switch Configuration**: Point application back to source database
3. **Restart Application**: Verify it works with source
4. **Investigate Issues**: Review migration logs and errors
5. **Fix Issues**: Correct problems in migration script or target database
6. **Retry Migration**: After fixes, attempt migration again

## Common Issues

### Document ID Conflicts

**Issue**: Target database already has documents with same IDs

**Solution**:
```python
def safe_migrate(source_db, target_db, collection: str):
    """Migrate with conflict detection."""
    documents = source_db.list_all(collection)

    for doc in documents:
        doc_id = doc.pop("_id")

        try:
            # Check if document exists
            existing = target_db.get(collection, doc_id)
            print(f"  ⚠️  Document {doc_id} already exists, skipping")
            continue
        except HTTPException as e:
            if e.status_code == 404:
                # Document doesn't exist, safe to create
                target_db.save(collection, doc_id, doc)
            else:
                raise
```

### Large Dataset Timeouts

**Issue**: Migration times out on large collections

**Solution**: Migrate in batches
```python
def batch_migrate(source_db, target_db, collection: str, batch_size: int = 100):
    """Migrate in batches."""
    documents = source_db.list_all(collection)

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        print(f"  Migrating batch {i//batch_size + 1} ({len(batch)} docs)...")

        for doc in batch:
            doc_id = doc.pop("_id")
            target_db.save(collection, doc_id, doc)

        print(f"  ✓ Batch complete")
```

### Type Conversion Issues

**Issue**: Different databases handle types differently (e.g., Decimal in DynamoDB)

**Solution**: Convert types during migration
```python
from decimal import Decimal

def convert_for_target(doc: Dict, target_provider: str) -> Dict:
    """Convert document for target database."""
    if target_provider == "dynamodb":
        # Convert floats to Decimal for DynamoDB
        return convert_floats_to_decimal(doc)
    return doc
```

## Related Documentation

- [Configuration](configuration.md) - Database configuration for different providers
- [Implementations](implementations/) - Provider-specific details
- [Testing](testing.md) - Testing migration scripts
- [Troubleshooting](troubleshooting.md) - Migration issues
- [Database Service README](README.md) - Overview

---

Last Updated: 2026-01-11
