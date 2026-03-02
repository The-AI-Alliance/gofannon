from typing import Any, Dict, List, Optional
from fastapi import HTTPException
import couchdb
from .base import DatabaseService


class CouchDBService(DatabaseService):
    """CouchDB implementation of the DatabaseService."""

    def __init__(self, url: str, user: str, password: str, settings):
        try:
            self.server = couchdb.Server(url)
            self.server.resource.credentials = (user, password)
            # Check if server is up
            self.server.version()
            print("Successfully connected to CouchDB server.")
        except Exception as e:
            print(f"Failed to connect to CouchDB server at {url}: {e}")
            raise ConnectionError(f"Could not connect to CouchDB: {e}") from e

        # Track which indexes have already been ensured this process lifetime
        # so we don't issue redundant HTTP calls to CouchDB on every save.
        # Key: (db_name, tuple(sorted(fields)))
        self._ensured_indexes: set = set()

    def _get_or_create_db(self, db_name: str):
        try:
            return self.server[db_name]
        except couchdb.http.ResourceNotFound:
            print(f"Database '{db_name}' not found. Creating it.")
            return self.server.create(db_name, n=1, q=2)

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        db = self._get_or_create_db(db_name)
        doc = db.get(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{db_name}'")
        return dict(doc)

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        db = self._get_or_create_db(db_name)
        # CouchDB requires _id to be part of the document
        doc["_id"] = doc_id
        # If the document already exists, we need its _rev to update it
        if doc_id in db:
            existing_doc = db[doc_id]
            doc["_rev"] = existing_doc.rev
        elif "_rev" in doc:
            del doc["_rev"]

        try:
            doc_id, rev = db.save(doc)
            return {"id": doc_id, "rev": rev}
        except couchdb.http.ResourceConflict as e:
             raise HTTPException(status_code=409, detail=f"Document update conflict: {e}")

    def delete(self, db_name: str, doc_id: str):
        db = self._get_or_create_db(db_name)
        if doc_id in db:
            doc = db[doc_id]
            db.delete(doc)
        else:
             raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found for deletion.")

    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        db = self._get_or_create_db(db_name)
        # Using a simple all-docs query. For more complex queries, a view would be needed.
        return [dict(row.doc) for row in db.view('_all_docs', include_docs=True)]

    def find(
        self,
        db_name: str,
        selector: Dict[str, Any],
        fields: Optional[List[str]] = None,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Query using CouchDB Mango selector (uses indexes instead of full scan).

        Falls back to the base-class in-Python filter if the Mango
        request fails for any reason (e.g. missing _find endpoint on
        an old CouchDB version).
        """
        try:
            db = self._get_or_create_db(db_name)
            query: Dict[str, Any] = {"selector": selector, "limit": limit}
            if fields:
                # Always include _id so callers can identify docs
                field_set = set(fields) | {"_id"}
                query["fields"] = list(field_set)
            return [dict(row) for row in db.find(query)]
        except Exception as e:
            print(f"CouchDB Mango find failed, falling back to list_all filter: {e}")
            return super().find(db_name, selector, fields, limit)

    def ensure_index(
        self,
        db_name: str,
        fields: List[str],
        index_name: Optional[str] = None,
    ) -> None:
        """Create a Mango index if it doesn't already exist.

        Idempotent — CouchDB ignores duplicate index creation, and we
        also track which indexes have been ensured this process lifetime
        so we don't make redundant HTTP calls on every save.
        """
        cache_key = (db_name, tuple(sorted(fields)))
        if cache_key in self._ensured_indexes:
            return

        try:
            db = self._get_or_create_db(db_name)
            name = index_name or f"idx-{'_'.join(fields)}"
            # CouchDB POST to _index is idempotent — if the index
            # already exists with the same definition it returns
            # {"result": "exists"} and does nothing.
            db.resource.post_json("_index", body={
                "index": {"fields": fields},
                "name": name,
                "type": "json",
            })
            self._ensured_indexes.add(cache_key)
        except Exception as e:
            # Index creation is best-effort — queries still work
            # (just slower) if the index is missing.
            print(f"Warning: failed to ensure index on {db_name} {fields}: {e}")