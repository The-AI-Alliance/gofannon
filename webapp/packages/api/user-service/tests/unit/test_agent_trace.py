"""Unit tests for the agent runtime trace module.

Covers Trace event collection, the depth/agent stack handling, the
truncation cap, GOFANNON_DISABLE_USER_TRACE, the contextvar binding,
the line-buffering stdout wrapper, the logging handler, and the
capture_user_io context manager. Pure-Python tests; no FastAPI.
"""
from __future__ import annotations

import asyncio
import logging
import sys

import pytest

from services.agent_trace import (
    MAX_EVENT_MESSAGE_BYTES,
    MAX_EVENTS_PER_TRACE,
    Trace,
    bind_trace,
    capture_user_io,
    get_current_trace,
    new_run_id,
)


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------
# Trace: structural events
# ---------------------------------------------------------------------


def test_trace_starts_empty():
    t = Trace()
    assert t.events == []


def test_agent_start_pushes_event_and_returns_start_ms():
    t = Trace()
    start = t.agent_start(agent_name="alpha")

    assert isinstance(start, float)
    assert len(t.events) == 1
    ev = t.events[0]
    assert ev["type"] == "agent_start"
    assert ev["agent_name"] == "alpha"
    assert ev["depth"] == 0  # first agent is at top level
    assert ev["source"] == "system"


def test_agent_end_emits_duration_and_outcome():
    t = Trace()
    start = t.agent_start(agent_name="alpha")
    t.agent_end(agent_name="alpha", start_ms=start, outcome="success")

    end = t.events[-1]
    assert end["type"] == "agent_end"
    assert end["agent_name"] == "alpha"
    assert end["outcome"] == "success"
    assert end["duration_ms"] is not None
    assert end["duration_ms"] >= 0


def test_nested_agents_track_depth():
    """Calling agent_start twice without an intervening end nests."""
    t = Trace()
    s1 = t.agent_start(agent_name="alpha")
    # While alpha is running, alpha calls beta — depth should go 1.
    s2 = t.agent_start(agent_name="beta")
    t.agent_end(agent_name="beta", start_ms=s2, outcome="success")
    t.agent_end(agent_name="alpha", start_ms=s1, outcome="success")

    types_and_depths = [(e["type"], e["depth"], e.get("agent_name")) for e in t.events]
    assert types_and_depths == [
        ("agent_start", 0, "alpha"),
        ("agent_start", 1, "beta"),
        ("agent_end", 1, "beta"),
        ("agent_end", 0, "alpha"),
    ]


def test_llm_call_event_carries_metadata():
    t = Trace()
    t.agent_start(agent_name="alpha")
    t.llm_call(provider="anthropic", model="claude-haiku-4-5",
               duration_ms=234.5, input_tokens=100, output_tokens=50)

    ev = t.events[-1]
    assert ev["type"] == "llm_call"
    assert ev["provider"] == "anthropic"
    assert ev["model"] == "claude-haiku-4-5"
    assert ev["duration_ms"] == 234.5  # rounded to 1 decimal
    assert ev["input_tokens"] == 100
    assert ev["output_tokens"] == 50
    assert ev["agent_name"] == "alpha"  # picks up from stack


def test_llm_call_with_error_field():
    t = Trace()
    t.agent_start(agent_name="alpha")
    t.llm_call(provider="openai", model="gpt-4", error="RateLimitError: too fast")
    ev = t.events[-1]
    assert ev["error"] == "RateLimitError: too fast"


def test_data_store_event():
    t = Trace()
    t.agent_start(agent_name="alpha")
    t.data_store(op="read", namespace="docs", key="readme.md", found=True)

    ev = t.events[-1]
    assert ev["type"] == "data_store"
    assert ev["operation"] == "read"
    assert ev["namespace"] == "docs"
    assert ev["key"] == "readme.md"
    assert ev["found"] is True


def test_error_captures_traceback():
    t = Trace()
    t.agent_start(agent_name="alpha")
    try:
        raise ValueError("boom")
    except ValueError as exc:
        t.error(exc)

    ev = t.events[-1]
    assert ev["type"] == "error"
    assert ev["exception_type"] == "ValueError"
    assert ev["message"] == "boom"
    # Traceback is captured by traceback.format_exc, which only works
    # while we're inside the except clause — Trace.error must be called
    # there for traceback to be populated. We confirmed it's there.
    assert "ValueError" in ev["traceback"]
    assert "boom" in ev["traceback"]


# ---------------------------------------------------------------------
# Caps and truncation
# ---------------------------------------------------------------------


