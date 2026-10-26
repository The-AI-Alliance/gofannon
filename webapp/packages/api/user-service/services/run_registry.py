"""Run registry — in-process record of agent runs.

A ``RunRecord`` holds everything the runs UX needs to display, replay, and
cancel an in-flight or recently-completed agent run. The
``RunRegistry`` is a singleton (per process) that owns the records.

Design constraints:

- **Single process.** Records live in memory. A multi-replica deployment
  would need sticky sessions or a shared store; that's out of scope for
  Phase 1 (issue text calls this out explicitly).
- **Closing the SSE connection does not kill the run.** Each record's
  asyncio Task runs independently of any subscriber. The registry holds
  a strong reference so the task isn't GC'd. The SSE response is a thin
  subscriber that reads events from a per-record subscriber queue.
- **Replay-then-live.** A new subscriber sees every event already in
  ``record.trace.events`` (replay), then transitions to live consumption
  via its own queue. Multiple subscribers per record are supported —
  each gets its own queue, attached to the trace via ``Trace.attach_queue``
  semantics. (Today Trace only supports one queue; this module wraps that
  by fanning out at append-time. See ``_FanoutTrace`` below.)
- **Eviction.** On completion, the record stays in memory for
  ``EVICTION_TTL_SECONDS`` (default 3600). After that, it's evicted —
  callers asking for it get 404. Persistence to CouchDB is a follow-up.
- **Auth scoping.** Records track ``user_id``. Lookup-by-id callers must
  check ownership before exposing the record. Widening this to
  workspace membership is a later change.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Set

from services.agent_trace import Trace
from time_utils import naive_utc_now


# persistence: each worker process gets a stable identity
# generated at module import. Used to mark which worker owns each
# in-flight run so the stop-polling task can scan only its own runs
# in CouchDB rather than every running record in the registry. The
# value persists for the lifetime of the worker process and is lost
# on restart, which is the correct behavior -- a restarted worker
# is a different worker as far as cancel-token ownership is
# concerned, since the in-memory token dict is gone.
WORKER_ID = uuid.uuid4().hex

# Test-mode flag: when reset_run_registry_for_tests is called, this
# flips to True for the rest of the process lifetime. Any RunRegistry
# constructed while it's True skips the DB lookup in _get_db and
# operates purely in-memory. Lets unit tests exercise the registry
# without standing up CouchDB and without test records contaminating
# a real DB.
_test_mode_no_db = False

# Local in-memory cache TTL for completed records. The CouchDB
# record is the source of truth for completed runs; we keep a brief
# local cache so back-to-back reads (typical when a UI page renders
# right after completion) don't re-fetch.
LOCAL_CACHE_TTL_SECONDS = 300  # 5 minutes

# Backwards-compat alias for the constant the pre-persistence code
# called EVICTION_TTL_SECONDS. The name was specific to the old
# meaning -- a single in-memory eviction TTL of 1 hour -- which now
# split into LOCAL_CACHE_TTL_SECONDS (in-memory cache evict) and
# COUCH_RETENTION_SECONDS (CouchDB eviction). External callers
# (notably tests/unit/services/test_run_registry.py) imported the
# old name; keep it pointing at the local cache TTL so existing
# call sites that backdate _completed_at_monotonic past this value
# still trigger eviction the way they expect.
EVICTION_TTL_SECONDS = LOCAL_CACHE_TTL_SECONDS

# CouchDB retention for completed runs. Runs older than this get
# evicted by the periodic eviction task in app_factory's lifespan.
COUCH_RETENTION_SECONDS = 7 * 24 * 3600  # 7 days

# CouchDB database that holds run records. Separate DB from the
# data store so each can be backed up, queried, and reasoned about
# independently. Created on first write via the standard
# ensure-db-exists behavior of the database service.
RUN_REGISTRY_DB = "gofannon_runs"

DONE_SENTINEL = object()


# Indexes created on first persistence call. Idempotent at the
# database_service level, but we still guard with a module flag to
# skip the call entirely on subsequent uses.
_indexes_ensured = False


def _ensure_indexes(db) -> None:
    """Create the indexes the registry needs. Idempotent."""
    global _indexes_ensured
    if _indexes_ensured:
        return
    # Polling task: 'find my owned in-flight runs that need stopping'.
    db.ensure_index(RUN_REGISTRY_DB, ["worker_id", "status"],
                    index_name="by_worker_status")
    # List endpoint: 'find runs for this user, optionally filtered by
    # agent_id, ordered by started_at descending'.
    db.ensure_index(RUN_REGISTRY_DB, ["user_id", "agent_id", "started_at"],
                    index_name="by_user_agent")
    # Eviction: 'find completed runs older than N days'.
    db.ensure_index(RUN_REGISTRY_DB, ["status", "completed_at"],
                    index_name="by_status_completed")
    _indexes_ensured = True


class _FanoutTrace(Trace):
    """A Trace that supports multiple attached subscriber queues.

    The base ``Trace.attach_queue`` overwrites the single queue slot. We
    need fanout for the registry: a long-lived "live" queue is consumed
    by SSE subscribers, and new subscribers also get the existing
    ``self.events`` list replayed before going live. Each subscriber's
    own queue is set via ``add_subscriber``; removal via
    ``remove_subscriber``.

    Path A integration: each subscriber tracks the loop that owns its
    queue. When append() fires from a thread other than the queue\'s
    owning loop (the executor runs the agent on a side thread), the
    put_nowait is routed through call_soon_threadsafe so the queue is
    only mutated by its owning loop. When no loop is provided
    (legacy callers), behavior is the original direct put_nowait.
    """

    def __init__(self) -> None:
        super().__init__()
        # subscriber → optional owning_loop. None means "emit from any
        # thread without bridging" (the legacy code path before
        # Path A).
        self._subscribers: Dict[asyncio.Queue, Optional[asyncio.AbstractEventLoop]] = {}

    def add_subscriber(
        self,
        queue: asyncio.Queue,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._subscribers[queue] = loop

    def remove_subscriber(self, queue: asyncio.Queue) -> None:
        self._subscribers.pop(queue, None)

    def append(self, event: Dict[str, Any]) -> None:
        # Append to the immutable history first (parent stores in
        # self.events), then fan out to subscribers.
        super().append(event)
        for q, loop in list(self._subscribers.items()):
            if loop is not None:
                # Route the put via the queue\'s owning loop. Safe
                # even when we\'re already on that loop\'s thread.
                loop.call_soon_threadsafe(self._safe_subscriber_put, q, event)
            else:
                try:
                    q.put_nowait(event)
                except Exception:
                    # Queue full or closed; drop the event for that
                    # subscriber rather than blocking other emitters.
                    pass

    @staticmethod
    def _safe_subscriber_put(queue: asyncio.Queue, event: Dict[str, Any]) -> None:
        try:
            queue.put_nowait(event)
        except Exception:
            pass


@dataclass
class RunRecord:
    """One agent run's full state."""

    run_id: str
    user_id: str
    agent_name: str
    # CouchDB doc id of the saved agent this run came from, when applicable.
    # None for runs initiated from the create-flow sandbox (no saved agent yet).
    # Used by the runs UI to deep-link to the per-agent runs page.
    agent_id: Optional[str] = None
    # The input dict the run was launched with. Stored so the runs UI
    # can pre-fill the form when revisiting a past run via deep link.
    # None for old records that predate this field.
    input_dict: Optional[Dict[str, Any]] = None
    started_at: datetime = field(default_factory=naive_utc_now)
    status: Literal["running", "success", "error", "stopped"] = "running"
    trace: _FanoutTrace = field(default_factory=_FanoutTrace)
    task: Optional[asyncio.Task] = None  # Set by the registry on register
    result: Optional[Any] = None
    error: Optional[str] = None
    schema_warnings: Optional[List[str]] = None
    ops_log: Optional[List[Dict[str, Any]]] = None
    completed_at: Optional[datetime] = None
    # Wall-clock timestamp (time.monotonic) for cheap eviction comparison.
    _completed_at_monotonic: Optional[float] = None
    # persistence: which worker owns the live cancel token
    # for this run. Used by the stop-polling task to scope its
    # CouchDB query to runs this worker can actually act on. When a
    # record is loaded from CouchDB on a non-owning worker (e.g. for
    # display in the runs UI) this field reflects the persisted
    # owner, not the local worker.
    worker_id: str = field(default_factory=lambda: WORKER_ID)
    # cross-worker stop: the stop endpoint flips this to
    # True on the CouchDB record. The owning worker's polling task
    # observes the change and flips its local cancel token. For
    # local fast-path stops (when the stop request lands on the
    # owning worker) the cancel token is flipped immediately and
    # stop_requested is still written to CouchDB so the record
    # reflects what happened.
    stop_requested: bool = False
    # Flag used by mark_complete to skip re-persisting an already-
    # completed record (defensive against double-call).
    _persisted_complete: bool = False

    def to_summary(self) -> Dict[str, Any]:
        """Subset suitable for list endpoints — no events, no result body.

        Does include inputDict and error so the per-agent past-runs UI
        can render an input preview and inline error message without
        firing N+1 full-record fetches for each row.
        """
        return {
            "runId": self.run_id,
            "agentId": self.agent_id,
            "agentName": self.agent_name,
            "status": self.status,
            "startedAt": self.started_at.isoformat(),
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "inputDict": self.input_dict,
            "error": self.error,
        }

    def to_full(self) -> Dict[str, Any]:
        return {
            **self.to_summary(),
            "events": list(self.trace.events),
            "result": self.result,
            "error": self.error,
            "schemaWarnings": self.schema_warnings,
            "opsLog": self.ops_log,
            # inputDict echoes the input the run was launched with so
            # the runs UI can pre-fill its form when a user revisits a
            # past run via deep link.
            "inputDict": self.input_dict,
        }


    def to_couch_doc(self, include_events: bool = False) -> Dict[str, Any]:
        """Serialize for CouchDB. Only persistable fields; no asyncio
        Task, no live Trace queues, no cancel-token reference (the
        token lives in run_cancel_registry keyed by run_id).

        include_events controls whether the trace events list ships
        with the doc. Set True only on completion -- in-flight writes
        skip events to keep the per-write payload small (events
        accumulate during the run and can reach tens of KB; writing
        them on every state change would create amplification).
        """
        doc = {
            "_id": self.run_id,
            "type": "run",
            "run_id": self.run_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "input_dict": self.input_dict,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "worker_id": self.worker_id,
            "stop_requested": self.stop_requested,
            "result": self.result,
            "error": self.error,
            "schema_warnings": self.schema_warnings,
            "ops_log": self.ops_log,
        }
        if include_events:
            doc["events"] = list(self.trace.events)
        return doc

    @classmethod
    def from_couch_doc(cls, doc: Dict[str, Any]) -> "RunRecord":
        """Reconstruct from a CouchDB document.

        The reconstructed record is *view-only*: it has no task, no
        cancel token, and its Trace is a fresh fanout instance pre-
        populated with the persisted events (so SSE replay still
        works). Live-tailing an in-flight run owned by another worker
        is not supported; callers should treat such records as
        readable but not subscribable.
        """
        from datetime import datetime as _dt
        rec = cls(
            run_id=doc["run_id"],
            user_id=doc["user_id"],
            agent_name=doc["agent_name"],
            agent_id=doc.get("agent_id"),
            input_dict=doc.get("input_dict"),
        )
        # Override defaults set by dataclass init
        rec.started_at = _dt.fromisoformat(doc["started_at"])
        if doc.get("completed_at"):
            rec.completed_at = _dt.fromisoformat(doc["completed_at"])
        rec.status = doc.get("status", "running")
        rec.worker_id = doc.get("worker_id", "")
        rec.stop_requested = bool(doc.get("stop_requested", False))
        rec.result = doc.get("result")
        rec.error = doc.get("error")
        rec.schema_warnings = doc.get("schema_warnings")
        rec.ops_log = doc.get("ops_log")
        # Populate the trace with persisted events so SSE replay works
        # for completed-run deep links from other workers.
        events = doc.get("events") or []
        if events:
            rec.trace.events.extend(events)
        rec._persisted_complete = doc.get("status") in ("success", "error", "stopped")
        return rec


