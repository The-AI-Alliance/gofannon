"""Unit tests for the Anthropic 1P WIF token helper.

Focus is the concurrency behavior. gofannon dispatches LLM calls in
parallel (ASVS_MEDIUM_CONCURRENCY is 5, HEAVY 4, filter 4), so the token
helper is entered concurrently on every cold start and after every
invalidation. Without serialisation each of those coroutines performs its
own STS mint and its own Anthropic exchange.

Two things are being protected:

  1. Cost and noise. N-1 redundant exchanges per stampede, each producing a
     CloudTrail entry and a row in Anthropic's authentication event feed.

  2. A latent JTI hazard. Anthropic's issuer enforces single-use assertions,
     so presenting the same JWT twice is rejected. Today every path mints a
     fresh JWT before exchanging, so N misses produce N distinct jti values
     and nothing breaks -- but caching the JWT would be an obvious-looking
     optimisation that passes every serial test and fails intermittently
     under load. test_every_exchange_uses_a_distinct_jwt pins that
     invariant so the refactor fails loudly instead.

No network: STS and the exchange are patched throughout.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from services import anthropic_wif


pytestmark = pytest.mark.unit


_RULE = "fdrl_test"
_ENV = {
    "ANTHROPIC_FEDERATION_RULE_ID": _RULE,
    "ANTHROPIC_ORGANIZATION_ID": "org_test",
    "ANTHROPIC_SERVICE_ACCOUNT_ID": "svac_test",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Federation config present, static key absent, cache empty."""
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_WORKSPACE_ID", raising=False)
    anthropic_wif.clear_token_cache()
    yield
    anthropic_wif.clear_token_cache()


class _Recorder:
    """Stands in for STS + the Anthropic exchange, counting both.

    Each mint returns a distinct JWT and each exchange a distinct access
    token, so a test can tell reuse from re-minting.
    """

    def __init__(self, latency=0.02, expires_in=3453):
        self.latency = latency
        self.expires_in = expires_in
        self.jwts = []
        self.exchanged_jwts = []
        self.tokens = []

    def mint(self):
        # Blocking sleep on purpose: the real _mint_sts_web_identity_token is
        # sync boto3 and is dispatched via asyncio.to_thread, so this mirrors
        # production. A bare asyncio.sleep here would not exercise that path.
        time.sleep(self.latency)
        jwt = f"jwt-{len(self.jwts) + 1}"
        self.jwts.append(jwt)
        return jwt

    def exchange(self, jwt, cfg):
        time.sleep(self.latency)
        self.exchanged_jwts.append(jwt)
        token = f"sk-ant-oat01-{len(self.tokens) + 1}"
        self.tokens.append(token)
        return {"access_token": token, "expires_in": self.expires_in}

    def install(self, monkeypatch):
        monkeypatch.setattr(
            anthropic_wif, "_mint_sts_web_identity_token", self.mint
        )
        monkeypatch.setattr(
            anthropic_wif, "_exchange_jwt_for_access_token", self.exchange
        )
        return self


@pytest.fixture
def recorder(monkeypatch):
    return _Recorder().install(monkeypatch)


# --------------------------------------------------------------- basics


@pytest.mark.asyncio
async def test_first_call_mints_and_caches(recorder):
    token = await anthropic_wif.get_anthropic_1p_bearer_token()
    assert token == "sk-ant-oat01-1"
    assert len(recorder.tokens) == 1


@pytest.mark.asyncio
async def test_second_call_reuses_cache(recorder):
    first = await anthropic_wif.get_anthropic_1p_bearer_token()
    second = await anthropic_wif.get_anthropic_1p_bearer_token()
    assert first == second
    assert len(recorder.tokens) == 1, "a warm cache must not re-exchange"


@pytest.mark.asyncio
async def test_invalidate_forces_a_fresh_token(recorder):
    first = await anthropic_wif.get_anthropic_1p_bearer_token()
    anthropic_wif.invalidate_anthropic_1p_token()
    second = await anthropic_wif.get_anthropic_1p_bearer_token()
    assert second != first
    assert len(recorder.tokens) == 2


@pytest.mark.asyncio
async def test_missing_config_raises(monkeypatch, recorder):
    monkeypatch.delenv("ANTHROPIC_FEDERATION_RULE_ID")
    with pytest.raises(anthropic_wif.AnthropicWifConfigError) as exc:
        await anthropic_wif.get_anthropic_1p_bearer_token()
    assert "ANTHROPIC_FEDERATION_RULE_ID" in str(exc.value)