def test_per_event_message_truncated_when_too_large():
    t = Trace()
    t.agent_start(agent_name="alpha")
    huge = "x" * (MAX_EVENT_MESSAGE_BYTES + 100)
    t.stdout(huge)

    ev = t.events[-1]
    # Truncated message includes a marker; total length is the cap plus
    # the marker text (which is small relative to the cap).
    assert ev["message"].startswith("x" * 100)  # leading bytes preserved
    assert "[truncated" in ev["message"]
    assert len(ev["message"]) < len(huge)  # actually shrank


def test_truncation_cap_appends_synthetic_event_and_drops_rest(monkeypatch):
    # Lower the cap so we don't have to emit thousands of events.
    monkeypatch.setattr("services.agent_trace.MAX_EVENTS_PER_TRACE", 5)
    t = Trace()
    t.agent_start(agent_name="alpha")
    # Emit until past the cap.
    for i in range(20):
        t.stdout(f"line {i}")

    # First few got in; then a trace_truncated marker; nothing after.
    types = [e["type"] for e in t.events]
    assert "trace_truncated" in types
    # No more than one trace_truncated.
    assert types.count("trace_truncated") == 1
    # Once truncated, no further events land.
    truncated_idx = types.index("trace_truncated")
    assert all(t == "trace_truncated" or t != "stdout" for t in types[truncated_idx + 1:])


# ---------------------------------------------------------------------
# GOFANNON_DISABLE_USER_TRACE — user-origin events suppressed
# ---------------------------------------------------------------------


def test_user_origin_events_suppressed_when_env_var_set(monkeypatch):
    monkeypatch.setenv("GOFANNON_DISABLE_USER_TRACE", "1")
    t = Trace()
    t.agent_start(agent_name="alpha")
    t.stdout("should not appear")
    t.log("INFO", "should not appear either")

    types = [e["type"] for e in t.events]
    assert "stdout" not in types
    assert "log" not in types
    # But structural events still emit:
    assert "agent_start" in types


def test_structural_events_still_emit_when_user_trace_disabled(monkeypatch):
    """Errors are not user-origin; they should always show up."""
    monkeypatch.setenv("GOFANNON_DISABLE_USER_TRACE", "1")
    t = Trace()
    t.agent_start(agent_name="alpha")
    try:
        raise RuntimeError("crash")
    except RuntimeError as exc:
        t.error(exc)
    t.llm_call(provider="anthropic", model="claude-haiku-4-5")

    types = [e["type"] for e in t.events]
    assert "error" in types
    assert "llm_call" in types


@pytest.mark.parametrize("val", ["0", "false", "FALSE", "no", ""])
def test_user_trace_remains_enabled_for_falsy_env_values(monkeypatch, val):
    """Only "1"/"true"/"yes" (case-insensitive) suppresses; anything else doesn't."""
    monkeypatch.setenv("GOFANNON_DISABLE_USER_TRACE", val)
    t = Trace()
    t.agent_start(agent_name="alpha")
    t.stdout("should appear")
    types = [e["type"] for e in t.events]
    assert "stdout" in types


# ---------------------------------------------------------------------
# Contextvar binding
# ---------------------------------------------------------------------


def test_get_current_trace_returns_none_outside_bind():
    assert get_current_trace() is None


def test_bind_trace_makes_trace_visible_inside_block():
    t = Trace()
    assert get_current_trace() is None
    with bind_trace(t):
        assert get_current_trace() is t
    # Reset on exit.
    assert get_current_trace() is None


def test_bind_trace_restores_previous_value_on_nested_use():
    t1 = Trace()
    t2 = Trace()
    with bind_trace(t1):
        assert get_current_trace() is t1
        with bind_trace(t2):
            assert get_current_trace() is t2
        # Inner bind should not have leaked.
        assert get_current_trace() is t1
    assert get_current_trace() is None


def test_bind_trace_resets_even_on_exception():
    t = Trace()
    with pytest.raises(RuntimeError):
        with bind_trace(t):
            assert get_current_trace() is t
            raise RuntimeError("boom")
    assert get_current_trace() is None


# ---------------------------------------------------------------------
# Queue publishing (the streaming hook)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attach_queue_makes_appended_events_publish():
    t = Trace()
    queue: asyncio.Queue = asyncio.Queue()
    t.attach_queue(queue)

    t.agent_start(agent_name="alpha")
    t.stdout("hello")
    t.agent_end(agent_name="alpha", start_ms=0.0, outcome="success")

    # Queue should now hold three items, in order.
    items = []
    while not queue.empty():
        items.append(queue.get_nowait())
    types = [i["type"] for i in items]
    assert types == ["agent_start", "stdout", "agent_end"]


