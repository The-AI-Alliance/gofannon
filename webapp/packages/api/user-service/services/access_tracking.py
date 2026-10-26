"""Deferred access tracking for the data store.

The data store's read paths (``get``, ``get_all``, ``get_many``)
historically did a save-back inside the loop to bump an
``accessCount`` counter and stamp ``lastAccessedByAgent`` /
``lastAccessedAt``.  That turned a one-shot bulk read into N+1 round
trips and forked the doc revision on every read, defeating both the
HTTP-call savings of bulk APIs and CouchDB's compaction.

This module decouples the tracking from the read path: callers record
intent in an in-memory accumulator, and a periodic background flush
batches all pending updates into one ``save_many()`` call every 10
seconds.

Tradeoffs:

  * Counts are eventually-consistent.  A read followed immediately by
    ``get_all()`` may see a stale ``accessCount``.  Acceptable since
    the field is advisory metadata for the data-store viewer, not
    application-critical state.
  * Unflushed updates are lost on process exit.  No explicit shutdown
    hook because we don't have a graceful-shutdown path on the API
    yet, and adding one for this alone is overkill.  Worst case: the
    last 10 seconds of access counts disappear.
  * The accumulator is process-local.  In a multi-replica deployment
    each replica has its own buffer; counts converge over the next
    flush interval after they migrate to one writer.  Acceptable for
    the same advisory-metadata reason.

Concurrency: the accumulator's mutating methods are guarded by a
``threading.Lock``.  We don't expect contention to be high — the read
side does a single dict insert per access — but this is the simplest
correct model under FastAPI's async + thread-pool execution.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Dict, List, Optional, TYPE_CHECKING
from time_utils import naive_utc_now

if TYPE_CHECKING:
    from .database_service.base import DatabaseService

logger = logging.getLogger(__name__)

# How often the background task flushes accumulated accesses.  Lower
# means fresher counts but more frequent _bulk_docs calls; higher
# means staler counts and less DB work.  Ten seconds is the sweet
# spot for the workloads we see (audit pipelines doing big bulk
# reads in waves separated by minutes of LLM latency).
FLUSH_INTERVAL_SECONDS = 10.0


class AccessAccumulator:
    """Buffers (doc_id, agent_name, ts) accesses and flushes them in batches."""

    def __init__(self, db_service: "DatabaseService", db_name: str) -> None:
        self._db = db_service
        self._db_name = db_name
        # doc_id → (agent_name, last_ts, count_delta).  Multiple accesses
        # to the same doc within a flush window collapse: we keep only
        # the most recent agent_name + ts and sum the count delta.
        self._buffer: Dict[str, Dict[str, object]] = {}
        self._lock = threading.Lock()
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

    def record(self, doc_id: str, agent_name: Optional[str]) -> None:
        """Record a single access.  Cheap (one dict insert)."""
        if not doc_id or not agent_name:
            return
        ts = naive_utc_now().isoformat()
        with self._lock:
            entry = self._buffer.get(doc_id)
            if entry is None:
                self._buffer[doc_id] = {
                    "agent_name": agent_name,
                    "ts": ts,
                    "delta": 1,
                }
            else:
                # Same doc accessed again within the window — collapse.
                entry["agent_name"] = agent_name
                entry["ts"] = ts
                entry["delta"] = int(entry["delta"]) + 1

    def record_many(self, doc_ids: List[str], agent_name: Optional[str]) -> None:
        """Convenience wrapper for the bulk-read path."""
        if not agent_name:
            return
        for doc_id in doc_ids:
            self.record(doc_id, agent_name)

    def ensure_started(self) -> None:
        """Start the background flush task on first access.

        Lazy-start is correct because the AccessAccumulator may be
        instantiated outside an asyncio event loop (e.g., in tests)
        and we don't want construction to fail there.  The first
        record() call from inside an async context kicks off the
        loop.
        """
        if self._task is not None or self._stopped:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # No event loop yet — try again next time.
        self._task = loop.create_task(self._flush_loop())

    async def _flush_loop(self) -> None:
        while not self._stopped:
            try:
                await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
                await self.flush()
            except asyncio.CancelledError:
                # Final flush so we don't drop in-flight updates if a
                # shutdown hook ever cancels us.
                await self.flush()
                raise
            except Exception:
                # Never let a flush error kill the loop.
                logger.exception("AccessAccumulator: flush failed; continuing")

    async def flush(self) -> int:
        """Apply buffered accesses to the DB.  Returns count flushed.

        We snapshot the buffer under the lock, then do the DB work
        without holding it so concurrent record() calls aren't blocked
        on network latency.
        """
        with self._lock:
            if not self._buffer:
                return 0
            snapshot = self._buffer
            self._buffer = {}

        # Fetch current docs in one bulk call so we have the right
        # _rev to write back with.
        doc_ids = list(snapshot.keys())
        try:
            existing = self._db.get_many(self._db_name, doc_ids)
        except Exception:
            logger.exception(
                "AccessAccumulator: get_many failed; dropping %d updates",
                len(snapshot),
            )
            return 0

        updates: List[Dict[str, object]] = []
        for doc_id, entry in snapshot.items():
            doc = existing.get(doc_id)
            if doc is None:
                # Doc was deleted between read and flush.  Skip.
                continue
            doc["lastAccessedByAgent"] = entry["agent_name"]
            doc["lastAccessedAt"] = entry["ts"]
            doc["accessCount"] = int(doc.get("accessCount", 0)) + int(entry["delta"])
            updates.append(doc)

        if not updates:
            return 0

        try:
            results = self._db.save_many(self._db_name, updates)
        except Exception:
            logger.exception(
                "AccessAccumulator: save_many failed; %d updates lost",
                len(updates),
            )
            return 0

        ok = sum(1 for r in results if r.get("ok"))
        if ok < len(updates):
            logger.info(
                "AccessAccumulator: flushed %d/%d (some conflicts skipped)",
                ok, len(updates),
            )
        return ok

    def stop(self) -> None:
        """Stop the background loop.  Tests call this to avoid leaking tasks."""
        self._stopped = True
        if self._task is not None:
            self._task.cancel()
            self._task = None
