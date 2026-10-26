# webapp/packages/api/user-service/services/data_store_service.py

"""
Service for managing agent data store operations.

The data store allows agents to persist and share data across executions.
Data is scoped to users - all agents owned by a user can access the same data pool.
"""

import json
import sys
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from services.database_service import DatabaseService
from services.cancel_token import check_should_stop
from services.access_tracking import AccessAccumulator
from time_utils import naive_utc_now


# Database/collection name for data store records
DATA_STORE_DB = "agent_data_store"

# Standard indexes that every data store database should have.
# Each entry is (fields, index_name).
_STANDARD_INDEXES = [
    (["userId", "namespace"], "user-namespace-index"),
]


class DataStoreService:
    """Service for agent data store operations."""

    def __init__(self, db: DatabaseService):
        self.db = db
        # Background batcher for access-tracking metadata.  Keeps the
        # read paths off the write path; see services/access_tracking.py.
        self._access_accumulator = AccessAccumulator(db, DATA_STORE_DB)
        # Track namespaces we've already ensured indexes for so we
        # don't call ensure_index on every single write.
        self._indexed_namespaces: set = set()
        # Eagerly create the standard indexes on startup so that
        # queries are fast from the very first request.
        self._ensure_standard_indexes()

    def _ensure_standard_indexes(self) -> None:
        """Create the standard Mango / backend indexes for the data store.

        Called once at service init.  The underlying ensure_index is
        idempotent — it's a no-op if the index already exists.
        """
        for fields, name in _STANDARD_INDEXES:
            try:
                self.db.ensure_index(DATA_STORE_DB, fields, index_name=name)
            except Exception as e:
                # Best-effort — queries still work, just slower.
                print(f"Warning: could not ensure index {name}: {e}")

    def _ensure_namespace_indexed(self, user_id: str, namespace: str) -> None:
        """Ensure the standard index covers this user/namespace combination.

        The index on [userId, namespace] already covers all namespaces,
        so this method just records that we've seen the namespace to
        avoid redundant ensure_index calls.  If a backend ever needs
        per-namespace indexes this is the hook point.
        """
        cache_key = (user_id, namespace)
        if cache_key in self._indexed_namespaces:
            return
        # Re-ensure the standard index — idempotent, but guarantees
        # coverage even if the DB was recreated since init.
        for fields, name in _STANDARD_INDEXES:
            try:
                self.db.ensure_index(DATA_STORE_DB, fields, index_name=name)
            except Exception:
                pass
        self._indexed_namespaces.add(cache_key)

    def _make_doc_id(self, user_id: str, namespace: str, key: str) -> str:
        """Generate document ID from composite key."""
        import base64
        safe_key = base64.urlsafe_b64encode(key.encode()).decode()
        return f"{user_id}:{namespace}:{safe_key}"

    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        try:
            return sys.getsizeof(json.dumps(value))
        except (TypeError, ValueError):
            return 0

    def get(
        self,
        user_id: str,
        namespace: str,
        key: str,
        agent_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        check_should_stop()
        """Get a value from the data store."""
        doc_id = self._make_doc_id(user_id, namespace, key)

        try:
            doc = self.db.get(DATA_STORE_DB, doc_id)

            if agent_name and doc:
                doc["lastAccessedByAgent"] = agent_name
                doc["lastAccessedAt"] = naive_utc_now().isoformat()
                doc["accessCount"] = doc.get("accessCount", 0) + 1
                self.db.save(DATA_STORE_DB, doc_id, doc)

            return doc
        except HTTPException as e:
            if e.status_code == 404:
                return None
            raise

    def set(
        self,
        user_id: str,
        namespace: str,
        key: str,
        value: Any,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        check_should_stop()
        """Set a value in the data store.

        Optimistic-write: tries save() with no pre-read.  If the doc
        already exists and we don't have its _rev, the backend's save
        returns a 409.  We catch that, re-fetch the existing doc,
        merge our new value into it (preserving created* fields and
        merging metadata), and retry once.  In the common case
        (writing a fresh key, or a stale-rev-free update) this is one
        HTTP round trip instead of two.

        On a second consecutive conflict — which only happens when 3+
        writers race the same key — we surface the 409 to the caller
        rather than retry indefinitely.  That choice is deliberate:
        retrying forever masks bugs that produce contention; one retry
        absorbs the common race.
        """
        doc_id = self._make_doc_id(user_id, namespace, key)
        now = naive_utc_now()

        self._ensure_namespace_indexed(user_id, namespace)

        # Build the doc as-if-fresh first.  If the optimistic write
        # collides, we'll merge into the existing doc on retry.
        new_doc = {
            "_id": doc_id,
            "userId": user_id,
            "namespace": namespace,
            "key": key,
            "value": value,
            "metadata": metadata or {},
            "createdByAgent": agent_name,
            "lastAccessedByAgent": agent_name,
            "accessCount": 0,
            "createdAt": now.isoformat(),
            "updatedAt": now.isoformat(),
            "lastAccessedAt": now.isoformat() if agent_name else None,
        }

        try:
            saved = self.db.save(DATA_STORE_DB, doc_id, new_doc)
            new_doc["_rev"] = saved.get("rev")
            return new_doc
        except HTTPException as e:
            if e.status_code != 409:
                raise

        # Conflict: doc exists.  Re-fetch, merge, retry.
        existing = self.db.get(DATA_STORE_DB, doc_id)
        record_data = {
            **existing,
            "value": value,
            "updatedAt": now.isoformat(),
        }
        if metadata:
            record_data["metadata"] = {**existing.get("metadata", {}), **metadata}
        if agent_name:
            record_data["lastAccessedByAgent"] = agent_name
            record_data["lastAccessedAt"] = now.isoformat()

        saved = self.db.save(DATA_STORE_DB, doc_id, record_data)
        record_data["_rev"] = saved.get("rev")
        return record_data

    def delete(self, user_id: str, namespace: str, key: str) -> bool:
        check_should_stop()
        """Delete a value from the data store."""
        doc_id = self._make_doc_id(user_id, namespace, key)

        try:
            self.db.delete(DATA_STORE_DB, doc_id)
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            raise

    def list_keys(
        self,
        user_id: str,
        namespace: str,
        prefix: Optional[str] = None
    ) -> List[str]:
        """List all keys in a namespace.

        Uses an indexed query instead of scanning all documents.
        """
        check_should_stop()
        docs = self.db.find(
            DATA_STORE_DB,
            {"userId": user_id, "namespace": namespace},
            fields=["key"],
            limit=None,  # fetch ALL keys; a fixed cap silently truncates
                         # large namespaces (e.g. repos with >10k files),
                         # leaving orphaned docs after clear().
        )

        keys = [doc.get("key", "") for doc in docs]
        if prefix is not None:
            keys = [k for k in keys if k.startswith(prefix)]
        return sorted(keys)

    def list_namespaces(self, user_id: str) -> List[str]:
        """List all namespaces for a user.

        Uses an indexed query instead of scanning all documents.
        Returns a sorted list of all unique namespace names that contain
        data for the specified user. Useful for discovering what data
        exists before querying specific namespaces.
        """
        check_should_stop()
        docs = self.db.find(
            DATA_STORE_DB,
            {"userId": user_id},
            fields=["namespace"],
            limit=None,
        )
        namespaces = {doc.get("namespace") or "default" for doc in docs}
        return sorted(namespaces)

    def get_all(
        self,
        user_id: str,
        namespace: str,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return all key-value pairs in a namespace in one query.

        Access tracking, when ``agent_name`` is provided, is deferred
        to the AccessAccumulator: we record the doc IDs touched and
        a background task batches the count updates every 10 seconds.
        Previously this method did an inline save() per doc, turning
        a one-shot bulk read into N+1 HTTP calls and forking each
        doc's revision history.
        """
        check_should_stop()
        docs = self.db.find(
            DATA_STORE_DB,
            {"userId": user_id, "namespace": namespace},
            limit=None,
        )

        results = {}
        accessed_ids: List[str] = []
        for doc in docs:
            key = doc.get("key", "")
            results[key] = doc.get("value")
            if agent_name:
                doc_id = doc.get("_id") or self._make_doc_id(user_id, namespace, key)
                accessed_ids.append(doc_id)

        if accessed_ids:
            self._access_accumulator.ensure_started()
            self._access_accumulator.record_many(accessed_ids, agent_name)

        return results

    def get_many(
        self,
        user_id: str,
        namespace: str,
        keys: List[str],
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        check_should_stop()
        """Get multiple values at once.

        Uses the backend's bulk-fetch primitive (CouchDB
        _all_docs?keys=, etc.) for one round trip regardless of N.
        Access tracking is deferred to the AccessAccumulator; see
        get_all() for the rationale.
        """
        if not keys:
            return {}

        doc_ids = [self._make_doc_id(user_id, namespace, k) for k in keys]
        docs = self.db.get_many(DATA_STORE_DB, doc_ids)

        results: Dict[str, Any] = {}
        accessed_ids: List[str] = []
        for key, doc_id in zip(keys, doc_ids):
            doc = docs.get(doc_id)
            if doc is None:
                continue
            # Defensive: ensure the doc still belongs to this user/namespace.
            if doc.get("userId") != user_id or doc.get("namespace") != namespace:
                continue
            results[key] = doc.get("value")
            if agent_name:
                accessed_ids.append(doc_id)

        if accessed_ids:
            self._access_accumulator.ensure_started()
            self._access_accumulator.record_many(accessed_ids, agent_name)

        return results

    def set_many(
        self,
        user_id: str,
        items: List[Tuple[str, str, Any, Optional[Dict[str, Any]]]],
        agent_name: Optional[str] = None
    ) -> int:
        check_should_stop()
        """Set multiple values at once via the backend's bulk primitive.

        One get_many() to fetch existing docs (so we get _revs and
        can preserve created* fields), then one save_many() to ship
        the writes.  Two HTTP round trips total regardless of N,
        compared to the old loop-over-set() shape which was up to
        2N + index-ensure overhead.

        Per-doc conflicts surface in the result and are retried once
        each via set() (which has its own conflict handling).  If
        retries fail we count them as not-saved and return a smaller
        ``count``.

        Items are tuples of ``(namespace, key, value, metadata)``.
        """
        if not items:
            return 0

        # Prep: one ensure-index per unique namespace, doc_id list.
        unique_namespaces = {ns for ns, _, _, _ in items}
        for ns in unique_namespaces:
            self._ensure_namespace_indexed(user_id, ns)

        doc_ids = [self._make_doc_id(user_id, ns, key) for ns, key, _, _ in items]

        # One bulk fetch for any existing docs.
        existing_map = self.db.get_many(DATA_STORE_DB, doc_ids)

        now_iso = naive_utc_now().isoformat()
        new_docs: List[Dict[str, Any]] = []
        # Index from doc_id back to the items tuple so we can retry
        # the losers individually after the bulk save.
        item_by_id: Dict[str, Tuple[str, str, Any, Optional[Dict[str, Any]]]] = {}

        for (ns, key, value, metadata), doc_id in zip(items, doc_ids):
            existing = existing_map.get(doc_id)
            if existing:
                doc = {
                    **existing,
                    "value": value,
                    "updatedAt": now_iso,
                }
                if metadata:
                    doc["metadata"] = {**existing.get("metadata", {}), **metadata}
                if agent_name:
                    doc["lastAccessedByAgent"] = agent_name
                    doc["lastAccessedAt"] = now_iso
            else:
                doc = {
                    "_id": doc_id,
                    "userId": user_id,
                    "namespace": ns,
                    "key": key,
                    "value": value,
                    "metadata": metadata or {},
                    "createdByAgent": agent_name,
                    "lastAccessedByAgent": agent_name,
                    "accessCount": 0,
                    "createdAt": now_iso,
                    "updatedAt": now_iso,
                    "lastAccessedAt": now_iso if agent_name else None,
                }
            new_docs.append(doc)
            item_by_id[doc_id] = (ns, key, value, metadata)

        results = self.db.save_many(DATA_STORE_DB, new_docs)

        # Count successes, retry losers via set() (has conflict retry).
        count = 0
        for r in results:
            if r.get("ok"):
                count += 1
                continue
            # Retry — ResourceConflict is the expected reason; other
            # errors (network etc.) are still worth one retry too.
            doc_id = r.get("id")
            tup = item_by_id.get(doc_id)
            if tup is None:
                continue
            ns, key, value, metadata = tup
            try:
                self.set(user_id, ns, key, value, agent_name, metadata)
                count += 1
            except Exception:
                pass  # Best-effort; caller can retry the whole batch.

        return count

    def clear_namespace(self, user_id: str, namespace: str) -> int:
        """Delete all records in a namespace via one bulk call.

        Old shape: list_keys() + N delete() calls = N+1 round trips.
        New shape: list_keys() + one delete_many() = 2 round trips
        (or 3 because delete_many internally does a get_many to fetch
        _revs, but that's still O(1) regardless of N).
        """
        check_should_stop()
        keys = self.list_keys(user_id, namespace)
        if not keys:
            return 0
        doc_ids = [self._make_doc_id(user_id, namespace, k) for k in keys]
        results = self.db.delete_many(DATA_STORE_DB, doc_ids)
        return sum(1 for r in results if r.get("ok"))


    def delete_many(
        self,
        user_id: str,
        namespace: str,
        keys: List[str],
    ) -> int:
        check_should_stop()
        """Delete multiple keys at once via the backend's bulk primitive.

        One get_many() to fetch existing _revs, then one _bulk_docs
        call with delete markers. Two HTTP round trips regardless of
        N, vs. the per-key loop which was up to 3N (exists + get +
        delete) HTTP calls.

        Returns the count of keys successfully deleted. Missing keys
        are treated as already-deleted (idempotent), counted as
        successful.
        """
        if not keys:
            return 0
        doc_ids = [self._make_doc_id(user_id, namespace, key) for key in keys]
        results = self.db.delete_many(DATA_STORE_DB, doc_ids)
        return sum(1 for r in results if r.get("ok"))


class AgentDataStoreProxy:
    """
    Proxy class injected into agent execution context.
    Provides a clean API for agents to interact with the data store.

    When an ``ops_log`` list is passed in, every operation appends an entry
    so the sandbox UI can show a live timeline of reads and writes. The log
    is shared across the root proxy and any namespace-scoped copies returned
    by ``use_namespace`` — so ``data_store.use_namespace("x").set(...)`` and
    ``data_store.set(...)`` both land in the same list.
    """

    # Cap value previews so the ops log doesn't bloat on large records.
    # Full values are still written to the DB; this is display only.
    _VALUE_PREVIEW_MAX = 200

    def __init__(
        self,
        service: DataStoreService,
        user_id: str,
        agent_name: str,
        default_namespace: str = "default",
        ops_log: Optional[List[Dict[str, Any]]] = None,
    ):
        self._service = service
        self._user_id = user_id
        self._agent_name = agent_name
        self._namespace = default_namespace
        # Shared ops log (may be None when running outside the sandbox, e.g.
        # via the deployed-agent path where we don't surface ops to a UI).
        self._ops_log = ops_log

    def _preview(self, value: Any) -> Any:
        """Make a compact display-safe preview of a stored value."""
        if value is None:
            return None
        try:
            s = json.dumps(value)
        except (TypeError, ValueError):
            s = repr(value)
        if len(s) > self._VALUE_PREVIEW_MAX:
            return s[: self._VALUE_PREVIEW_MAX] + "…"
        return s

    def _log(self, op: str, **fields) -> None:
        if self._ops_log is None:
            return
        entry = {
            "op": op,
            "namespace": self._namespace,
            "agent": self._agent_name,
            "ts": naive_utc_now().isoformat(),
            **fields,
        }
        self._ops_log.append(entry)

    def use_namespace(self, namespace: str) -> "AgentDataStoreProxy":
        """Return a new proxy scoped to a specific namespace.

        Shares the same ops_log as the parent proxy so operations on the
        returned proxy still show up in the timeline.
        """
        return AgentDataStoreProxy(
            self._service,
            self._user_id,
            self._agent_name,
            namespace,
            ops_log=self._ops_log,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        record = self._service.get(
            self._user_id,
            self._namespace,
            key,
            self._agent_name
        )
        value = record.get("value") if record else default
        self._log(
            "get", key=key,
            found=bool(record),
            valuePreview=self._preview(value),
        )
        return value

    def set(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a value by key."""
        self._service.set(
            self._user_id,
            self._namespace,
            key,
            value,
            self._agent_name,
            metadata
        )
        self._log("set", key=key, valuePreview=self._preview(value))

    def delete(self, key: str) -> bool:
        """Delete a value by key."""
        result = self._service.delete(self._user_id, self._namespace, key)
        self._log("delete", key=key, found=result)
        return result

    def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys at once via the backend's bulk primitive.

        Use this instead of looping over delete() when you have a
        list of keys to remove (e.g. orphan cleanup after a partial
        rerun). One bulk call regardless of N. For wiping the whole
        namespace, use clear() instead -- it's even simpler.
        """
        count = self._service.delete_many(self._user_id, self._namespace, list(keys))
        self._log("delete_many", count=count, keys=list(keys)[:10])
        return count

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        keys = self._service.list_keys(self._user_id, self._namespace, prefix)
        self._log("list_keys", prefix=prefix, count=len(keys))
        return keys

    def list_namespaces(self) -> List[str]:
        """List all namespaces containing data for this user.

        Returns a sorted list of namespace names. Use this to discover
        what data exists before querying specific namespaces.

        Example:
            namespaces = data_store.list_namespaces()
            # Returns: ["default", "files:apache/repo", "summary:apache/repo", ...]
        """
        namespaces = self._service.list_namespaces(self._user_id)
        self._log("list_namespaces", count=len(namespaces))
        return namespaces

    def get_all(self) -> Dict[str, Any]:
        """Get all key-value pairs in the current namespace in one query.

        Much more efficient than list_keys() + get() per key when you
        need everything in the namespace.

        Example:
            ns_store = data_store.use_namespace("files:myrepo")
            all_files = ns_store.get_all()  # single indexed query
            for filepath, content in all_files.items():
                ...
        """
        result = self._service.get_all(
            self._user_id,
            self._namespace,
            self._agent_name
        )
        self._log("get_all", count=len(result))
        return result

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once."""
        result = self._service.get_many(
            self._user_id,
            self._namespace,
            keys,
            self._agent_name
        )
        self._log("get_many", requested=len(keys), found=len(result))
        return result

    def set_many(self, items: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> int:
        """Set multiple values at once."""
        item_list = [
            (self._namespace, key, value, metadata)
            for key, value in items.items()
        ]
        count = self._service.set_many(self._user_id, item_list, self._agent_name)
        self._log("set_many", count=count, keys=list(items.keys())[:10])
        return count

    def clear(self) -> int:
        """Clear all data in the current namespace."""
        count = self._service.clear_namespace(self._user_id, self._namespace)
        self._log("clear", count=count)
        return count


def get_data_store_service(db: DatabaseService) -> DataStoreService:
    """Factory function to create DataStoreService instance."""
    return DataStoreService(db)