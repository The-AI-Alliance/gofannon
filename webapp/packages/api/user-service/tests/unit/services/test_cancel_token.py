"""Unit tests for cooperative cancellation."""
from __future__ import annotations

import asyncio

import pytest

from services.cancel_token import (
    AgentStopped,
    CancelToken,
    bind_token,
    check_should_stop,
    current_token,
    reset_token,
    should_stop,
)
from services import run_cancel_registry


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_registry():
    run_cancel_registry.reset_for_tests()
    yield
    run_cancel_registry.reset_for_tests()


def test_default_should_stop_is_false():
    assert should_stop() is False


def test_bound_token_visible_via_should_stop():
    tok = CancelToken()
    ctx = bind_token(tok)
    try:
        assert should_stop() is False
        tok.request_stop()
        assert should_stop() is True
    finally:
        reset_token(ctx)


def test_check_should_stop_raises_when_set():
    tok = CancelToken()
    ctx = bind_token(tok)
    try:
        tok.request_stop()
        with pytest.raises(AgentStopped):
            check_should_stop()
    finally:
        reset_token(ctx)


def test_check_should_stop_does_not_raise_when_unset():
    tok = CancelToken()
    ctx = bind_token(tok)
    try:
        check_should_stop()  # no exception
    finally:
        reset_token(ctx)


def test_chained_tasks_inherit_token():
    """asyncio task created from within a token-bound task inherits the
    same contextvar — stopping the parent stops the child."""
    tok = CancelToken()
    results = {}

    async def child():
        # Child sees the parent's token via contextvar inheritance.
        results["child_sees"] = should_stop()

    async def parent():
        ctx = bind_token(tok)
        try:
            tok.request_stop()
            child_task = asyncio.create_task(child())
            await child_task
        finally:
            reset_token(ctx)

    asyncio.run(parent())
    assert results["child_sees"] is True


def test_run_cancel_registry_publish_get_clear():
    tok = CancelToken()
    run_cancel_registry.publish("r-1", tok)
    assert run_cancel_registry.get("r-1") is tok
    run_cancel_registry.clear("r-1")
    assert run_cancel_registry.get("r-1") is None


def test_run_cancel_registry_get_missing_returns_none():
    assert run_cancel_registry.get("nope") is None
