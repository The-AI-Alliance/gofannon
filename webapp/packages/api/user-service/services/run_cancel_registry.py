"""Per-run cancel-token registry.

A small dict keyed by run_id that holds the active CancelToken for each
in-flight run. Maintained alongside (and independently of) the run
registry: the run launcher binds a fresh CancelToken, publishes it here
so ``POST /runs/{id}/stop`` can find it, and resets on completion.

If no runner has published a token for a run, stop calls on it return
404.
"""
from __future__ import annotations

from typing import Dict, Optional

from services.cancel_token import CancelToken


_tokens: Dict[str, CancelToken] = {}


def publish(run_id: str, token: CancelToken) -> None:
    _tokens[run_id] = token


def get(run_id: str) -> Optional[CancelToken]:
    return _tokens.get(run_id)


def clear(run_id: str) -> None:
    _tokens.pop(run_id, None)


def reset_for_tests() -> None:
    _tokens.clear()
