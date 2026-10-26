"""Cooperative cancellation primitive.

A ``CancelToken`` is a tiny flag-with-a-method-name. It's bound to an
asyncio task via a ``ContextVar`` so structurally distant code paths
(LLM service, data-store proxy, gofannon-client) can poll it without a
signature change. asyncio task context inheritance means a chained
agent automatically shares the parent's token — stopping the parent
stops the children.

Enforcement happens at *structural boundaries*: at entry to each
tool invocation we call ``check_should_stop()``, which raises
``AgentStopped`` if the token has been set. In-flight LLM HTTP
requests finish naturally; only the *next* observable action is
interrupted. This is intentionally less aggressive than
``task.cancel()``, which would interrupt mid-await and skip cleanup
handlers.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional


class AgentStopped(BaseException):
    """Raised when a run's cancel token is set and a structural check fires.

    Inherits from BaseException (not Exception) deliberately, mirroring
    asyncio.CancelledError, KeyboardInterrupt, and SystemExit:
    cancellation signals must propagate through user code unimpeded. If
    AgentStopped were Exception, a single ``except Exception`` anywhere
    in the agent code would swallow the cancel and the agent would
    continue. The asvs_* agents in particular do exactly this -- broad
    try/except around data store loads -- and a stop request would log
    a warning per chapter and roll on regardless. Making AgentStopped
    BaseException forces it to bubble past those handlers to the
    streaming endpoint's explicit catch where mark_complete fires.
    """


@dataclass
class CancelToken:
    """Trivial boolean flag, intentionally not thread-safe.

    asyncio task switching never preempts a sync attribute write, so the
    obvious dataclass works. Adding a Lock would be slower without
    being safer.

    Optional on_stop hook fires when request_stop() is called. The
    Path A executor uses this to also cancel the agent task on its
    own loop -- without it, an agent mid-LLM-call doesn't notice the
    stop until the LLM call returns, because check_should_stop only
    fires at structural boundaries. Task cancellation interrupts at
    the next await, which is exactly the await we're stuck on.
    """
    _stopped: bool = False
    _on_stop: Optional["object"] = None  # zero-arg callable

    def request_stop(self) -> None:
        self._stopped = True
        cb = self._on_stop
        if cb is not None:
            try:
                cb()
            except Exception:
                # Callback failures must never propagate out of
                # request_stop -- the stop bit is the source of truth
                # for cooperative cancellation; the callback is just
                # the prompt-interrupt optimization.
                pass

    def is_stopped(self) -> bool:
        return self._stopped

    def set_on_stop(self, cb) -> None:
        """Register a zero-arg callable to fire on request_stop. The
        callable runs synchronously from whatever thread called
        request_stop(); it must be cheap and thread-safe (typically
        loop.call_soon_threadsafe to schedule actual work elsewhere).
        Passing None clears the hook."""
        self._on_stop = cb


_token: ContextVar[Optional[CancelToken]] = ContextVar("cancel_token", default=None)


def bind_token(token: CancelToken):
    """Set the active token for the current task. Returns the contextvar
    Token so the caller can ``reset()`` if they need to."""
    return _token.set(token)


def reset_token(ctx_token) -> None:
    _token.reset(ctx_token)


def current_token() -> Optional[CancelToken]:
    return _token.get()


def should_stop() -> bool:
    tok = _token.get()
    return tok.is_stopped() if tok else False


def check_should_stop() -> None:
    """Raise ``AgentStopped`` if the bound token has been set.

    Call at the entry to each tool function so a stop request takes
    effect at the next structural boundary.
    """
    if should_stop():
        raise AgentStopped("Run was stopped by user")
