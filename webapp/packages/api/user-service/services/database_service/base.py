import abc
from typing import Any, Dict, List, Optional


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

    def find(
        self,
        db_name: str,
        selector: Dict[str, Any],
        fields: Optional[List[str]] = None,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Query documents matching a selector.

        The default implementation falls back to list_all + in-Python
        filtering.  Backends that support server-side queries (CouchDB
        Mango, Firestore where, DynamoDB filter expressions) should
        override this for performance.

        Args:
            db_name:  Database / collection / table name.
            selector: Dict of field → value equality filters.
            fields:   Optional list of fields to return (projection).
            limit:    Maximum number of documents to return.

        Returns:
            List of matching documents (as dicts).
        """
        all_docs = self.list_all(db_name)
        results = []
        for doc in all_docs:
            if all(doc.get(k) == v for k, v in selector.items()):
                if fields:
                    results.append({f: doc.get(f) for f in fields})
                else:
                    results.append(doc)
                if len(results) >= limit:
                    break
        return results

    def ensure_index(
        self,
        db_name: str,
        fields: List[str],
        index_name: Optional[str] = None,
    ) -> None:
        """Ensure an index exists on the given fields.

        No-op by default.  Backends that support index creation (e.g.
        CouchDB Mango) should override this.
        """
        pass