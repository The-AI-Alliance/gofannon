# Agent Runtime Trace

This document explains the per-run trace mechanism that powers the sandbox's Progress Log accordion, including how to disable user-origin capture for production-deployed agents.

## Overview

When an agent runs in the sandbox, `services/agent_trace.py` collects a structured per-run timeline of everything it does — agent invocations, LLM calls, data store operations, errors, and (by default) user-origin output like `print()` calls and `logging` records. The trace ships back in `RunCodeResponse.trace` and renders in the sandbox UI's Progress Log accordion, grouped per agent and with errors highlighted.

The trace is in-memory only. It exists for the duration of a single sandbox request and is shipped to the client; nothing is persisted server-side.

## Event Types

Each entry in the trace is a dict with at minimum `type`, `ts`, `agent_name`, `depth`, and `source`. Type-specific fields are documented in `services/agent_trace.py`.

| Type | When emitted | Source |
|---|---|---|
| `agent_start` | Agent's `run()` is about to be invoked | `system` |
| `agent_end` | `run()` returned (or raised) | `system` |
| `llm_call` | A call through `tools.call_llm` completed (or failed) | `system` |
| `data_store` | A data store operation (read/write/list/etc.) | `system` |
| `error` | The agent's `run()` raised | `system` |
| `stdout` | A line was written to stdout or stderr | `stdout` |
| `log` | A `logging` record was emitted | `log` |
| `trace_truncated` | Per-run event cap reached; subsequent events dropped | `system` |

The `source` tag is the lever for filtering: structural events (`source: "system"`) are always emitted; user-origin events (`source: "stdout"` or `"log"`) can be disabled — see below.

## Disabling User-Origin Capture

Set `GOFANNON_DISABLE_USER_TRACE=1` (or `true`, or `yes` — case-insensitive) in the API container's environment to suppress stdout, stderr, and `logging` capture. Structural events still emit, so the Progress Log still shows the agent's call graph, LLM calls, data store ops, and errors — just not the agent's printed output.

```yaml
# docker-compose.yml — disable user-origin capture in production-like envs
services:
  api:
    environment:
      - GOFANNON_DISABLE_USER_TRACE=1
```

### Why You Might Want To

The sandbox is a development tool; capturing `print()` is wonderful for debugging. But the same mechanism is in the runtime path, so once you start running agents in environments where the trace is visible to humans who shouldn't see everything (a customer-facing dashboard, a multi-tenant deployment, a logged audit trail), you have to think about what could leak:

- An agent that received an API key as part of its input and prints the input dict for debugging
- Raw user PII in logged data
- An OAuth token returned by a tool call and logged
- Any data the agent processes that's more sensitive than the trace's audience

For the local sandbox, none of that matters. For anything beyond, set the env var.

### What's Still Captured When Disabled

The structural events are still in the trace. So even with `GOFANNON_DISABLE_USER_TRACE=1`:

- You see which agents ran, in what order, with what duration
- LLM calls show provider/model and (when surfaced) tokens
- Data store operations show namespace/key/op
- Errors include the exception type, message, and full traceback

The structural events are derived from the runtime's instrumentation points, not from the agent's own output, so they don't leak the agent's domain data. Tracebacks can technically include local variable values via `traceback.format_exc` if a frame's repr exposes them, but the standard format doesn't dump locals — only the source line at the failure point. If even that is too much, you'd need a follow-up that strips traceback frames inside `Trace.error`.

## Caps

Two safety caps prevent a runaway agent from consuming unbounded memory or producing a multi-megabyte response payload:

| Cap | Default | Constant |
|---|---|---|
| Per-event message size | 4 KB | `MAX_EVENT_MESSAGE_BYTES` |
| Per-trace event count | 2000 | `MAX_EVENTS_PER_TRACE` |

Hitting the per-event cap appends a `... [truncated, N more bytes]` marker to the message and continues. Hitting the per-trace cap appends a `trace_truncated` event and silently drops everything else.

These constants live at the top of `services/agent_trace.py` and can be tuned if you find them too tight or too loose for your use case.

## Implementation Notes

### Contextvar binding

The `Trace` object is bound to the current asyncio task tree via `contextvars.ContextVar`. This means nested layers — the LLM service wrapper in `dependencies.py`, the data store proxy, the recursive `GofannonClient.call` for chained agents — can call `get_current_trace()` and emit events without having to thread the collector through every function signature. Threading by argument would touch a dozen public APIs and force agent code itself to be aware of tracing; the contextvar keeps it transparent.

### stdout/stderr line buffering

`_LineBufferingStream` wraps the original stream and accumulates writes until it sees a `\n`, at which point it flushes one line into `Trace.stdout`. Without this buffering, a single `print("hello")` would emit several events (one per write call from the print mechanism — `"hello"`, `" "`, `"\n"`, etc.). It also mirrors writes to the original stream, so server logs still see the agent's output normally.

### `logging` capture

A `_TraceLogHandler` is added to the root logger for the duration of `capture_user_io`, then removed. This catches calls to `logging.info(...)` and similar from inside the agent. It does *not* catch the user service's own internal logging — those go through the observability service, which has its own handler chain.

### Failure-path response

When an agent raises, the route handler returns a structured `RunCodeResponse` with `error` and `trace` populated rather than raising an HTTP error. This is intentional: the partial trace is the most useful payload for debugging, and forcing the client to deal with both a 500-ish error code AND a separate trace endpoint would make the Progress Log harder to keep in sync. The downside is that the HTTP status is 200 even on agent errors; clients that want to distinguish "the agent ran and failed" from "the agent ran and succeeded" have to inspect `response.error`.

## Adding New Event Types

To add a new event type — say, you want to instrument MCP server calls:

1. Add a method on `Trace` (e.g., `mcp_call`) that builds the event dict and calls `self.append(...)`.
2. Pick a `type` string. Pick a `source` (likely `"system"`).
3. Find the call site you want to instrument. Pull the active trace via `get_current_trace()`. If non-None, call your new method.
4. Update the frontend's `eventSummary` and `eventColor` in `SandboxProgressLog.jsx` to render the new type.

The shape is permissive — extra fields on an event are ignored by the renderer, so you can add provider-specific metadata without coordinating frontend changes for each addition.