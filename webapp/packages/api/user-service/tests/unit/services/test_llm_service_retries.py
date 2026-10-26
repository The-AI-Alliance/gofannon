"""Unit tests for LLM service retry behavior.

Covers the rate-limit and timeout retry loops in ``llm_service.call_llm``.
Tests are written against the proposed PR that introduces
``MAX_RATE_LIMIT_RETRIES`` and exponential backoff with jitter for
``litellm.RateLimitError``, alongside the existing ``MAX_TIMEOUT_RETRIES``
linear-backoff path for ``litellm.Timeout``.

All tests mock ``asyncio.sleep`` so they run instantly. The randomness in
the jitter calculation is mocked deterministically where the math is
being verified.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import litellm
import pytest

from services import llm_service


pytestmark = pytest.mark.unit


# --- Test doubles ---------------------------------------------------------


class _DummyMessage:
    def __init__(self, content: str):
        self.content = content
        self.tool_calls = None


class _DummyChoice:
    def __init__(self, message):
        self.message = message


class _DummyResponse:
    """Minimal stand-in for a litellm completion response."""

    def __init__(self, content: str, total_cost: float = 0.0):
        self.choices = [_DummyChoice(_DummyMessage(content))]
        self.usage = SimpleNamespace(total_cost=total_cost)


def _make_rate_limit_error(message: str = "429 Too Many Requests") -> litellm.RateLimitError:
    """Construct a RateLimitError without going through HTTP machinery."""
    return litellm.RateLimitError(
        message=message,
        llm_provider="openai",
        model="gpt-4o-mini",
    )


def _make_timeout_error(message: str = "timed out") -> litellm.Timeout:
    """Construct a Timeout without going through HTTP machinery."""
    return litellm.Timeout(
        message=message,
        model="gpt-4o-mini",
        llm_provider="openai",
    )


def _scripted_acompletion(*outcomes):
    """Return an async fake of litellm.acompletion that yields outcomes in order.

    Each ``outcome`` is either an Exception (raised) or a value (returned).
    Tracks how many times it has been called via the ``.calls`` attribute.
    """
    state = {"n": 0}

    async def fake(**_kwargs):
        i = state["n"]
        state["n"] += 1
        if i >= len(outcomes):
            raise AssertionError(
                f"acompletion called {i + 1} times but only {len(outcomes)} outcomes scripted"
            )
        outcome = outcomes[i]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    fake.state = state  # expose for assertions
    return fake


# --- Rate-limit retry: happy path -----------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_retry_eventually_succeeds(monkeypatch):
    """Two RateLimitErrors followed by a success should retry, sleep, and return.

    Verifies:
      - The successful response is returned to the caller.
      - ``asyncio.sleep`` was awaited exactly twice (once per retry).
      - Successive sleep durations are monotonically non-decreasing
        (exponential curve, with jitter).
      - Usage is recorded only once, on the eventual success.
    """
    acompletion = _scripted_acompletion(
        _make_rate_limit_error("first 429"),
        _make_rate_limit_error("second 429"),
        _DummyResponse("hello after retries", total_cost=2.5),
    )

    sleep_calls = []

    async def fake_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    user_service = Mock()

    content, _ = await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        parameters={},
        user_service=user_service,
        user_id="user-1",
    )

    assert content == "hello after retries"
    assert acompletion.state["n"] == 3, "should call acompletion 3 times (2 failures + 1 success)"
    assert len(sleep_calls) == 2, "should sleep once between each retry"
    assert sleep_calls[0] <= sleep_calls[1], "exponential backoff should not decrease"
    user_service.add_usage.assert_called_once_with("user-1", 2.5, basic_info=None)


# --- Rate-limit retry: exhaustion -----------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_retry_exhausts_and_reraises(monkeypatch):
    """Persistent RateLimitError should retry MAX_RATE_LIMIT_RETRIES times then re-raise.

    Verifies:
      - The final raise propagates the original ``RateLimitError`` type.
      - ``observability.log_exception`` was called with
        ``rate_limit_retries_exhausted`` in metadata.
      - No usage is recorded (the call never succeeded).
    """
    # Force MAX_RATE_LIMIT_RETRIES to a small value so the test is fast and obvious.
    monkeypatch.setattr(llm_service, "MAX_RATE_LIMIT_RETRIES", 3)

    final_error = _make_rate_limit_error("persistent 429")
    acompletion = _scripted_acompletion(
        _make_rate_limit_error("429 #1"),
        _make_rate_limit_error("429 #2"),
        _make_rate_limit_error("429 #3"),
        final_error,
    )

    observability = Mock()
    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: observability)

    user_service = Mock()

    with pytest.raises(litellm.RateLimitError):
        await llm_service.call_llm(
            provider="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            parameters={},
            user_service=user_service,
            user_id="user-2",
        )

    assert acompletion.state["n"] == 1 + 3, "should make 1 initial attempt + 3 retries"
    observability.log_exception.assert_called_once()
    metadata = observability.log_exception.call_args.kwargs["metadata"]
    assert metadata.get("rate_limit_retries_exhausted") == 3
    user_service.add_usage.assert_not_called()


# --- Rate-limit retry: math verification ----------------------------------


@pytest.mark.asyncio
async def test_rate_limit_backoff_is_exponential_with_jitter(monkeypatch):
    """Backoff durations should follow 2^n + uniform(0, n+1), clamped to the cap.

    Mocks ``random.uniform`` to return its lower bound (0) so the math is
    deterministic. Expected sleeps: 2^0=1, 2^1=2, 2^2=4, 2^3=8, 2^4=16.
    """
    monkeypatch.setattr(llm_service, "MAX_RATE_LIMIT_RETRIES", 5)
    monkeypatch.setattr(llm_service, "RATE_LIMIT_BACKOFF_CAP_SECONDS", 60)
    monkeypatch.setattr(llm_service.random, "uniform", lambda _lo, _hi: 0)

    acompletion = _scripted_acompletion(
        *[_make_rate_limit_error(f"429 #{i}") for i in range(5)],
        _DummyResponse("eventually", total_cost=0.0),
    )

    sleep_durations = []

    async def fake_sleep(duration):
        sleep_durations.append(duration)

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        parameters={},
        user_service=Mock(),
        user_id="user-3",
    )

    assert sleep_durations == [1.0, 2.0, 4.0, 8.0, 16.0]


@pytest.mark.asyncio
async def test_rate_limit_backoff_clamped_to_cap(monkeypatch):
    """When 2^n exceeds the configured cap, sleep should clamp to the cap."""
    monkeypatch.setattr(llm_service, "MAX_RATE_LIMIT_RETRIES", 8)
    monkeypatch.setattr(llm_service, "RATE_LIMIT_BACKOFF_CAP_SECONDS", 10)
    # Zero jitter so we can read the cap behavior cleanly.
    monkeypatch.setattr(llm_service.random, "uniform", lambda _lo, _hi: 0)

    acompletion = _scripted_acompletion(
        *[_make_rate_limit_error(f"429 #{i}") for i in range(8)],
        _DummyResponse("eventually", total_cost=0.0),
    )

    sleep_durations = []

    async def fake_sleep(duration):
        sleep_durations.append(duration)

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        parameters={},
        user_service=Mock(),
        user_id="user-4",
    )

    # Raw curve would be [1, 2, 4, 8, 16, 32, 64, 128]; cap at 10 means everything
    # from attempt 4 (16) onward is clamped to 10.
    assert sleep_durations == [1.0, 2.0, 4.0, 8.0, 10.0, 10.0, 10.0, 10.0]


# --- Rate-limit retry: disable via env override ---------------------------


@pytest.mark.asyncio
async def test_rate_limit_retries_disabled_by_zero_count(monkeypatch):
    """Setting MAX_RATE_LIMIT_RETRIES=0 should re-raise immediately, no sleep."""
    monkeypatch.setattr(llm_service, "MAX_RATE_LIMIT_RETRIES", 0)

    acompletion = _scripted_acompletion(_make_rate_limit_error("immediate fail"))

    sleep_mock = AsyncMock()
    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", sleep_mock)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    with pytest.raises(litellm.RateLimitError):
        await llm_service.call_llm(
            provider="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            parameters={},
            user_service=Mock(),
            user_id="user-5",
        )

    assert acompletion.state["n"] == 1
    sleep_mock.assert_not_called()


# --- Non-retryable exceptions still bypass the retry loop -----------------


@pytest.mark.asyncio
async def test_non_retryable_exception_does_not_retry(monkeypatch):
    """Plain RuntimeError should fall through to the error classifier and re-raise.

    The retry loop must only catch ``litellm.RateLimitError`` and
    ``litellm.Timeout``. Any other exception class indicates a non-transient
    failure and should not trigger backoff sleeps.
    """
    monkeypatch.setattr(llm_service, "MAX_RATE_LIMIT_RETRIES", 5)
    monkeypatch.setattr(llm_service, "MAX_TIMEOUT_RETRIES", 5)

    acompletion = _scripted_acompletion(RuntimeError("non-retryable boom"))
    sleep_mock = AsyncMock()
    observability = Mock()

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", sleep_mock)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: observability)

    with pytest.raises(RuntimeError, match="non-retryable boom"):
        await llm_service.call_llm(
            provider="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            parameters={},
            user_service=Mock(),
            user_id="user-6",
        )

    assert acompletion.state["n"] == 1, "should fail on the first attempt, no retry"
    sleep_mock.assert_not_called()
    observability.log_exception.assert_called_once()


# --- Timeout retry path: regression guard ---------------------------------


@pytest.mark.asyncio
async def test_timeout_retry_still_works(monkeypatch):
    """The new RateLimit retry loop must not regress the existing Timeout path.

    With MAX_TIMEOUT_RETRIES set, a single Timeout followed by a success
    should still resolve to a successful call.
    """
    monkeypatch.setattr(llm_service, "MAX_TIMEOUT_RETRIES", 2)
    monkeypatch.setattr(llm_service, "MAX_RATE_LIMIT_RETRIES", 0)

    acompletion = _scripted_acompletion(
        _make_timeout_error("first timeout"),
        _DummyResponse("recovered", total_cost=1.0),
    )

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    content, _ = await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        parameters={},
        user_service=Mock(),
        user_id="user-7",
    )

    assert content == "recovered"
    assert acompletion.state["n"] == 2


# --- Mixed failure modes: timeout and rate-limit counters are independent --


@pytest.mark.asyncio
async def test_timeout_and_rate_limit_counters_independent(monkeypatch):
    """Timeouts and rate-limit errors should each have their own retry budget.

    With both budgets at 2, a sequence of 2 Timeouts + 2 RateLimits + success
    should complete successfully — neither counter eats from the other's budget.
    Total of 4 failures + 1 success across 5 acompletion calls.
    """
    monkeypatch.setattr(llm_service, "MAX_TIMEOUT_RETRIES", 2)
    monkeypatch.setattr(llm_service, "MAX_RATE_LIMIT_RETRIES", 2)
    monkeypatch.setattr(llm_service.random, "uniform", lambda _lo, _hi: 0)

    acompletion = _scripted_acompletion(
        _make_timeout_error("timeout #1"),
        _make_timeout_error("timeout #2"),
        _make_rate_limit_error("429 #1"),
        _make_rate_limit_error("429 #2"),
        _DummyResponse("finally", total_cost=0.0),
    )

    monkeypatch.setattr(llm_service.litellm, "acompletion", acompletion)
    monkeypatch.setattr(llm_service.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    content, _ = await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        parameters={},
        user_service=Mock(),
        user_id="user-8",
    )

    assert content == "finally"
    assert acompletion.state["n"] == 5