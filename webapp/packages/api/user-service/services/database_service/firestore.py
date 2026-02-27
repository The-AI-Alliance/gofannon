from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from firebase_admin import firestore
from .base import DatabaseService


class FirestoreDBService(DatabaseService):
    """Firestore implementation of the DatabaseService."""

    def __init__(self):
        try:
            self.db = firestore.client()
            print("Successfully connected to Firestore.")
        except Exception as e:
            print(f"Failed to connect to Firestore: {e}")
            raise ConnectionError(f"Could not connect to Firestore: {e}") from e

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        doc_ref = self.db.collection(db_name).document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{db_name}'")

        data = doc.to_dict()
        # Firestore doesn't store the ID in the doc, so we add it back
        # MODIFICATION: Use '_id' to match the Pydantic model's alias.
        data['_id'] = doc.id
        return data

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        doc_ref = self.db.collection(db_name).document(doc_id)
        # The document being saved already contains '_id' from model_dump(by_alias=True)
        doc_ref.set(doc)
        # Firestore 'rev' is not really a concept, so we return a placeholder
        return {"id": doc_id, "rev": "firestore-rev"}

    def delete(self, db_name: str, doc_id: str):
        doc_ref = self.db.collection(db_name).document(doc_id)
        if not doc_ref.get().exists:
             raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found for deletion.")
        doc_ref.delete()

    def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        docs_stream = self.db.collection(db_name).stream()
        # MODIFICATION: Iterate and add the document ID to each result.
        results = []
        for doc in docs_stream:
            data = doc.to_dict()
            # This is the critical fix. The document ID must be included.
            # Use '_id' to match the Pydantic model's alias.
            data['_id'] = doc.id
            results.append(data)
        return results

    def find(
        self,
        db_name: str,
        selector: Dict[str, Any],
        fields: Optional[List[str]] = None,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Query using Firestore's native where() filters.

        Firestore automatically indexes all fields, so equality
        queries are efficient without explicit index creation.
        Composite queries on 2+ fields may require a composite index
        in Firestore — these are created automatically or via the
        Firebase console when first needed.
        """
        try:
            query = self.db.collection(db_name)
            for field, value in selector.items():
                query = query.where(field, "==", value)
            query = query.limit(limit)

            results = []
            for doc in query.stream():
                data = doc.to_dict()
                data["_id"] = doc.id
                if fields:
                    data = {f: data.get(f) for f in set(fields) | {"_id"}}
                results.append(data)
            return results
        except Exception as e:
            print(f"Firestore find failed, falling back to list_all filter: {e}")
            return super().find(db_name, selector, fields, limit)