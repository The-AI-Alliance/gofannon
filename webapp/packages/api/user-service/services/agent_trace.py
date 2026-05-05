"""Per-run trace collector for the agent runtime.

When an agent executes in the sandbox, every meaningful event —
agent_start, agent_end, llm_call, data_store, log, stdout, error —
is appended to a shared Trace bound via contextvar. The route handler
ships the accumulated trace back to the client in the RunCodeResponse,
which renders it in the sandbox's Progress Log accordion.

Why a contextvar instead of plumbing the collector through every call:
the LLM service is many layers below the agent runtime entry point and
is also called directly from agent code via tools.call_llm. Threading a
trace argument through every call site means changing public function
signatures and forcing every caller (including agents) to know about
tracing. A contextvar lets each layer ask "is there an active trace?"
and emit if yes, with no signature change. The contextvar is set in
_execute_agent_code's outer scope and reset on exit.

Security note: agent print()/log output is captured into the trace,
which is shown in the UI and could be persisted later. We cap individual
event message length and total event count, and we tag each event with
``source`` so future filtering (e.g., "drop user-origin events when
shipping to a customer-visible audit log") is mechanical. An operator
can disable user-origin capture entirely by setting
GOFANNON_DISABLE_USER_TRACE=1 — the structural events (agent_start,
llm_call, etc.) are still emitted; just the noisy stdout/log channel
is silenced.
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import os
import sys
import time
import traceback
import uuid

from services.log_redaction import redact
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Per-event message cap. Stops a runaway agent from logging a huge buffer
# (e.g. an entire LLM response or a 50KB stack trace) and ballooning
# memory or response size. 4 KB is generous for any single line.
MAX_EVENT_MESSAGE_BYTES = 4096

# Per-run total event cap. A single run that emits more than this many
# events is almost certainly stuck in a loop. We append a synthetic
# "trace truncated" event and silently discard the rest.
MAX_EVENTS_PER_TRACE = 2000


def _user_trace_enabled() -> bool:
    """Operator can disable user-origin (stdout/log) capture."""
    return os.getenv("GOFANNON_DISABLE_USER_TRACE", "").lower() not in ("1", "true", "yes")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ms() -> float:
    return time.monotonic() * 1000.0


def _truncate(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    if len(s) <= MAX_EVENT_MESSAGE_BYTES:
        return s
    return s[:MAX_EVENT_MESSAGE_BYTES] + f"\n... [truncated, {len(s) - MAX_EVENT_MESSAGE_BYTES} more bytes]"


class Trace:
    """Mutable container for events emitted during a single sandbox run.

    Not thread-safe. Each sandbox request gets its own Trace; the
    contextvar binding scopes it to the asyncio task tree.
    """

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self._truncated = False
        self._depth = 0  # current nesting level for chained agent calls
        self._stack: List[str] = []  # current agent_name stack
        # Optional asyncio.Queue for live streaming. When set (via
        # attach_queue), every append() also publishes the event to
        # the queue so a streaming response handler can yield it
        # over SSE. None for non-streaming runs (the bulk-trace
        # path through /agents/run-code).
        self._queue: Optional[asyncio.Queue] = None

    def attach_queue(self, queue: asyncio.Queue) -> None:
        """Attach a queue that receives every appended event.

        Events that were already in self.events when this is called
        are NOT replayed — attach the queue before any events are
        emitted. The streaming handler does this immediately after
        creating the Trace.
        """
        self._queue = queue

    def _current_agent(self) -> str:
        return self._stack[-1] if self._stack else "unknown"

    def append(self, event: Dict[str, Any]) -> None:
        if self._truncated:
            return
        if len(self.events) >= MAX_EVENTS_PER_TRACE:
            trunc_event = {
                "type": "trace_truncated",
                "ts": _now_iso(),
                "agent_name": self._current_agent(),
                "depth": self._depth,
                "source": "system",
                "message": f"Trace exceeded {MAX_EVENTS_PER_TRACE} events; subsequent events dropped.",
            }
            self.events.append(trunc_event)
            self._publish(trunc_event)
            self._truncated = True
            return
        self.events.append(event)
        self._publish(event)

    def _publish(self, event: Dict[str, Any]) -> None:
        """Push to the streaming queue if one is attached.

        We use put_nowait so emitters never block on a slow consumer.
        If the queue fills up (consumer disconnected, etc.), the
        event is silently dropped from the stream — but it stays in
        self.events, so the final response payload is still
        complete. asyncio.Queue with default maxsize=0 is unbounded;
        callers can pass a bounded queue if they want backpressure.
        """
        if self._queue is None:
            return
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    # ------------------------------------------------------------------
    # Structural events. Always emitted regardless of GOFANNON_DISABLE_USER_TRACE.
    # ------------------------------------------------------------------

    def agent_start(self, agent_name: str, agent_id: Optional[str] = None,
                    called_by: Optional[str] = None) -> float:
        """Push an agent onto the stack and return the start timestamp.

        The caller passes the returned value back to ``agent_end`` so we
        can compute duration without keeping more state on the Trace.
        """
        self._stack.append(agent_name)
        start_ms = _now_ms()
        self.append({
            "type": "agent_start",
            "ts": _now_iso(),
            "agent_name": agent_name,
            "agent_id": agent_id,
            "depth": self._depth,
            "called_by": called_by,
            "source": "system",
        })
        self._depth += 1
        return start_ms

    def agent_end(self, agent_name: str, start_ms: float,
                  outcome: str = "success",
                  result_preview: Optional[str] = None) -> None:
        self._depth = max(0, self._depth - 1)
        duration_ms = _now_ms() - start_ms
        self.append({
            "type": "agent_end",
            "ts": _now_iso(),
            "agent_name": agent_name,
            "depth": self._depth,
            "duration_ms": round(duration_ms, 1),
            "outcome": outcome,
            "result_preview": _truncate(result_preview) if result_preview else None,
            "source": "system",
        })
        if self._stack and self._stack[-1] == agent_name:
            self._stack.pop()

    def llm_call(self, provider: str, model: str,
                 input_tokens: Optional[int] = None,
                 output_tokens: Optional[int] = None,
                 duration_ms: Optional[float] = None,
                 cost_usd: Optional[float] = None,
                 error: Optional[str] = None) -> None:
        self.append({
            "type": "llm_call",
            "ts": _now_iso(),
            "agent_name": self._current_agent(),
            "depth": self._depth,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": round(duration_ms, 1) if duration_ms is not None else None,
            "cost_usd": cost_usd,
            "error": _truncate(error) if error else None,
            "source": "system",
        })

    def data_store(self, op: str, namespace: str, key: Optional[str] = None,
                   found: Optional[bool] = None, count: Optional[int] = None) -> None:
        self.append({
            "type": "data_store",
            "ts": _now_iso(),
            "agent_name": self._current_agent(),
            "depth": self._depth,
            "operation": op,
            "namespace": namespace,
            "key": key,
            "found": found,
            "count": count,
            "source": "system",
        })

    def error(self, exception: BaseException) -> None:
        """Emit a structural error event with the formatted traceback.

        Errors are always captured even with GOFANNON_DISABLE_USER_TRACE —
        they're the most useful payload in the trace and the agent won't
        be running after this anyway.
        """
        tb_str = traceback.format_exc()
        self.append({
            "type": "error",
            "ts": _now_iso(),
            "agent_name": self._current_agent(),
            "depth": self._depth,
            "exception_type": type(exception).__name__,
            "message": _truncate(str(exception)),
            "traceback": _truncate(tb_str),
            "source": "system",
        })

    # ------------------------------------------------------------------
    # User-origin events. Suppressed when GOFANNON_DISABLE_USER_TRACE=1.
    # ------------------------------------------------------------------

    def stdout(self, line: str) -> None:
        if not _user_trace_enabled():
            return
        line = line.rstrip("\n")
        if not line:
            return
        # Scrub credentials before the line lands in the trace events
        # list (and from there into the SSE stream + final response).
        # Redaction is best-effort and never raises; see
        # services/log_redaction.py for the patterns and failure model.
        line = redact(line)
        self.append({
            "type": "stdout",
            "ts": _now_iso(),
            "agent_name": self._current_agent(),
            "depth": self._depth,
            "message": _truncate(line),
            "source": "stdout",
        })

    def log(self, level: str, message: str, logger_name: Optional[str] = None) -> None:
        if not _user_trace_enabled():
            return
        # Scrub credentials. See stdout() above for rationale.
        message = redact(message)
        self.append({
            "type": "log",
            "ts": _now_iso(),
            "agent_name": self._current_agent(),
            "depth": self._depth,
            "level": level,
            "logger": logger_name,
            "message": _truncate(message),
            "source": "log",
        })


# ----------------------------------------------------------------------
# Contextvar binding
# ----------------------------------------------------------------------

_current_trace: contextvars.ContextVar[Optional[Trace]] = contextvars.ContextVar(
    "gofannon_agent_trace", default=None
)


def get_current_trace() -> Optional[Trace]:
    return _current_trace.get()


@contextmanager
def bind_trace(trace: Trace):
    """Bind a Trace as the active collector for the contextvar lifetime.

    Used at the top of _execute_agent_code so every nested call (LLM
    service, data store proxy, gofannon-client recursion) can find the
    same Trace via get_current_trace().
    """
    token = _current_trace.set(trace)
    try:
        yield trace
    finally:
        _current_trace.reset(token)


# ----------------------------------------------------------------------
# stdout/stderr capture — context manager
# ----------------------------------------------------------------------

class _LineBufferingStream:
    """File-like wrapper that splits writes into newline-terminated lines
    and forwards each line to a callback.

    Why this exists: print() does multiple writes per logical line ("hello",
    " ", "world", "\\n"). We need to buffer until \\n then flush a single
    line into the trace. Otherwise every print() gets fragmented across
    several events.
    """

    def __init__(self, on_line, original_stream):
        self._on_line = on_line
        self._original = original_stream
        self._buf: List[str] = []

    def write(self, s: str) -> int:
        # Mirror to the original stream too so server logs still see it.
        try:
            self._original.write(s)
        except Exception:
            pass
        if not isinstance(s, str):
            s = str(s)
        for chunk in s.splitlines(keepends=True):
            self._buf.append(chunk)
            if chunk.endswith("\n"):
                line = "".join(self._buf)
                self._buf = []
                try:
                    self._on_line(line)
                except Exception:
                    pass
        return len(s)

    def flush(self) -> None:
        try:
            self._original.flush()
        except Exception:
            pass
        if self._buf:
            line = "".join(self._buf)
            self._buf = []
            try:
                self._on_line(line)
            except Exception:
                pass

    def __getattr__(self, name):
        return getattr(self._original, name)


class _TraceLogHandler(logging.Handler):
    """logging.Handler that forwards records to the active Trace."""

    def emit(self, record: logging.LogRecord) -> None:
        trace = get_current_trace()
        if trace is None:
            return
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        trace.log(record.levelname, msg, logger_name=record.name)


@contextmanager
def capture_user_io(trace: Trace):
    """Capture stdout, stderr, and root-logger output into the trace
    for the duration of the context.

    Restores all three on exit, even if the agent raised. Safe to nest
    (stdout/stderr replacement is idempotent because we only swap once).
    """
    if not _user_trace_enabled():
        yield
        return

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = _LineBufferingStream(trace.stdout, original_stdout)
    sys.stderr = _LineBufferingStream(trace.stdout, original_stderr)

    handler = _TraceLogHandler()
    handler.setLevel(logging.NOTSET)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    try:
        yield
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        root_logger.removeHandler(handler)


# ----------------------------------------------------------------------
# Convenience: run-id generator. Frontend uses this to key per-run
# accordion sections; backend passes it back so the client can correlate
# request → response when multiple runs happen quickly.
# ----------------------------------------------------------------------

def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
