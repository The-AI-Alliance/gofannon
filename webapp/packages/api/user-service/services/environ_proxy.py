"""Per-agent environment variable overlay.

Wraps ``os.environ`` with a contextvar-bound overlay so each agent run can
see its own ``env_vars`` without mutating shared process state. asyncio
tasks inherit contextvar context, so concurrent runs see different
overlays without locking.

Usage from request handler / runner::

    from services.environ_proxy import install_environ_proxy, env_overlay

    install_environ_proxy()                       # once, at process startup
    with env_overlay({"OPUS_CONCURRENCY": "8"}):  # per-run
        await agent.run(...)

The proxy is a transparent ``MutableMapping``-shaped wrapper; ``os.environ.get``,
``os.environ["KEY"]``, and ``key in os.environ`` all consult the overlay first
and fall back to the real environ. Mutations write to the real environ
(unchanged behavior — agents that intentionally modify the host environ
keep working; the overlay only affects *reads*).
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Mapping, Optional


_overlay: ContextVar[Optional[Mapping[str, str]]] = ContextVar(
    "agent_env_overlay", default=None
)


class _EnvironProxy:
    """Wraps an existing ``os.environ``-like mapping with a contextvar overlay.

    Reads consult the overlay first; misses and mutations pass through to the
    wrapped real environ. We expose just enough of ``os.environ``'s interface
    that ``os.environ["X"]``, ``.get(...)``, ``in``, ``setdefault``, ``pop``,
    iteration, and ``len`` all work.
    """

    def __init__(self, real):
        # Keep a reference to the genuine os.environ (the underlying _Environ).
        self._real = real

    # ----- read path: consult overlay first -----

    def __getitem__(self, key):
        ov = _overlay.get()
        if ov is not None and key in ov:
            return ov[key]
        return self._real[key]

    def get(self, key, default=None):
        ov = _overlay.get()
        if ov is not None and key in ov:
            return ov[key]
        return self._real.get(key, default)

    def __contains__(self, key):
        ov = _overlay.get()
        if ov is not None and key in ov:
            return True
        return key in self._real

    def __iter__(self):
        # Iteration sees both overlay and real environ, overlay values win.
        ov = _overlay.get() or {}
        seen = set()
        for k in ov:
            seen.add(k)
            yield k
        for k in self._real:
            if k not in seen:
                yield k

    def __len__(self):
        ov = _overlay.get() or {}
        return len(set(ov) | set(self._real))

    def keys(self):
        return list(iter(self))

    def items(self):
        for k in self:
            yield k, self[k]

    def values(self):
        for k in self:
            yield self[k]

    # ----- write path: passthrough to real environ -----

    def __setitem__(self, key, value):
        self._real[key] = value

    def __delitem__(self, key):
        del self._real[key]

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
            return default
        return self[key]

    def pop(self, key, *args):
        return self._real.pop(key, *args)

    def update(self, *args, **kwargs):
        self._real.update(*args, **kwargs)

    def copy(self):
        # Return a plain dict snapshot including overlay values.
        return dict(self.items())

    def __repr__(self):
        return f"_EnvironProxy({self._real!r})"


_installed = False


def install_environ_proxy() -> None:
    """Replace ``os.environ`` with an ``_EnvironProxy`` once.

    Idempotent — calling twice is a no-op. Call once at process startup
    (typically from ``app_factory.create_app`` or ``main`` before any
    agent code runs).
    """
    global _installed
    if _installed:
        return
    proxy = _EnvironProxy(os.environ)
    os.environ = proxy  # type: ignore[assignment]
    _installed = True


@contextmanager
def env_overlay(overlay: Mapping[str, str]) -> Iterator[None]:
    """Bind an overlay for the duration of the ``with`` block.

    The new overlay is LAYERED over any enclosing overlay rather than
    replacing it, so an agent that calls another agent passes its
    env_vars down the call chain. Precedence, innermost first::

        callee's own env_vars
          > caller's env_vars (transitively, up the whole chain)
            > real process environ

    This lets shared configuration (e.g. model/param tiers) be set once
    on an orchestrator and inherited by every downstream agent, while an
    individual agent can still override any single key by defining it on
    itself — its value wins for its own run and for anything it calls.

    Restores the prior overlay (often ``None``) on exit. Safe under
    concurrent asyncio tasks: each task gets its own contextvar copy,
    seeded from the context it was spawned in.
    """
    parent = _overlay.get() or {}
    token = _overlay.set({**parent, **overlay})
    try:
        yield
    finally:
        _overlay.reset(token)
