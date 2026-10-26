"""Unit tests for the in-process run registry."""
from __future__ import annotations

import asyncio
import time

import pytest

from services.run_registry import (
    EVICTION_TTL_SECONDS,
    DONE_SENTINEL,
    RunRegistry,
    _FanoutTrace,
    reset_run_registry_for_tests,
)


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset():
    reset_run_registry_for_tests()
    yield
    reset_run_registry_for_tests()


def test_new_record_assigns_unique_run_id():
    reg = RunRegistry()
    r1 = reg.new_record(user_id="alice", agent_name="x")
    r2 = reg.new_record(user_id="alice", agent_name="x")
    assert r1.run_id != r2.run_id
    assert r1.status == "running"
    assert r2.status == "running"


def test_get_returns_record_by_id():
    reg = RunRegistry()
    rec = reg.new_record(user_id="alice", agent_name="x")
    assert reg.get(rec.run_id) is rec


def test_get_returns_none_for_unknown_id():
    reg = RunRegistry()
    assert reg.get("not-a-real-id") is None


def test_list_for_user_filters_by_user_id():
    reg = RunRegistry()
    a = reg.new_record(user_id="alice", agent_name="x")
    b = reg.new_record(user_id="bob", agent_name="y")
    assert reg.list_for_user("alice") == [a]
    assert reg.list_for_user("bob") == [b]


def test_list_for_user_sorted_newest_first():
    import time as _t
    reg = RunRegistry()
    a = reg.new_record(user_id="alice", agent_name="x")
    _t.sleep(0.001)
    b = reg.new_record(user_id="alice", agent_name="y")
    out = reg.list_for_user("alice")
    assert out[0] is b
    assert out[1] is a


def test_mark_complete_sets_terminal_state():
    reg = RunRegistry()
    rec = reg.new_record(user_id="alice", agent_name="x")
    reg.mark_complete(rec, status="success", result={"k": "v"})
    assert rec.status == "success"
    assert rec.result == {"k": "v"}
    assert rec.completed_at is not None


def test_eviction_after_ttl_removes_completed_record():
    reg = RunRegistry()
    rec = reg.new_record(user_id="alice", agent_name="x")
    reg.mark_complete(rec, status="success")
    # Backdate the eviction clock past TTL.
    rec._completed_at_monotonic = time.monotonic() - (EVICTION_TTL_SECONDS + 10)
    # get() triggers eviction.
    assert reg.get(rec.run_id) is None


def test_running_record_is_not_evicted():
    reg = RunRegistry()
    rec = reg.new_record(user_id="alice", agent_name="x")
    # No completion → no eviction even if we tried.
    assert reg.get(rec.run_id) is rec


def test_fanout_trace_delivers_to_multiple_subscribers():
    trace = _FanoutTrace()
    q1: asyncio.Queue = asyncio.Queue()
    q2: asyncio.Queue = asyncio.Queue()
    trace.add_subscriber(q1)
    trace.add_subscriber(q2)
    trace.append({"type": "tick", "i": 1})
    trace.append({"type": "tick", "i": 2})

    assert q1.qsize() == 2
    assert q2.qsize() == 2
    assert q1.get_nowait()["i"] == 1
    assert q2.get_nowait()["i"] == 1


def test_fanout_trace_remove_subscriber_stops_delivery():
    trace = _FanoutTrace()
    q: asyncio.Queue = asyncio.Queue()
    trace.add_subscriber(q)
    trace.append({"i": 1})
    trace.remove_subscriber(q)
    trace.append({"i": 2})

    assert q.qsize() == 1


def test_mark_complete_signals_done_to_subscribers():
    reg = RunRegistry()
    rec = reg.new_record(user_id="alice", agent_name="x")
    q: asyncio.Queue = asyncio.Queue()
    rec.trace.add_subscriber(q)
    reg.mark_complete(rec, status="success")
    item = q.get_nowait()
    assert item is DONE_SENTINEL


def test_to_summary_omits_event_body():
    reg = RunRegistry()
    rec = reg.new_record(user_id="alice", agent_name="x")
    rec.trace.append({"type": "agent_start", "ts": 1})
    summary = rec.to_summary()
    assert "events" not in summary
    assert "result" not in summary
    assert summary["runId"] == rec.run_id
    assert summary["status"] == "running"
