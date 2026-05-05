"""Integration tests for the SSE streaming sandbox endpoint.

Covers:
  - Successful run: 'trace' frames are streamed for each Trace event,
    final 'done' frame carries the result.
  - Failure path: 'done' frame's outcome is 'error' and the trace
    contains the error event with the exception's type and message.
  - Frame format: each frame is event:NAME\\ndata:JSON\\n\\n; the
    parser tolerates split chunks (we feed it the full body so we don't
    test partial chunking, but we do verify the boundary parser works).
  - Heartbeat comments (starting with `: `) appear when the run is slow
    enough; we don't force this in the test (would require a 30s+ run)
    but we verify the parser ignores them.

We mock out _execute_agent_code so the test doesn't need a real agent
runtime — we just need the streaming endpoint to talk to a Trace and
yield frames.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app_factory import create_app
from dependencies import get_db, get_user_service_dep
from routes import get_current_user


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------
# SSE frame parsing helper
# ---------------------------------------------------------------------


def parse_sse_frames(body: str):
    """Parse an SSE response body into a list of (event, data) tuples.

    Mirrors what the frontend's runCodeInSandboxStreaming does: split
    on blank-line boundaries, then for each frame extract `event:` and
    `data:` lines. Comment lines (`: ...`) are ignored.
    """
    frames = []
    for raw in body.split("\n\n"):
        if not raw.strip():
            continue
        event = "message"
        data_lines = []
        for line in raw.split("\n"):
            if line.startswith(":"):
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        try:
            data = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            continue
        frames.append((event, data))
    return frames


# ---------------------------------------------------------------------
# App + auth scaffolding shared by all tests
# ---------------------------------------------------------------------


def _make_app(mock_execute):
    """Build a FastAPI app with the streaming endpoint wired to a mocked
    _execute_agent_code. Authentication is short-circuited to a fixed
    test user.
    """
    app = create_app()

    def override_current_user(request: Request):
        user = {"uid": "test-user", "email": "test@example.com"}
        request.state.user = user
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    # The streaming endpoint calls db and user_service via DI; minimal
    # stubs are enough since our mocked _execute_agent_code doesn't
    # actually use them.
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_user_service_dep] = lambda: object()

    # Patch _execute_agent_code at the module where it's looked up by
    # the route. The endpoint imports it from the dependencies module
    # but the route handler reads it as a module-global, so we patch
    # the attribute on `routes`.
    import routes
    original = routes._execute_agent_code
    routes._execute_agent_code = mock_execute
    return app, original, routes


def _request_payload(**overrides):
    """Minimal valid request body for /agents/run-code/stream."""
    body = {
        "code": "async def run(input_dict, tools): return {}",
        "inputDict": {},
        "tools": {},
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_streaming_emits_trace_frames_and_done_on_success():
    """Successful run: events emitted during execution become 'trace'
    frames; the response ends with a 'done' frame whose outcome is
    'success' and whose result matches what the agent returned."""

    async def mock_execute(*args, trace=None, agent_name=None, **kwargs):
        # Exercise the trace as a real agent run would.
        start = trace.agent_start(agent_name=agent_name or "test")
        trace.stdout("hello from agent")
        trace.llm_call(provider="anthropic", model="claude-haiku-4-5", duration_ms=10.0)
        trace.agent_end(agent_name=agent_name or "test", start_ms=start, outcome="success")
        return ({"outputText": "ok"}, None)  # (result, ops_log)

    app, original, routes_mod = _make_app(mock_execute)
    try:
        client = TestClient(app)
        with client.stream("POST", "/agents/run-code/stream",
                           json=_request_payload(friendlyName="alpha")) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            body = "".join(chunk for chunk in resp.iter_text())

        frames = parse_sse_frames(body)
        events_by_kind = [f[0] for f in frames]

        # We expect: 4 trace frames (agent_start, stdout, llm_call,
        # agent_end) + 1 done frame.
        assert events_by_kind.count("trace") == 4
        assert events_by_kind.count("done") == 1
        assert events_by_kind[-1] == "done"

        # Verify event types in order.
        trace_events = [f[1] for f in frames if f[0] == "trace"]
        types = [e["type"] for e in trace_events]
        assert types == ["agent_start", "stdout", "llm_call", "agent_end"]

        # Done frame carries the outcome and result.
        done = [f[1] for f in frames if f[0] == "done"][0]
        assert done["outcome"] == "success"
        assert done["result"] == {"outputText": "ok"}
        assert done["error"] is None
    finally:
        routes_mod._execute_agent_code = original
        app.dependency_overrides = {}


def test_streaming_emits_done_with_error_when_agent_raises():
    """If the agent raises, the trace's error event still flows through
    the stream, and the done frame's outcome is 'error' with the
    exception's type:message in the error field."""

    async def mock_execute(*args, trace=None, agent_name=None, **kwargs):
        start = trace.agent_start(agent_name=agent_name or "test")
        trace.stdout("about to fail")
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError as exc:
            trace.error(exc)
            trace.agent_end(agent_name=agent_name or "test", start_ms=start, outcome="error")
            raise

    app, original, routes_mod = _make_app(mock_execute)
    try:
        client = TestClient(app)
        with client.stream("POST", "/agents/run-code/stream",
                           json=_request_payload(friendlyName="alpha")) as resp:
            assert resp.status_code == 200
            body = "".join(chunk for chunk in resp.iter_text())

        frames = parse_sse_frames(body)

        # Trace frames include the error event.
        trace_events = [f[1] for f in frames if f[0] == "trace"]
        types = [e["type"] for e in trace_events]
        assert "error" in types
        error_ev = next(e for e in trace_events if e["type"] == "error")
        assert error_ev["exception_type"] == "ZeroDivisionError"
        assert error_ev["message"] == "division by zero"

        # Done frame reports outcome=error.
        done_frames = [f[1] for f in frames if f[0] == "done"]
        assert len(done_frames) == 1
        done = done_frames[0]
        assert done["outcome"] == "error"
        assert "ZeroDivisionError" in (done["error"] or "")
        assert "division by zero" in (done["error"] or "")
        assert done["result"] is None
    finally:
        routes_mod._execute_agent_code = original
        app.dependency_overrides = {}


