"""Thread-based agent executor (Path A).

Background: the streaming endpoint creates ``asyncio.create_task(run_agent_task())``
which runs the agent on the SAME event loop as the worker that received
the request. Inside, the user agent calls ``files_ns.set("foo", bar)``
synchronously — that\'s a blocking HTTP call to CouchDB. While that call
is in flight, the worker\'s event loop is fully blocked, no other
coroutine on that loop progresses. With many sequential sync calls
(asvs_download_repo does ~1300 of them) the worker is effectively
unavailable for the duration of an agent run, even though only one of
N workers is supposed to be busy.

Fix: hand the agent off to its own OS thread with its own asyncio event
loop. The worker\'s loop stays free; sync calls inside the agent only
block the agent thread\'s loop. Trace events bridge back to the
worker\'s queue via ``call_soon_threadsafe``; cancellation is a
thread-safe bool flip that the agent picks up on its next
``check_should_stop()`` call.

This module is intentionally thin — most of the cross-thread plumbing
lives in agent_trace.py and run_registry.py where the Trace knows how
to publish to a queue owned by another loop. The executor itself just
spins up the thread, runs the supplied factory inside a fresh loop,
and bridges the result back via a Future on the parent loop.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any, Awaitable, Callable

from services.cancel_token import CancelToken, bind_token, AgentStopped


async def execute_in_thread(
    coro_factory: Callable[[], Awaitable[Any]],
    cancel_token: CancelToken,
    thread_name: str = "agent-executor",
) -> Any:
    """Run ``coro_factory()`` in a fresh thread with its own event loop.

    ``coro_factory`` is a zero-arg callable that returns a coroutine.
    We accept a factory rather than a coroutine because a coroutine
    object\'s loop affinity is decided when its first ``await`` runs;
    instantiating it INSIDE the target thread keeps everything bound
    to the agent thread\'s loop. Passing a pre-built coroutine here
    would attach it to the caller\'s loop and defeat the point.

    The CancelToken is re-bound inside the target thread\'s context
    so the agent\'s ``check_should_stop()`` sees it. ContextVar
    bindings don\'t cross thread boundaries on their own; we re-set
    explicitly. Setting the bit from the worker loop (POST /runs/
    <id>/stop) is fine — bools are thread-safe to read and write.

    Cancellation: we install an on_stop callback on the CancelToken
    that calls task.cancel() on the agent\'s task via
    call_soon_threadsafe. This interrupts the agent at the next
    await -- including mid-LLM-call, mid-httpx-request, etc. Without
    this, check_should_stop only fires at structural boundaries,
    which means a stop during a multi-minute Bedrock call doesn\'t
    take effect until the call returns. The agent runner wraps the
    resulting CancelledError as AgentStopped so the streaming
    endpoint\'s existing is_stop detection picks it up unchanged.

    Returns the coroutine\'s result or re-raises its exception on
    the calling task. Exceptions propagate naturally through the
    Future\'s ``set_exception``.
    """
    parent_loop = asyncio.get_running_loop()
    result_future: asyncio.Future = parent_loop.create_future()

    # Shared state for the on_stop callback to reach into the agent
    # thread. Worker reads, agent thread writes. Plain dict; CPython
    # GIL makes the simple set/get ops atomic, and we tolerate the
    # benign race of stop arriving before task creation (callback
    # sees task=None, does nothing; the bit is still set, so the
    # first await in the agent will be cancelled once the task IS
    # created).
    thread_state: dict = {"loop": None, "task": None}

    def _on_stop() -> None:
        loop = thread_state.get("loop")
        task = thread_state.get("task")
        if loop is None or task is None:
            return
        # Schedule the cancellation on the agent\'s own loop. cancel()
        # on a done task is idempotent.
        try:
            loop.call_soon_threadsafe(task.cancel)
        except RuntimeError:
            # Loop has already closed -- nothing to do.
            pass

    cancel_token.set_on_stop(_on_stop)

    def thread_entry() -> None:
        thread_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(thread_loop)
            # The cancel token contextvar binding doesn\'t inherit
            # across thread boundaries; bind it inside this thread\'s
            # context so check_should_stop() at structural boundaries
            # inside the agent sees the token.
            bind_token(cancel_token)

            async def runner():
                try:
                    return await coro_factory()
                except asyncio.CancelledError:
                    # Convert task cancellation to AgentStopped so the
                    # streaming endpoint\'s except branch can detect
                    # it the same way it detects a structural-boundary
                    # stop. CancelledError inherits from BaseException
                    # (not Exception) in Python 3.8+, so it wouldn\'t
                    # otherwise be caught by run_agent_task\'s except.
                    raise AgentStopped("Run was cancelled by stop request")

            try:
                task = thread_loop.create_task(runner())
                thread_state["loop"] = thread_loop
                thread_state["task"] = task
                result = thread_loop.run_until_complete(task)
                parent_loop.call_soon_threadsafe(_set_result_safe, result_future, result)
            except BaseException as exc:
                parent_loop.call_soon_threadsafe(_set_exception_safe, result_future, exc)
        finally:
            # Clear the on_stop hook so a late stop from another
            # request (highly unlikely but possible if the registry
            # entry hasn\'t evicted yet) doesn\'t fire into a closed
            # loop.
            cancel_token.set_on_stop(None)
            # Drain pending background tasks before closing the loop.
            # Litellm spins up an internal LoggingWorker coroutine
            # that owns a queue and a long-running task on whatever
            # loop is current when the first litellm call happens.
            # In Path A that's this thread's loop. If we close the
            # loop while the worker is still alive, its next
            # call_soon (asyncio.Queue.get's getter.cancel path) hits
            # a closed loop and raises 'RuntimeError: Event loop is
            # closed', which Python surfaces as 'Exception ignored
            # in: <coroutine object LoggingWorker._worker_loop>'.
            # Harmless but noisy in the api logs.
            #
            # Cancel any task still around, give the loop one tick
            # to process the cancellations, then close cleanly.
            try:
                pending = [t for t in asyncio.all_tasks(thread_loop)
                           if not t.done()]
                for t in pending:
                    t.cancel()
                if pending:
                    thread_loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                # Best-effort drain; if it raises we still want to
                # close the loop below rather than leak it.
                pass
            try:
                thread_loop.close()
            except Exception:
                pass

    threading.Thread(target=thread_entry, daemon=True, name=thread_name).start()
    return await result_future


def _set_result_safe(future: asyncio.Future, result: Any) -> None:
    """Set a future\'s result iff still pending.

    If the parent task was cancelled or otherwise resolved before the
    agent thread finished, the future may already be done. Silently
    skip the second resolve rather than raising InvalidStateError back
    into call_soon_threadsafe (which would surface as an uncaught
    exception on the parent loop\'s exception handler).
    """
    if not future.done():
        future.set_result(result)


def _set_exception_safe(future: asyncio.Future, exc: BaseException) -> None:
    if not future.done():
        future.set_exception(exc)
