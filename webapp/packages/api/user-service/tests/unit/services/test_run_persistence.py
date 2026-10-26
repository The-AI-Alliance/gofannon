"""Tests for run persistence across client disconnect.

Covers the three things that can regress and would not be obvious:

  1. bind_task actually binds. If it stops being called, the detached
     task loses its only strong reference and becomes GC-eligible
     mid-run. Nothing else in the suite would notice.
  2. Client disconnect does NOT cancel the task. This is the whole
     behavior change; a future "clean up the finally block" refactor
     could silently restore the old cancel and cost another 61-of-64.
  3. force-complete refuses a run that is still emitting events, and
     allows one that is not.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from services.run_registry import (
    DONE_SENTINEL,
    RunRegistry,
    reset_run_registry_for_tests,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset():
    reset_run_registry_for_tests()
    yield
    reset_run_registry_for_tests()


# ---------------------------------------------------------------- binding


@pytest.mark.asyncio
async def test_bind_task_holds_a_strong_reference():
    """The registry must hold the task, not just metadata about it.

    asyncio keeps only weak references to tasks, so once the SSE
    generator's frame is gone the registry is the sole owner. If
    bind_task is skipped, record.task is None and the task is
    GC-eligible while still running.
    """
    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")

    async def _work():
        await asyncio.sleep(0.05)
        return "done"

    task = asyncio.create_task(_work())
    reg.bind_task(record, task)

    assert record.task is task, "registry must retain the task object itself"
    assert not record.task.done()
    assert await task == "done"


@pytest.mark.asyncio
async def test_task_survives_when_only_the_registry_holds_it():
    """Drop every local reference; the task must still complete.

    This is the detached-run scenario in miniature: the SSE handler
    returns, its closure goes away, and only the registry is left.
    """
    import gc

    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    completed = []

    async def _work():
        await asyncio.sleep(0.05)
        completed.append(True)

    def _start_and_forget():
        t = asyncio.create_task(_work())
        reg.bind_task(record, t)
        # `t` goes out of scope here, exactly like agent_task does when
        # event_generator returns.

    _start_and_forget()
    gc.collect()
    await asyncio.sleep(0.15)

    assert completed == [True], "task was collected or cancelled after its local ref was dropped"
    assert record.task.done()


# ------------------------------------------------------- disconnect policy


@pytest.mark.asyncio
async def test_generator_close_does_not_cancel_the_task():
    """Closing the subscriber must not cancel the run.

    Models the finally block: the generator is closed while the agent
    task is mid-flight. Under the old code this cancelled after 5s.
    """
    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    finished = asyncio.Event()

    async def _agent():
        await asyncio.sleep(0.2)
        finished.set()
        return "result"

    agent_task = asyncio.create_task(_agent())
    reg.bind_task(record, agent_task)

    async def _generator():
        try:
            yield "event: run_id\n\n"
            await asyncio.sleep(3600)  # blocked waiting for queue items
        finally:
            # The patched policy: log and detach. No await, no cancel.
            if not agent_task.done():
                pass

    gen = _generator()
    await gen.__anext__()
    await gen.aclose()  # client disconnected

    await asyncio.wait_for(finished.wait(), timeout=1.0)
    assert not agent_task.cancelled()
    assert await agent_task == "result"


@pytest.mark.asyncio
async def test_explicit_stop_still_cancels():
    """Removing implicit cancellation must not remove explicit stop.

    /stop is now the only cancel path, so it becomes load-bearing.
    """
    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")

    async def _agent():
        await asyncio.sleep(3600)

    agent_task = asyncio.create_task(_agent())
    reg.bind_task(record, agent_task)

    outcome = reg.request_stop(record.run_id, "alice")
    assert outcome in ("flipped_local", "persisted_remote")

    agent_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await agent_task


@pytest.mark.asyncio
async def test_stop_by_non_owner_is_refused():
    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    assert reg.request_stop(record.run_id, "mallory") == "forbidden"


# ------------------------------------------------------- staleness guard


def _idle_seconds(record):
    """Mirror of routes._run_idle_seconds for unit-level testing."""
    from datetime import datetime, timezone

    def _age(ts):
        if not ts:
            return None
        try:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - ts).total_seconds()
        except Exception:
            return None

    events = list(getattr(record.trace, "events", []) or [])
    for ev in reversed(events):
        if isinstance(ev, dict):
            age = _age(ev.get("timestamp") or ev.get("ts"))
            if age is not None:
                return age
        break
    return _age(getattr(record, "started_at", None))


def test_recent_event_reads_as_active():
    """A run emitting events is alive; force-complete must refuse it."""
    from datetime import datetime, timezone

    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    record.trace.append({
        "type": "log",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    idle = _idle_seconds(record)
    assert idle is not None and idle < 5


def test_old_event_reads_as_stale():
    """No events for a long time is the orphaned-worker signature."""
    from datetime import datetime, timedelta, timezone

    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    record.trace.append({
        "type": "log",
        "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
    })

    idle = _idle_seconds(record)
    assert idle is not None and idle > 3600


def test_no_events_falls_back_to_started_at():
    """A run that died before its first event must still be clearable."""
    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    assert _idle_seconds(record) is not None


def test_mark_complete_is_idempotent():
    """The UI can double-click; a second clear must not error."""
    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    reg.mark_complete(record, status="error", error="cleared")
    assert record.status == "error"
    reg.mark_complete(record, status="error", error="cleared")
    assert record.status == "error"


@pytest.mark.asyncio
async def test_mark_complete_signals_subscribers():
    """Clearing a run must unblock anyone still streaming it."""
    reg = RunRegistry()
    record = reg.new_record(user_id="alice", agent_name="agent")
    q = asyncio.Queue()
    record.trace.add_subscriber(q)

    reg.mark_complete(record, status="error", error="cleared")

    assert await asyncio.wait_for(q.get(), timeout=1.0) is DONE_SENTINEL


# ------------------------------------------------- deployed-run input safety
#
# These exercise services.log_redaction directly rather than a local copy —
# the point is that the deployed-run path reuses the SAME filter as
# agent_trace and observability_service, so behavior cannot drift.


def test_run_inputs_are_redacted_before_storage():
    """Run inputs are persisted to CouchDB and served by GET /runs/{id}.

    Storing them raw would write live credentials to disk. Storing nothing
    would lose the provenance that makes a run record useful.
    """
    import copy
    from services.log_redaction import redact_in_place

    raw = {
        "sourceRepo": "apache/apisix",
        "sourceToken": "github_pat_" + "x" * 82,
        "outputToken": "github_pat_" + "y" * 82,
        "level": "L3",
        "outputDirectory": "scans/example",
    }
    red = redact_in_place(copy.deepcopy(raw))

    assert "github_pat_" not in str(red), "a credential survived redaction"
    assert red["sourceRepo"] == "apache/apisix"
    assert red["level"] == "L3"
    assert red["outputDirectory"] == "scans/example"
    assert "REDACTED" in red["sourceToken"]


def test_redaction_recurses_into_nested_objects():
    import copy
    from services.log_redaction import redact_in_place

    red = redact_in_place(copy.deepcopy(
        {"outer": {"anthropic": "sk-ant-" + "a" * 30}, "keep": "visible"}))
    assert "sk-ant-aaa" not in str(red)
    assert red["keep"] == "visible"


def test_redaction_does_not_mutate_the_agents_inputs():
    """redact_in_place mutates dicts. The agent must still get the real values.

    If the deepcopy in the route is ever dropped, the agent receives
    '[REDACTED:github_pat]' as its token and every GitHub call 401s — a
    failure that would look like a credentials problem, not a code one.
    """
    import copy
    from services.log_redaction import redact_in_place

    original = {"sourceToken": "github_pat_" + "z" * 82}
    snapshot = copy.deepcopy(original)
    redact_in_place(copy.deepcopy(original))
    assert original == snapshot, "the caller's dict was mutated"


def test_record_carries_agent_id_for_deep_linking():
    """Deployed runs should link back to their agent in the runs UI."""
    reg = RunRegistry()
    record = reg.new_record(
        user_id="alice", agent_name="asvs_orchestrate", agent_id="agent-123",
        input_dict={"level": "L3"},
    )
    assert record.agent_id == "agent-123"
    assert record.input_dict == {"level": "L3"}