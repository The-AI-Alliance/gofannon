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
        limit: Optional[int] = 10000,
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
                if limit is not None and len(results) >= limit:
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

    # ------------------------------------------------------------------
    # Bulk APIs.  Default implementations loop the per-doc methods so
    # every backend works out of the box; backends that natively
    # support bulk should override for performance (CouchDB _bulk_docs,
    # DynamoDB BatchWriteItem, etc.).
    # ------------------------------------------------------------------

    def save_many(
        self,
        db_name: str,
        docs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Save multiple documents in a single backend call where supported.

        Args:
            db_name: Database / collection name.
            docs:    List of documents.  Each must include an ``_id``;
                     for updates, also include the current ``_rev``.

        Returns:
            List of result dicts in the same order as the input,
            each shaped ``{"id": doc_id, "rev": new_rev, "ok": True}``
            on success or ``{"id": doc_id, "error": "...", "ok": False}``
            on per-document failure.  The call as a whole only raises
            for connection-level errors; per-doc conflicts surface as
            ``ok=False`` entries so callers can retry just the losers.
        """
        results: List[Dict[str, Any]] = []
        for doc in docs:
            doc_id = doc.get("_id")
            if not doc_id:
                results.append({"ok": False, "id": None, "error": "missing _id"})
                continue
            try:
                saved = self.save(db_name, doc_id, doc)
                results.append({"ok": True, "id": doc_id, "rev": saved.get("rev")})
            except Exception as exc:
                results.append({"ok": False, "id": doc_id, "error": str(exc)})
        return results

    def delete_many(
        self,
        db_name: str,
        doc_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Delete multiple documents in a single backend call where supported.

        Returns a list of ``{"id": ..., "ok": bool, "error": ...?}``
        in the same order as ``doc_ids``.  Missing documents count as
        successful deletes (idempotent — semantically the doc is gone).
        """
        results: List[Dict[str, Any]] = []
        for doc_id in doc_ids:
            try:
                self.delete(db_name, doc_id)
                results.append({"ok": True, "id": doc_id})
            except Exception as exc:
                # Missing-doc deletes are not failures.
                msg = str(exc).lower()
                if "not found" in msg or "404" in msg:
                    results.append({"ok": True, "id": doc_id})
                else:
                    results.append({"ok": False, "id": doc_id, "error": str(exc)})
        return results

    def get_many(
        self,
        db_name: str,
        doc_ids: List[str],
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch multiple documents in a single backend call where supported.

        Returns a dict keyed by doc_id; missing documents are mapped
        to ``None`` rather than raising.  Backends that support bulk
        fetch (CouchDB _all_docs?keys=, DynamoDB BatchGetItem) should
        override; the default loops self.get() and swallows 404s.
        """
        out: Dict[str, Optional[Dict[str, Any]]] = {}
        for doc_id in doc_ids:
            try:
                out[doc_id] = self.get(db_name, doc_id)
            except Exception:
                out[doc_id] = None
        return out