"""Tests for the Path A thread-based agent executor.

The three invariants we care about:

1. **Worker loop isolation.** Sync-blocking work inside the agent
   (think ``time.sleep`` or a sync HTTP call to CouchDB) does NOT
   stop the worker's event loop from progressing other coroutines.
2. **Trace bridge.** Events the agent appends from its side-thread
   end up on the queue owned by the worker loop, in the right order.
3. **Cross-thread cancellation.** A cancel-bit flipped from the
   worker loop is observed by the agent on its next
   ``check_should_stop()`` call.

These tests use ``time.sleep`` rather than a real HTTP call to keep
the suite hermetic; the semantics are the same — both block the
calling thread without yielding to its event loop.
"""
import asyncio
import time

import pytest

from services.agent_executor import execute_in_thread
from services.agent_trace import Trace
from services.cancel_token import CancelToken, check_should_stop, AgentStopped


@pytest.mark.asyncio
async def test_worker_loop_stays_responsive_during_agent_block():
    """A 500ms sync block in the agent must not freeze the worker
    loop for 500ms — heartbeats must keep ticking."""

    async def agent_coro():
        time.sleep(0.5)
        return "agent-done"

    heartbeats = []

    async def heartbeat():
        for _ in range(15):
            heartbeats.append(time.monotonic())
            await asyncio.sleep(0.05)

    hb = asyncio.create_task(heartbeat())
    result = await execute_in_thread(agent_coro, CancelToken())
    await hb

    assert result == "agent-done"
    gaps_ms = [(heartbeats[i + 1] - heartbeats[i]) * 1000 for i in range(len(heartbeats) - 1)]
    # If isolation works, all gaps are ~50ms. Without it, one gap
    # is ~500ms (the sleep) and others ~0ms. Generous 200ms ceiling
    # absorbs CI jitter.
    assert max(gaps_ms) < 200, f"worker loop blocked; max gap was {max(gaps_ms):.0f}ms"


@pytest.mark.asyncio
async def test_trace_events_bridge_from_agent_thread():
    """Events appended from inside the agent reach the worker
    queue intact and in order, via call_soon_threadsafe."""
    trace = Trace()
    queue = asyncio.Queue()
    trace.attach_queue(queue, loop=asyncio.get_running_loop())

    async def agent_coro():
        for i in range(5):
            trace.append({"type": "log", "message": f"event {i}"})
        return "ok"

    await execute_in_thread(agent_coro, CancelToken())

    # Drain whatever the threadsafe routing has put on the queue.
    # call_soon_threadsafe is asynchronous-ish; give the loop a
    # tick or two to drain pending callbacks.
    await asyncio.sleep(0.01)
    received = []
    while not queue.empty():
        received.append(queue.get_nowait())

    assert len(received) == 5
    for i, ev in enumerate(received):
        assert ev["message"] == f"event {i}"


@pytest.mark.asyncio
async def test_cancel_token_works_across_threads():
    """A cancel bit flipped from the worker loop is observed by the
    agent's next check_should_stop() inside its thread."""
    cancel = CancelToken()

    async def agent_coro():
        for _ in range(100):
            check_should_stop()  # raises AgentStopped once cancel is set
            time.sleep(0.01)
        return "not-reached"

    async def stopper():
        await asyncio.sleep(0.05)
        cancel.request_stop()

    asyncio.create_task(stopper())

    with pytest.raises(AgentStopped):
        await execute_in_thread(agent_coro, cancel)


@pytest.mark.asyncio
async def test_stop_interrupts_mid_await():
    """request_stop() interrupts the agent at its next await, not at
    its next check_should_stop() structural boundary. This is what
    makes a stop pressed during a long Bedrock call take effect
    immediately instead of after the call returns."""
    import time as _t
    cancel = CancelToken()

    async def agent_coro():
        # An await with no check_should_stop boundaries -- analogue
        # of a long-running LLM call.
        await asyncio.sleep(10.0)
        return "should-not-reach-here"

    async def stopper():
        await asyncio.sleep(0.1)
        cancel.request_stop()

    asyncio.create_task(stopper())

    start = _t.monotonic()
    with pytest.raises(AgentStopped):
        await execute_in_thread(agent_coro, cancel)
    elapsed = _t.monotonic() - start
    # Should resolve within 1s of the stopper firing at 0.1s -- if
    # cancel isn\'t mid-await-aware, this would take the full 10s.
    assert elapsed < 1.5, (
        f"stop should take effect mid-await; took {elapsed:.2f}s"
    )


@pytest.mark.asyncio
async def test_agent_stopped_escapes_except_exception():
    """Regression: agents' broad `except Exception as e: log; continue`
    patterns must not swallow AgentStopped. The asvs_orchestrate agent
    in particular wraps an ASVS-load call in try/except Exception; with
    AgentStopped as Exception the agent caught it, logged a warning per
    chapter, dropped sections it couldn't classify, and rolled through
    to a useless 0-section output instead of stopping. Making
    AgentStopped a BaseException (mirroring asyncio.CancelledError's
    Python 3.8 reparenting) makes broad except clauses pass it through."""
    from services.cancel_token import (
        AgentStopped, CancelToken, bind_token, check_should_stop,
    )

    cancel = CancelToken()

    async def agent_with_broad_except():
        bind_token(cancel)
        survivors = 0
        for _ in range(5):
            try:
                check_should_stop()
                survivors += 1
            except Exception:  # the asvs_* pattern
                survivors += 100  # marker: if this fires, test fails
        return survivors

    # Sanity: with bit not set, agent runs 5 iters normally.
    assert await agent_with_broad_except() == 5

    # Flip the bit. AgentStopped should escape the except Exception
    # and abort the agent.
    cancel.request_stop()
    with pytest.raises(AgentStopped):
        await agent_with_broad_except()
