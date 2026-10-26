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
            return self.server.create(db_name)

    def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        db = self._get_or_create_db(db_name)
        doc = db.get(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in '{db_name}'")
        return dict(doc)

    def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Save a document.

        Caller is responsible for providing ``_rev`` when updating an
        existing document; if absent and the doc already exists,
        CouchDB returns a 409 conflict and we surface it as an
        HTTPException(409).  The previous implementation pre-fetched
        the existing doc to obtain ``_rev`` automatically, which
        doubled the HTTP cost of every write.  Service-layer code
        that wants the safety of automatic rev resolution should call
        ``DataStoreService.set()``, which handles conflict retry.
        """
        db = self._get_or_create_db(db_name)
        doc["_id"] = doc_id
        # If the doc has a _rev='', that's a serialization artifact;
        # treat it the same as missing.
        if not doc.get("_rev"):
            doc.pop("_rev", None)

        try:
            saved_id, rev = db.save(doc)
            return {"id": saved_id, "rev": rev}
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
        limit: Optional[int] = 10000,
    ) -> List[Dict[str, Any]]:
        """Query using CouchDB Mango selector (uses indexes instead of full scan).

        limit semantics:
          - an int: return at most that many rows (single request).
          - None:   return ALL matching rows, paginating with Mango
                    bookmarks. Use this for namespace-spanning operations
                    (list_keys, clear, get_all) where a fixed cap silently
                    truncates large namespaces — e.g. a repo with >10,000
                    files would otherwise only list/clear the first 10,000,
                    leaving orphaned stale docs behind.

        Falls back to the base-class in-Python filter if the Mango
        request fails for any reason (e.g. missing _find endpoint on
        an old CouchDB version).
        """
        try:
            db = self._get_or_create_db(db_name)
            field_list = None
            if fields:
                field_list = list(set(fields) | {"_id"})

            if limit is not None:
                query: Dict[str, Any] = {"selector": selector, "limit": limit}
                if field_list:
                    query["fields"] = field_list
                return [dict(row) for row in db.find(query)]

            # limit is None -> fetch ALL rows via bookmark pagination.
            # CouchDB returns a bookmark with every _find response; passing
            # it on the next request continues after the last row. A page
            # smaller than page_size (or an unchanged bookmark) means done.
            PAGE = 10000
            out: List[Dict[str, Any]] = []
            bookmark = None
            seen_bookmarks = set()
            while True:
                query = {"selector": selector, "limit": PAGE}
                if field_list:
                    query["fields"] = field_list
                if bookmark:
                    query["bookmark"] = bookmark
                # python-cloudant's db.find accepts bookmark in the query
                # dict and exposes the returned bookmark on the result;
                # fall back to raw _find if the bound method doesn't surface
                # it. We read rows first, then advance the bookmark.
                result = db.find(query)
                rows = [dict(row) for row in result]
                out.extend(rows)
                # Obtain the next bookmark. python-cloudant attaches it to
                # the QueryResult; if unavailable, stop to avoid a loop.
                next_bookmark = getattr(result, "bookmark", None)
                if not next_bookmark or next_bookmark in seen_bookmarks:
                    break
                seen_bookmarks.add(next_bookmark)
                bookmark = next_bookmark
                if len(rows) < PAGE:
                    break
            return out
        except Exception as e:
            print(f"CouchDB Mango find failed, falling back to list_all filter: {e}")
            return super().find(db_name, selector, fields,
                                 limit if limit is not None else 10**9)

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

    def save_many(
        self,
        db_name: str,
        docs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Bulk save via CouchDB _bulk_docs (one HTTP POST for N docs).

        Each input doc must include ``_id`` and, for updates, ``_rev``.
        Per-doc conflicts surface as ``{"ok": False, "id": ...,
        "error": "conflict"}`` entries; the call as a whole still
        succeeds.  Callers can retry just the losers.
        """
        if not docs:
            return []
        db = self._get_or_create_db(db_name)
        # Strip _rev='' so CouchDB doesn't treat it as a stale rev.
        for d in docs:
            if not d.get("_rev"):
                d.pop("_rev", None)

        results: List[Dict[str, Any]] = []
        try:
            # python-couchdb's update() returns one (success, id, rev_or_exc)
            # tuple per input doc, in order.
            for success, doc_id, rev_or_exc in db.update(docs):
                if success:
                    results.append({"ok": True, "id": doc_id, "rev": rev_or_exc})
                else:
                    err = type(rev_or_exc).__name__
                    if isinstance(rev_or_exc, couchdb.http.ResourceConflict):
                        err = "conflict"
                    results.append({"ok": False, "id": doc_id, "error": err})
            return results
        except Exception as exc:
            # Connection-level error — fall through to the base impl
            # which loops save().  Slower but keeps the writes flowing.
            print(f"CouchDB save_many failed, falling back to per-doc save: {exc}")
            return super().save_many(db_name, docs)

    def delete_many(
        self,
        db_name: str,
        doc_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Bulk delete via _bulk_docs with _deleted: true markers.

        We need each doc's current _rev to delete via _bulk_docs.  Fetch
        them first via _all_docs in one round trip, then submit the
        delete batch.  Total: 2 HTTP calls regardless of N.
        """
        if not doc_ids:
            return []
        db = self._get_or_create_db(db_name)

        # Fetch existing rev for each id.  Missing docs are silently
        # treated as already-deleted.
        existing = self.get_many(db_name, doc_ids)

        markers: List[Dict[str, Any]] = []
        results_index: Dict[str, int] = {}  # doc_id -> position in `results`
        results: List[Dict[str, Any]] = []
        for doc_id in doc_ids:
            results_index[doc_id] = len(results)
            doc = existing.get(doc_id)
            if doc is None:
                # Already gone.  Idempotent success.
                results.append({"ok": True, "id": doc_id})
                continue
            markers.append({"_id": doc_id, "_rev": doc["_rev"], "_deleted": True})
            # Placeholder, filled in after the bulk call.
            results.append({"ok": False, "id": doc_id, "error": "pending"})

        if not markers:
            return results

        try:
            for success, doc_id, rev_or_exc in db.update(markers):
                idx = results_index[doc_id]
                if success:
                    results[idx] = {"ok": True, "id": doc_id}
                else:
                    err = type(rev_or_exc).__name__
                    if isinstance(rev_or_exc, couchdb.http.ResourceConflict):
                        err = "conflict"
                    results[idx] = {"ok": False, "id": doc_id, "error": err}
            return results
        except Exception as exc:
            print(f"CouchDB delete_many failed, falling back to per-doc delete: {exc}")
            return super().delete_many(db_name, doc_ids)

    def get_many(
        self,
        db_name: str,
        doc_ids: List[str],
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Bulk fetch via _all_docs?keys=[...]&include_docs=true.

        One HTTP call regardless of N.  Missing docs map to None.
        """
        if not doc_ids:
            return {}
        db = self._get_or_create_db(db_name)
        try:
            out: Dict[str, Optional[Dict[str, Any]]] = {}
            for row in db.view("_all_docs", keys=doc_ids, include_docs=True):
                # Rows for missing docs have row.error set and row.doc=None.
                if getattr(row, "error", None) or row.doc is None:
                    out[row.key] = None
                else:
                    out[row.key] = dict(row.doc)
            # Ensure every requested id is present even if the view
            # somehow skipped one.
            for doc_id in doc_ids:
                out.setdefault(doc_id, None)
            return out
        except Exception as exc:
            print(f"CouchDB get_many failed, falling back to per-doc get: {exc}")
            return super().get_many(db_name, doc_ids)