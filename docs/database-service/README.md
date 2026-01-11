# Gofannon Database Service Documentation

## Overview

The Gofannon database service provides a flexible, abstraction-based approach to data persistence. It supports multiple database backends through a common interface, allowing you to switch between database providers without changing application code.

**Current Supported Databases:**
- In-Memory (default for testing)
- Apache CouchDB
- Google Cloud Firestore
- AWS DynamoDB

## Documentation Structure

This documentation is organized into several focused guides:

### Core Documentation

1. **[Architecture](architecture.md)** - System design, patterns, and code structure
2. **[Database Interface](interface.md)** - Abstract base class and method specifications
3. **[Collections and Schema](schema.md)** - Data models and document structures
4. **[Configuration](configuration.md)** - Environment variables and setup

### Database Implementations

5. **[Memory Database](implementations/memory.md)** - In-memory storage for testing
6. **[CouchDB Implementation](implementations/couchdb.md)** - Apache CouchDB setup and usage
7. **[Firestore Implementation](implementations/firestore.md)** - Google Cloud Firestore setup
8. **[DynamoDB Implementation](implementations/dynamodb.md)** - AWS DynamoDB setup

### Development Guides

9. **[Implementing a New Database](implementing-new-database.md)** - Step-by-step guide for adding new backends
10. **[Testing Guide](testing.md)** - Unit tests, integration tests, and best practices

### Operations

11. **[Troubleshooting](troubleshooting.md)** - Common issues and solutions
12. **[Performance](performance.md)** - Optimization and monitoring
13. **[Security](security.md)** - Best practices and hardening
14. **[Migration](migration.md)** - Moving data between databases

## Quick Start

### For Development

Use the in-memory database (no setup required):

```bash
# Default configuration - uses memory database
cd webapp/packages/api/user-service
uvicorn main:app --reload
```

### For Production

Choose a database and configure it:

```bash
# Using CouchDB
export DATABASE_PROVIDER=couchdb
export COUCHDB_URL=http://localhost:5984
export COUCHDB_USER=admin
export COUCHDB_PASSWORD=password

# Start the application
uvicorn main:app --reload
```

See [Configuration](configuration.md) for detailed setup instructions.

## Key Concepts

### Database Abstraction

All database implementations inherit from a common `DatabaseService` abstract base class, providing four core methods:

- `get(db_name, doc_id)` - Retrieve a document
- `save(db_name, doc_id, doc)` - Create or update a document
- `delete(db_name, doc_id)` - Delete a document
- `list_all(db_name)` - List all documents in a collection

### Collections

The system uses six core collections:

| Collection | Purpose |
|------------|---------|
| `agents` | AI agent definitions and code |
| `deployments` | Agent deployment mappings |
| `users` | User profiles and billing |
| `sessions` | Chat conversation history |
| `tickets` | Async job tracking |
| `demos` | Demo application configs |

See [Collections and Schema](schema.md) for detailed structure.

### Factory Pattern

A factory function selects and instantiates the appropriate database implementation based on the `DATABASE_PROVIDER` environment variable:

```python
from services.database_service import get_database_service
from config import Settings

settings = Settings()
db = get_database_service(settings)

# Use the database (works with any implementation)
doc = db.get("agents", "agent-id")
```

## Common Tasks

### Switch Database Providers

1. Set `DATABASE_PROVIDER` environment variable
2. Configure provider-specific credentials
3. Restart the application

See [Configuration](configuration.md) for details.

### Implement a New Database

1. Create implementation class inheriting from `DatabaseService`
2. Implement all four abstract methods
3. Update factory function and configuration
4. Write tests

See [Implementing a New Database](implementing-new-database.md) for the complete guide.

### Migrate Data

Use the migration script to move data between databases:

```bash
python scripts/migrate_database.py \
  --source couchdb \
  --target dynamodb
```

See [Migration Guide](migration.md) for details.

## Additional Resources

### Code References

- Abstract base class: [base.py](../../webapp/packages/api/user-service/services/database_service/base.py)
- Factory function: [__init__.py](../../webapp/packages/api/user-service/services/database_service/__init__.py)
- Configuration: [config/__init__.py](../../webapp/packages/api/user-service/config/__init__.py)

### External Documentation

- **CouchDB**: https://docs.couchdb.org/
- **Firestore**: https://firebase.google.com/docs/firestore
- **DynamoDB**: https://docs.aws.amazon.com/dynamodb/

### Related Gofannon Documentation

- [LLM Provider Configuration](../llm-provider-configuration.md)
- [Developer Quickstart](../developers-quickstart.md)

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the specific implementation documentation
3. Open an issue on GitHub

---

**Documentation Version**: 1.0
**Last Updated**: 2026-01-11
**Maintainer**: Gofannon Development Team
