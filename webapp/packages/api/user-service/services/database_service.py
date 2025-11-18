import abc
from typing import Any, Dict, List
from fastapi import HTTPException
import couchdb

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

    def _get_or_create_db(self, db_name: str):
        try:
            return self.server[db_name]
        except couchdb.http.ResourceNotFound:
            print(f"Database '{db_name}' not found. Creating it.")
            return self.server.create(db_name)

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


class MemoryDBService(DatabaseService):
    """In-memory dictionary implementation for testing or when no DB is configured."""

    def __init__(self):
        self.dbs: Dict[str, Dict[str, Any]] = {}
        print("Using in-memory database service.")

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        if db_name not in self.dbs or doc_id not in self.dbs[db_name]:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{db_name}'")
        return self.dbs[db_name][doc_id]

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        if db_name not in self.dbs:
            self.dbs[db_name] = {}
        self.dbs[db_name][doc_id] = doc
        return {"id": doc_id, "rev": "memory-rev"}
    
    def delete(self, db_name: str, doc_id: str):
        if db_name in self.dbs and doc_id in self.dbs[db_name]:
            del self.dbs[db_name][doc_id]
        else:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found for deletion.")

    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        return list(self.dbs.get(db_name, {}).values())


# --- Service Factory ---

_db_instance = None

def get_database_service(settings) -> DatabaseService:
    global _db_instance
    if _db_instance is None:
        if settings.DATABASE_PROVIDER == "couchdb":
            if not all([settings.COUCHDB_URL, settings.COUCHDB_USER, settings.COUCHDB_PASSWORD]):
                raise ValueError("COUCHDB_URL, COUCHDB_USER, and COUCHDB_PASSWORD must be set for couchdb provider")
            _db_instance = CouchDBService(settings.COUCHDB_URL, settings.COUCHDB_USER, settings.COUCHDB_PASSWORD,settings)
        elif settings.DATABASE_PROVIDER == "firestore":
             _db_instance = FirestoreDBService()
        else:
            # Default to in-memory if not configured
            _db_instance = MemoryDBService()
    return _db_instance