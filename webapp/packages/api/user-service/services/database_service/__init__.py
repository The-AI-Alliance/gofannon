from .base import DatabaseService
from .couchdb import CouchDBService
from .memory import MemoryDBService
from .firestore import FirestoreDBService
from .dynamodb import DynamoDBService

__all__ = [
    'DatabaseService',
    'CouchDBService',
    'MemoryDBService',
    'FirestoreDBService',
    'DynamoDBService',
    'get_database_service',
]

# --- Service Factory ---

_db_instance = None


def get_database_service(settings) -> DatabaseService:
    """
    Factory function to get the appropriate database service instance based on settings.

    Args:
        settings: Application settings containing DATABASE_PROVIDER and related configuration

    Returns:
        DatabaseService: The configured database service instance

    Raises:
        ValueError: If required configuration is missing for the selected provider
    """
    global _db_instance
    if _db_instance is None:
        if settings.DATABASE_PROVIDER == "couchdb":
            if not all([settings.COUCHDB_URL, settings.COUCHDB_USER, settings.COUCHDB_PASSWORD]):
                raise ValueError("COUCHDB_URL, COUCHDB_USER, and COUCHDB_PASSWORD must be set for couchdb provider")
            _db_instance = CouchDBService(
                settings.COUCHDB_URL,
                settings.COUCHDB_USER,
                settings.COUCHDB_PASSWORD,
                settings
            )
        elif settings.DATABASE_PROVIDER == "firestore":
            _db_instance = FirestoreDBService()
        elif settings.DATABASE_PROVIDER == "dynamodb":
            # Get DynamoDB configuration from settings
            region_name = getattr(settings, 'DYNAMODB_REGION', None)
            endpoint_url = getattr(settings, 'DYNAMODB_ENDPOINT_URL', None)
            aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
            aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)

            _db_instance = DynamoDBService(
                region_name=region_name,
                endpoint_url=endpoint_url,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
        else:
            # Default to in-memory if not configured
            _db_instance = MemoryDBService()
    return _db_instance