class RunRegistry:
    """Registry of RunRecords backed by CouchDB.

    Local in-memory cache holds the full record (including the live
    Trace with subscriber queues, the asyncio Task, and the cancel
    token reference) only on the worker that owns the in-flight run.
    Other workers that need to *display* a run read its CouchDB doc
    and reconstruct a view-only RunRecord via
    ``RunRecord.from_couch_doc``.

    Stop semantics:
        POST /runs/<id>/stop hits some worker (chosen by the load
        balancer). That worker calls ``request_stop``, which writes
        stop_requested=true to the CouchDB doc. If the worker also
        owns the local cancel token (fast path) it flips the token
        immediately. The owning worker's polling task
        (``poll_owned_stops`` in app_factory's lifespan) reads its
        own in-flight runs and flips local tokens for any newly
        flagged.
    """

    def __init__(self, db=None) -> None:
        # In-memory cache. For OWNED records this holds the live
        # RunRecord with task / trace / etc. For records reconstructed
        # from CouchDB on this worker (e.g. for read endpoints) we
        # cache briefly to avoid re-fetching on close-together reads
        # by the polling UI.
        self._records: Dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()
        # Lazy DB binding; set on first persistence operation when
        # the caller has access to settings. Tests can pass None.
        self._db = db
        # Test-mode short-circuit: if the test fixture flipped the
        # module flag, never try to look up a DB. Lets unit tests
        # exercise the in-memory path even now that the production
        # 'from config import settings' import actually succeeds in
        # the test environment.
        self._db_disabled = (db is None) and _test_mode_no_db
        # Track which run_ids were stop-flipped locally so the polling
        # task doesn't re-flip and so we can stop polling them.
        self._stop_flipped: set = set()

    # --- DB binding helpers -------------------------------------

    def _get_db(self):
        """Return the DatabaseService, lazily initializing on first use."""
        if self._db_disabled:
            return None
        if self._db is not None:
            return self._db
        try:
            from config import settings
            from services.database_service import get_database_service
            self._db = get_database_service(settings)
            _ensure_indexes(self._db)
        except Exception:
            # If DB isn't reachable at startup we degrade to
            # in-memory-only behavior. Tests use this path; prod
            # callers will hit a different error before this point.
            self._db = None
        return self._db

    def _persist(self, record: RunRecord, include_events: bool = False) -> None:
        """Write the record to CouchDB. Best-effort -- logs and continues
        on failure rather than breaking the in-memory flow that handles
        the actual run.

        CouchDB requires _rev for updates. The save() in this codebase
        does NOT auto-resolve revs (per the comment in CouchDBService
        .save: "Caller is responsible for providing _rev when updating
        an existing document"), so we do a get() first to pick up the
        current _rev. New docs (first persist for a fresh run_id)
        skip the _rev step -- the get returns None and we save
        without _rev, which CouchDB accepts for inserts. Each update
        therefore costs one extra HTTP round-trip; acceptable since
        run records aren't written hot (create, complete, and the
        occasional stop_requested flip)."""
        db = self._get_db()
        if db is None:
            return
        try:
            doc = record.to_couch_doc(include_events=include_events)
            try:
                existing = db.get(RUN_REGISTRY_DB, record.run_id)
                if existing and existing.get("_rev"):
                    doc["_rev"] = existing["_rev"]
            except Exception:
                # Doc doesn't exist (or get failed transiently);
                # proceed without _rev. CouchDB treats a save with
                # no _rev as an insert; if the doc actually exists
                # we'll get a 409 below and log it.
                pass
            db.save(RUN_REGISTRY_DB, record.run_id, doc)
        except Exception as e:
            # Defensive: persistence failure mustn't break run-time
            # behavior. The in-memory record stays consistent; the
            # registry will retry on the next state transition.
            print(f"[run_registry] persist failed for {record.run_id}: {e}",
                  flush=True)

    # --- Public API ---------------------------------------------

    def new_record(
        self,
        *,
        user_id: str,
        agent_name: str,
        agent_id: Optional[str] = None,
        input_dict: Optional[Dict[str, Any]] = None,
    ) -> RunRecord:
        """Create a record with a fresh run_id, cache locally, and
        persist a stub to CouchDB so other workers can see it."""
        run_id = str(uuid.uuid4())
        record = RunRecord(
            run_id=run_id,
            user_id=user_id,
            agent_name=agent_name,
            agent_id=agent_id,
            input_dict=input_dict,
        )
        # worker_id is set by the dataclass default to WORKER_ID, so
        # this record is implicitly owned by this worker.
        self._records[run_id] = record
        self._persist(record, include_events=False)
        return record

    def bind_task(self, record: RunRecord, task: asyncio.Task) -> None:
        record.task = task

    def get(self, run_id: str) -> Optional[RunRecord]:
        """Return the record by run_id. Local cache first, CouchDB
        fallback. Returns None if not found in either."""
        self._evict_expired_local()
        rec = self._records.get(run_id)
        if rec is not None:
            return rec
        # Fall back to CouchDB. This handles cross-worker read
        # (UI loads on worker B for a run owned by worker A) and
        # post-eviction lookup (record completed and was evicted
        # from local cache but is still within the 7-day retention).
        db = self._get_db()
        if db is None:
            return None
        try:
            doc = db.get(RUN_REGISTRY_DB, run_id)
        except Exception:
            return None
        if not doc:
            return None
        rec = RunRecord.from_couch_doc(doc)
        # Cache briefly so the UI's poll-while-running loop doesn't
        # re-fetch this same doc every interval.
        rec._completed_at_monotonic = time.monotonic() if rec.completed_at else None
        self._records[run_id] = rec
        return rec

    def list_for_user(
        self,
        user_id: str,
        limit: int = 100,
        agent_id: Optional[str] = None,
    ) -> List[RunRecord]:
        """List records for a user, optionally filtered by agent_id.

        Queries CouchDB (the source of truth) rather than scanning
        the local cache, so this returns runs owned by any worker.
        Records are reconstructed from CouchDB docs; they are
        view-only (no live trace).
        """
        db = self._get_db()
        if db is None:
            # In-memory fallback for tests and dev without CouchDB.
            self._evict_expired_local()
            out = [r for r in self._records.values() if r.user_id == user_id]
            if agent_id is not None:
                out = [r for r in out if r.agent_id == agent_id]
            out.sort(key=lambda r: r.started_at, reverse=True)
            return out[:limit]

        selector = {"user_id": user_id, "type": "run"}
        if agent_id is not None:
            selector["agent_id"] = agent_id
        try:
            # CouchDBService.find doesn't expose Mango sort; fetch
            # what matches the selector (cap-bounded by limit) and
            # sort in Python. started_at is an ISO-8601 string so
            # reverse lex sort gives newest-first. For limit=100
            # the cost is negligible.
            docs = db.find(
                RUN_REGISTRY_DB,
                selector=selector,
                limit=limit,
            )
        except Exception as e:
            print(f"[run_registry] list_for_user query failed: {e}", flush=True)
            return []
        docs.sort(key=lambda d: d.get("started_at", ""), reverse=True)
        return [RunRecord.from_couch_doc(d) for d in docs]

    def mark_complete(
        self,
        record: RunRecord,
        *,
        status: Literal["success", "error", "stopped"],
        result: Any = None,
        error: Optional[str] = None,
        schema_warnings: Optional[List[str]] = None,
        ops_log: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        if record._persisted_complete and record.status == status:
            # Defensive: mark_complete can be called twice in the
            # cancel-handling paths (once from the AgentStopped catch,
            # once from the CancelledError catch).
            # Idempotent on identical second call.
            return
        record.status = status
        record.result = result
        record.error = error
        record.schema_warnings = schema_warnings
        record.ops_log = ops_log
        record.completed_at = naive_utc_now()
        record._completed_at_monotonic = time.monotonic()

        # Signal end-of-stream to all current subscribers.
        for q in list(record.trace._subscribers):
            try:
                q.put_nowait(DONE_SENTINEL)
            except Exception:
                pass

        # Persist final state including events. This is the big write;
        # subsequent reads from other workers see the full record.
        self._persist(record, include_events=True)
        record._persisted_complete = True

    def request_stop(self, run_id: str, user_id: str) -> str:
        """Flag the run as stop-requested.

        Returns one of:
            'flipped_local'     - we own the cancel token and flipped it
            'persisted_remote'  - wrote stop_requested to CouchDB for the
                                  owning worker to pick up via polling
            'not_found'         - no record in CouchDB or local cache
            'forbidden'         - record exists but is for another user

        The endpoint should treat anything other than 'not_found' /
        'forbidden' as success (HTTP 202).
        """
        # Try local cache first (fast path).
        local = self._records.get(run_id)
        if local is not None and local.user_id != user_id:
            return "forbidden"

        db = self._get_db()
        doc = None
        if db is not None:
            try:
                doc = db.get(RUN_REGISTRY_DB, run_id)
            except Exception:
                doc = None
        if doc is None and local is None:
            return "not_found"
        if doc is not None and doc.get("user_id") != user_id:
            return "forbidden"

        # Update CouchDB unconditionally so the polling task on the
        # owning worker sees the flag. Skip if we have no DB (tests).
        if db is not None and doc is not None:
            doc["stop_requested"] = True
            try:
                db.save(RUN_REGISTRY_DB, run_id, doc)
            except Exception as e:
                print(f"[run_registry] request_stop persist failed: {e}",
                      flush=True)

        # Local fast-path: if this worker owns the live cancel token,
        # flip it immediately so stop latency on the owning-worker
        # case is effectively zero.
        from services.run_cancel_registry import get as get_token
        token = get_token(run_id)
        if token is not None:
            token.request_stop()
            if local is not None:
                local.stop_requested = True
            self._stop_flipped.add(run_id)
            return "flipped_local"
        return "persisted_remote"

    def poll_owned_stops(self) -> int:
        """Scan CouchDB for in-flight runs this worker owns that have
        been flagged for stop. Flip local cancel tokens for any new
        ones. Returns the count of newly-flipped tokens.

        Called every few seconds by the background poller. The query
        uses the by_worker_status index so it stays fast even with
        thousands of historical records.
        """
        db = self._get_db()
        if db is None:
            return 0
        try:
            docs = db.find(
                RUN_REGISTRY_DB,
                selector={
                    "worker_id": WORKER_ID,
                    "status": "running",
                    "stop_requested": True,
                },
                limit=200,
            )
        except Exception as e:
            print(f"[run_registry] poll query failed: {e}", flush=True)
            return 0
        from services.run_cancel_registry import get as get_token
        flipped = 0
        for d in docs:
            run_id = d.get("run_id")
            if not run_id or run_id in self._stop_flipped:
                continue
            token = get_token(run_id)
            if token is None:
                # Token already cleaned up but doc still says
                # running -- the run is probably completing right
                # now. Skip; the upcoming mark_complete will write
                # the final state.
                continue
            token.request_stop()
            self._stop_flipped.add(run_id)
            local = self._records.get(run_id)
            if local is not None:
                local.stop_requested = True
            flipped += 1
        return flipped

    def evict_old_completed(self) -> int:
        """Delete CouchDB records for runs completed more than
        COUCH_RETENTION_SECONDS ago. Returns count deleted."""
        db = self._get_db()
        if db is None:
            return 0
        from datetime import timedelta
        cutoff = (naive_utc_now() - timedelta(seconds=COUCH_RETENTION_SECONDS)).isoformat()
        try:
            docs = db.find(
                RUN_REGISTRY_DB,
                selector={
                    "type": "run",
                    "status": {"$ne": "running"},
                    "completed_at": {"$lt": cutoff},
                },
                limit=500,
            )
        except Exception as e:
            print(f"[run_registry] evict query failed: {e}", flush=True)
            return 0
        deleted = 0
        for d in docs:
            run_id = d.get("run_id")
            if not run_id:
                continue
            try:
                db.delete(RUN_REGISTRY_DB, run_id)
                deleted += 1
            except Exception:
                pass
        return deleted

    def _evict_expired_local(self) -> None:
        """Drop the local in-memory cache for completed records past
        the short local TTL. CouchDB still holds them; subsequent
        reads fall through to from_couch_doc."""
        now = time.monotonic()
        expired = [
            run_id
            for run_id, r in self._records.items()
            if r._completed_at_monotonic is not None
            and (now - r._completed_at_monotonic) > LOCAL_CACHE_TTL_SECONDS
        ]
        for run_id in expired:
            self._records.pop(run_id, None)
            self._stop_flipped.discard(run_id)


_registry: Optional[RunRegistry] = None


def get_run_registry() -> RunRegistry:
    """Process-singleton accessor."""
    global _registry
    if _registry is None:
        _registry = RunRegistry()
    return _registry


def reset_run_registry_for_tests() -> None:
    """Tests-only — discard the singleton AND opt this process out of
    CouchDB persistence for the remainder of its lifetime.

    The opt-out is sticky: once any test in the process calls this,
    no subsequent RunRegistry() instance will try to talk to CouchDB.
    Lets unit tests run without standing up a real DB and prevents
    test runs from polluting a shared CouchDB instance."""
    global _registry, _test_mode_no_db
    _registry = None
    _test_mode_no_db = True