@pytest.mark.asyncio
async def test_static_api_key_refuses_to_run(monkeypatch, recorder):
    """litellm prefers a static key over an injected one, so a stray
    ANTHROPIC_API_KEY would silently bypass federation entirely."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-static")
    with pytest.raises(anthropic_wif.AnthropicWifConfigError) as exc:
        await anthropic_wif.get_anthropic_1p_bearer_token()
    assert "ANTHROPIC_API_KEY" in str(exc.value)
    assert not recorder.tokens, "must refuse before doing any work"


# ----------------------------------------------------------- concurrency


@pytest.mark.asyncio
async def test_concurrent_cold_start_performs_one_exchange(recorder):
    """The stampede this whole change exists to prevent.

    Ten coroutines enter with an empty cache. Without the lock each would
    mint and exchange, because the ~40ms of simulated latency spans the
    entire miss-to-write window.
    """
    tokens = await asyncio.gather(
        *[anthropic_wif.get_anthropic_1p_bearer_token(1800) for _ in range(10)]
    )
    assert len(recorder.tokens) == 1, (
        f"expected 1 exchange for 10 concurrent callers, got "
        f"{len(recorder.tokens)} -- the lock is not holding"
    )
    assert len(set(tokens)) == 1, "all callers must receive the same token"


@pytest.mark.asyncio
async def test_concurrent_warm_cache_performs_no_exchange(recorder):
    await anthropic_wif.get_anthropic_1p_bearer_token(1800)
    recorder.tokens.clear()

    tokens = await asyncio.gather(
        *[anthropic_wif.get_anthropic_1p_bearer_token(1800) for _ in range(10)]
    )
    assert not recorder.tokens, "a warm cache must not re-exchange"
    assert len(set(tokens)) == 1


@pytest.mark.asyncio
async def test_concurrent_after_invalidate_performs_one_exchange(recorder):
    """The retry path. If several in-flight calls all 401 and all
    invalidate, the re-mint must still collapse to one exchange."""
    first = await anthropic_wif.get_anthropic_1p_bearer_token(1800)
    anthropic_wif.invalidate_anthropic_1p_token()

    tokens = await asyncio.gather(
        *[anthropic_wif.get_anthropic_1p_bearer_token(1800) for _ in range(10)]
    )
    assert len(recorder.tokens) == 2, "one initial + one after invalidation"
    assert len(set(tokens)) == 1
    assert tokens[0] != first, "the token must actually have rotated"


@pytest.mark.asyncio
async def test_every_exchange_uses_a_distinct_jwt(recorder):
    """JTI replay protection: an assertion may be presented exactly once.

    This is the invariant a 'cache the JWT too, it lasts 900s' change would
    break -- silently, and only under concurrency. If this fails, the STS
    JWT is being reused across exchanges and Anthropic will start rejecting
    them.
    """
    for _ in range(3):
        await anthropic_wif.get_anthropic_1p_bearer_token(1800)
        anthropic_wif.invalidate_anthropic_1p_token()

    assert len(recorder.exchanged_jwts) == 3
    assert len(set(recorder.exchanged_jwts)) == 3, (
        "the same JWT was exchanged more than once -- Anthropic's issuer "
        "enforces single-use assertions and would reject the replay"
    )


@pytest.mark.asyncio
async def test_fast_path_does_not_hold_the_lock(recorder):
    """A warm cache must not serialise callers.

    If the fast path took the lock, concurrent dispatch would queue behind a
    mutex it does not need. Ten warm reads should complete in far less than
    ten times one exchange's latency.
    """
    await anthropic_wif.get_anthropic_1p_bearer_token(1800)

    started = time.monotonic()
    await asyncio.gather(
        *[anthropic_wif.get_anthropic_1p_bearer_token(1800) for _ in range(10)]
    )
    elapsed = time.monotonic() - started
    assert elapsed < 0.05, f"warm reads took {elapsed:.3f}s; are they serialised?"


# --------------------------------------------------------- cache sizing


@pytest.mark.asyncio
async def test_long_min_validity_still_hits_the_cache(monkeypatch):
    """Regression: a requirement longer than the token's own lifetime must
    not defeat the cache.

    The requirement is capped at what a fresh token could provide. Without
    that cap, asking for 1800s against a 600s token makes every lookup miss,
    so the cache appears present and does nothing.
    """
    rec = _Recorder(expires_in=600).install(monkeypatch)

    await anthropic_wif.get_anthropic_1p_bearer_token(1800)
    await anthropic_wif.get_anthropic_1p_bearer_token(1800)
    await anthropic_wif.get_anthropic_1p_bearer_token(1800)

    assert len(rec.tokens) == 1, (
        "min_validity_seconds above the token lifetime defeated the cache"
    )


@pytest.mark.asyncio
async def test_expired_token_is_re_minted(monkeypatch, recorder):
    await anthropic_wif.get_anthropic_1p_bearer_token()

    entry = anthropic_wif._ANTHROPIC_1P_TOKEN_CACHE[_RULE]
    entry["expires_at"] = time.time() - 1

    await anthropic_wif.get_anthropic_1p_bearer_token()
    assert len(recorder.tokens) == 2


@pytest.mark.asyncio
async def test_token_inside_refresh_margin_is_re_minted(monkeypatch, recorder):
    """Still valid, but not for long enough -- must refresh early rather
    than hand out a token that dies mid-request."""
    await anthropic_wif.get_anthropic_1p_bearer_token()

    entry = anthropic_wif._ANTHROPIC_1P_TOKEN_CACHE[_RULE]
    entry["expires_at"] = time.time() + (
        anthropic_wif._TOKEN_REFRESH_MARGIN_SECONDS - 5
    )

    await anthropic_wif.get_anthropic_1p_bearer_token()
    assert len(recorder.tokens) == 2


@pytest.mark.asyncio
async def test_workspace_id_included_only_when_set(monkeypatch):
    """workspace_id is required when the federation rule covers more than
    one workspace, and must be omitted otherwise."""
    seen = {}

    def capture(jwt, cfg):
        seen.update(cfg)
        return {"access_token": "sk-ant-oat01-x", "expires_in": 3453}

    monkeypatch.setattr(
        anthropic_wif, "_mint_sts_web_identity_token", lambda: "jwt-1"
    )
    monkeypatch.setattr(anthropic_wif, "_exchange_jwt_for_access_token", capture)

    await anthropic_wif.get_anthropic_1p_bearer_token()
    assert seen["workspace_id"] is None

    anthropic_wif.clear_token_cache()
    monkeypatch.setenv("ANTHROPIC_WORKSPACE_ID", "wrkspc_test")
    await anthropic_wif.get_anthropic_1p_bearer_token()
    assert seen["workspace_id"] == "wrkspc_test"


# ------------------------------------------------------ event loop binding


def test_lock_survives_a_second_event_loop(monkeypatch):
    """Sequential (uncontended) use across two event loops.

    NOTE: this case passes even with a module-level lock. Python 3.10+
    rebinds an UNCONTENDED asyncio.Lock to whichever loop next uses it, so a
    single call per loop never trips the binding check. Kept because it
    documents that the sequential path is fine and pins it against a future
    change that would break it -- but the test that actually catches the
    module-level-lock bug is test_concurrent_stampede_on_a_fresh_loop below,
    which leaves a waiter on the lock.

    Deliberately NOT an async test -- it must drive two separate loops
    itself, which a single-loop async fixture cannot do.
    """
    rec = _Recorder().install(monkeypatch)
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    anthropic_wif.clear_token_cache()
    anthropic_wif._clear_token_locks()

    async def once():
        return await anthropic_wif.get_anthropic_1p_bearer_token(60)

    first = asyncio.run(once())          # loop A, binds a lock
    anthropic_wif.clear_token_cache()    # force the lock path again
    second = asyncio.run(once())         # loop B -- used to raise here

    assert first and second
    assert len(rec.tokens) == 2
    anthropic_wif._clear_token_locks()


def test_concurrent_stampede_on_a_fresh_loop(monkeypatch):
    """Regression: a module-level asyncio.Lock breaks on a second loop.

    THIS is the test that catches it. An asyncio.Lock binds to the first
    event loop that awaits it; Python rebinds it silently while it is
    uncontended, but once a waiter has queued on it the lock keeps that
    loop and every acquire from another raises
    "RuntimeError: ... is bound to a different event loop".

    A concurrent burst guarantees contention, so running one on loop A and
    another on loop B reproduces it. Verified 2026-08-06: with a
    module-level lock this raises; with the per-loop lock it passes.

    A process gets more than one loop whenever uvicorn --reload restarts, a
    test suite calls asyncio.run() per test, or a worker thread runs its own
    loop. The failure is total -- every 1P token acquisition raises, so
    every call to the provider fails -- and it appears after a reload rather
    than at startup, which makes it look like an Anthropic outage.
    """
    rec = _Recorder().install(monkeypatch)
    for k, v in _ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    anthropic_wif.clear_token_cache()
    anthropic_wif._clear_token_locks()

    async def burst():
        return await asyncio.gather(
            *[anthropic_wif.get_anthropic_1p_bearer_token(1800) for _ in range(8)]
        )

    asyncio.run(burst())
    anthropic_wif.clear_token_cache()
    rec.tokens.clear()

    tokens = asyncio.run(burst())        # second loop
    assert len(rec.tokens) == 1, "stampede protection lost on a new loop"
    assert len(set(tokens)) == 1
    anthropic_wif._clear_token_locks()