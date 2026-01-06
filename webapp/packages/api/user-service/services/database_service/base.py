import abc
from typing import Any, Dict, List


class DatabaseService(abc.ABC):
    """Abstract base class for a generic database service."""

    @abc.abstractmethod
    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        """Retrieve a document by its ID."""
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Save (create or update) a document."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, db_name: str, doc_id: str):
        """Delete a document by its ID."""
        raise NotImplementedError

    @abc.abstractmethod
    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        """List all documents in a database/collection."""
        raise NotImplementedError