def test_streaming_done_includes_ops_log_and_schema_warnings():
    """The done frame also carries opsLog and schemaWarnings just like
    the bulk endpoint, so the frontend can update its data-store panel
    and surface warnings without a separate request."""

    async def mock_execute(*args, trace=None, agent_name=None, **kwargs):
        start = trace.agent_start(agent_name=agent_name or "test")
        trace.agent_end(agent_name=agent_name or "test", start_ms=start, outcome="success")
        ops = [{"op": "read", "namespace": "docs", "key": "x", "ts": "now"}]
        return ({"outputText": "ok"}, ops)

    app, original, routes_mod = _make_app(mock_execute)
    try:
        client = TestClient(app)
        with client.stream("POST", "/agents/run-code/stream",
                           json=_request_payload(
                               outputSchema={"foo": "string"},  # mismatched against {"outputText":...}
                               friendlyName="alpha",
                           )) as resp:
            body = "".join(chunk for chunk in resp.iter_text())

        frames = parse_sse_frames(body)
        done = [f[1] for f in frames if f[0] == "done"][0]
        assert done["opsLog"] == [{"op": "read", "namespace": "docs", "key": "x", "ts": "now"}]
        # outputText didn't match the declared schema {foo: string}, so
        # the validator should have flagged it.
        assert done["schemaWarnings"] is not None
        assert len(done["schemaWarnings"]) >= 1
    finally:
        routes_mod._execute_agent_code = original
        app.dependency_overrides = {}


def test_streaming_response_uses_correct_headers():
    """nginx/cloudflare buffer streaming responses by default — the
    endpoint must set X-Accel-Buffering: no and Cache-Control: no-cache
    to pass through unbuffered."""

    async def mock_execute(*args, trace=None, agent_name=None, **kwargs):
        start = trace.agent_start(agent_name=agent_name or "test")
        trace.agent_end(agent_name=agent_name or "test", start_ms=start, outcome="success")
        return ({}, None)

    app, original, routes_mod = _make_app(mock_execute)
    try:
        client = TestClient(app)
        with client.stream("POST", "/agents/run-code/stream",
                           json=_request_payload()) as resp:
            assert resp.headers["content-type"].startswith("text/event-stream")
            assert resp.headers.get("cache-control", "").lower() == "no-cache"
            assert resp.headers.get("x-accel-buffering") == "no"
            # Drain the body so the connection closes cleanly.
            for _ in resp.iter_text():
                pass
    finally:
        routes_mod._execute_agent_code = original
        app.dependency_overrides = {}


def test_streaming_friendly_name_reaches_execute_kwargs():
    """The request's friendlyName should arrive at _execute_agent_code
    as agent_name, so the trace's per-event agent_name reflects the
    actual agent rather than a placeholder."""

    captured = {}

    async def mock_execute(*args, trace=None, agent_name=None, **kwargs):
        captured["agent_name"] = agent_name
        start = trace.agent_start(agent_name=agent_name or "test")
        trace.agent_end(agent_name=agent_name or "test", start_ms=start, outcome="success")
        return ({}, None)

    app, original, routes_mod = _make_app(mock_execute)
    try:
        client = TestClient(app)
        with client.stream("POST", "/agents/run-code/stream",
                           json=_request_payload(friendlyName="my_special_agent")) as resp:
            for _ in resp.iter_text():
                pass

        assert captured["agent_name"] == "my_special_agent"
    finally:
        routes_mod._execute_agent_code = original
        app.dependency_overrides = {}


def test_sse_parser_tolerates_comment_heartbeats():
    """Sanity check on the parser: comment lines (proxy heartbeats)
    are silently ignored. We don't actually trigger the 30s heartbeat
    in the integration test (would slow the suite), but we verify the
    parser handles the format correctly."""
    body = (
        ": heartbeat\n\n"
        "event: trace\n"
        'data: {"type": "stdout", "message": "hi"}\n\n'
        ": another heartbeat\n\n"
        "event: done\n"
        'data: {"outcome": "success"}\n\n'
    )
    frames = parse_sse_frames(body)
    assert len(frames) == 2
    assert frames[0] == ("trace", {"type": "stdout", "message": "hi"})
    assert frames[1] == ("done", {"outcome": "success"})