@pytest.mark.asyncio
async def test_queue_publishing_does_not_block_when_full():
    """A bounded queue that fills up should not block emitters."""
    t = Trace()
    queue: asyncio.Queue = asyncio.Queue(maxsize=2)
    t.attach_queue(queue)

    # Three events, queue capacity of 2. The third should be silently
    # dropped from the stream (but still in t.events).
    t.agent_start(agent_name="alpha")
    t.stdout("one")
    t.stdout("two")  # this one fills the queue
    t.stdout("three")  # would block — instead, dropped from queue

    assert len(t.events) == 4  # all four made it to the bulk list
    assert queue.qsize() == 2  # queue capped


def test_no_queue_attached_means_no_publishing():
    """Without attach_queue, append doesn't try to publish to anything."""
    t = Trace()
    # Should not raise, should just append to events.
    t.agent_start(agent_name="alpha")
    t.stdout("hello")
    assert len(t.events) == 2


# ---------------------------------------------------------------------
# capture_user_io: stdout / stderr / logging redirection
# ---------------------------------------------------------------------


def test_capture_user_io_routes_print_to_stdout_event():
    """In production, capture_user_io is used together with bind_trace
    (see _execute_agent_code's `with bind_trace(trace), capture_user_io(trace):`).
    The logging handler routes through get_current_trace, so the bind
    is what makes the connection."""
    t = Trace()
    t.agent_start(agent_name="alpha")
    with bind_trace(t), capture_user_io(t):
        print("hello world")

    stdouts = [e for e in t.events if e["type"] == "stdout"]
    assert len(stdouts) == 1
    assert stdouts[0]["message"] == "hello world"


def test_capture_user_io_buffers_partial_writes_until_newline():
    """print() does multiple writes per logical line; we should emit one event per line."""
    t = Trace()
    t.agent_start(agent_name="alpha")
    with bind_trace(t), capture_user_io(t):
        sys.stdout.write("hello ")
        sys.stdout.write("world")
        sys.stdout.write("\n")
        sys.stdout.write("second line\n")

    stdouts = [e for e in t.events if e["type"] == "stdout"]
    assert [s["message"] for s in stdouts] == ["hello world", "second line"]


def test_capture_user_io_routes_logging_to_log_event():
    """Use a dedicated logger to avoid interference from pytest's
    caplog plugin which also hooks into the root logger."""
    t = Trace()
    t.agent_start(agent_name="alpha")
    test_logger = logging.getLogger("test_agent_trace_capture")
    test_logger.setLevel(logging.DEBUG)
    with bind_trace(t), capture_user_io(t):
        test_logger.warning("dangerous")

    logs = [e for e in t.events if e["type"] == "log"]
    assert len(logs) >= 1
    matching = [l for l in logs if "dangerous" in l["message"]]
    assert len(matching) == 1
    assert matching[0]["level"] == "WARNING"


def test_capture_user_io_restores_streams_on_exit():
    t = Trace()
    original_stdout = sys.stdout
    with capture_user_io(t):
        assert sys.stdout is not original_stdout
    assert sys.stdout is original_stdout


def test_capture_user_io_restores_streams_on_exception():
    t = Trace()
    original_stdout = sys.stdout
    with pytest.raises(RuntimeError):
        with capture_user_io(t):
            assert sys.stdout is not original_stdout
            raise RuntimeError("boom")
    assert sys.stdout is original_stdout


def test_capture_user_io_does_nothing_when_disabled(monkeypatch):
    """When GOFANNON_DISABLE_USER_TRACE=1, the context is a no-op."""
    monkeypatch.setenv("GOFANNON_DISABLE_USER_TRACE", "1")
    t = Trace()
    original_stdout = sys.stdout
    with bind_trace(t), capture_user_io(t):
        # stdout shouldn't be swapped at all.
        assert sys.stdout is original_stdout
        print("nothing should be captured")
    types = [e["type"] for e in t.events]
    assert "stdout" not in types


def test_capture_user_io_log_handler_removed_on_exit():
    """Adding our handler then removing it shouldn't leak handlers across runs."""
    t = Trace()
    initial_count = len(logging.getLogger().handlers)
    with capture_user_io(t):
        added = len(logging.getLogger().handlers) - initial_count
        assert added == 1
    assert len(logging.getLogger().handlers) == initial_count


# ---------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------


def test_new_run_id_returns_unique_short_string():
    a = new_run_id()
    b = new_run_id()
    assert a != b
    assert len(a) == 12
    assert all(c in "0123456789abcdef" for c in a)


def test_unbound_event_uses_unknown_agent():
    """An event emitted before any agent_start gets the placeholder name."""
    t = Trace()
    # No agent_start; just emit a stdout directly.
    t.stdout("orphan")
    ev = t.events[-1]
    assert ev["agent_name"] == "unknown"
