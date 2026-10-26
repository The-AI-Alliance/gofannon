"""Temperature, reconciled in llm_service against what each model accepts.

This used to live in every ASVS agent's _make_tier, keyed on provider NAME
({"bedrock", "anthropic"}). Two of those providers no longer
exist, and "anthropic-1p"-1p", was never listed. The rule
that selfhosted models loop at temperature 0.0 with thinking on existed only as a
comment. These tests pin all three flags on the request actually sent.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from services import llm_service

pytestmark = pytest.mark.unit

SELFHOSTED_MODELS = ["gemma4-26b", "qwen3.8-27b", "qwen3-8b"]


class _Resp:
    def __init__(self):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))]
        self.usage = SimpleNamespace(total_cost=0.0)


@pytest.fixture
def captured(monkeypatch):
    seen = {}

    async def fake_acompletion(**kwargs):
        seen.clear()
        seen.update(kwargs)
        if kwargs.get("stream"):
            async def _chunks():
                yield SimpleNamespace(choices=[])
            return _chunks()
        return _Resp()

    monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
    return seen


@pytest.fixture
def selfhosted_env(monkeypatch):
    monkeypatch.setenv("SELFHOSTED_API_BASE", "https://llm.example.com/v1")
    monkeypatch.setenv("SELFHOSTED_API_KEY", "sk-test")


@pytest.fixture
def wif(monkeypatch):
    async def fake_token(**_kw):
        return "tok"
    import services.anthropic_wif as w
    monkeypatch.setattr(w, "get_anthropic_1p_bearer_token", fake_token)


@pytest.fixture(autouse=True)
def _reset_warned():
    llm_service._NONZERO_TEMP_WARNED.clear()
    yield
    llm_service._NONZERO_TEMP_WARNED.clear()


async def _call(provider, model, **params):
    return await llm_service.call_llm(
        provider=provider, model=model,
        messages=[{"role": "user", "content": "hi"}],
        parameters=params, user_service=Mock(), user_id="u",
    )


async def _stream(provider, model, **params):
    async for _ in llm_service.stream_llm(
        provider=provider, model=model,
        messages=[{"role": "user", "content": "hi"}],
        parameters=params, user_service=Mock(), user_id="u",
    ):
        pass


# ---------------------------------------------------------------------------
# The helper
# ---------------------------------------------------------------------------


class TestReconcileTemperature:
    R = staticmethod(llm_service._reconcile_temperature)

    def test_absent_temperature_is_untouched_by_every_flag(self):
        for flag in ("rejects_temperature", "rejects_temperature_with_thinking",
                     "requires_nonzero_temperature_with_thinking"):
            kw = {}
            self.R(kw, {flag: True}, thinking_active=True)
            assert kw == {}

    def test_rejects_temperature_drops_even_without_thinking(self):
        kw = {"temperature": 0.3}
        self.R(kw, {"rejects_temperature": True}, thinking_active=False)
        assert "temperature" not in kw

    @pytest.mark.parametrize("t", [0.0, 0.2, 0.7, 2.0])
    def test_rejects_with_thinking_drops_anything_but_one(self, t):
        kw = {"temperature": t}
        self.R(kw, {"rejects_temperature_with_thinking": True}, thinking_active=True)
        assert "temperature" not in kw

    def test_rejects_with_thinking_keeps_one(self):
        """Anthropic documents temperature as locked to 1.0 under thinking;
        1.0 itself is accepted. The agents kept it too."""
        kw = {"temperature": 1.0}
        self.R(kw, {"rejects_temperature_with_thinking": True}, thinking_active=True)
        assert kw == {"temperature": 1.0}

    def test_rejects_with_thinking_keeps_temperature_when_thinking_off(self):
        kw = {"temperature": 0.2}
        self.R(kw, {"rejects_temperature_with_thinking": True}, thinking_active=False)
        assert kw == {"temperature": 0.2}

    @pytest.mark.parametrize("zero", [0, 0.0, "0", "0.0"])
    def test_requires_nonzero_drops_explicit_zero(self, zero):
        """Dropped, not replaced: vLLM then applies the model's own
        generation_config (the vendor-tuned value), else its default of 1.0."""
        kw = {"temperature": zero}
        self.R(kw, {"requires_nonzero_temperature_with_thinking": True},
               thinking_active=True, model_label="selfhosted/x")
        assert "temperature" not in kw

    def test_requires_nonzero_keeps_nonzero(self):
        kw = {"temperature": 0.6}
        self.R(kw, {"requires_nonzero_temperature_with_thinking": True}, thinking_active=True)
        assert kw == {"temperature": 0.6}

    def test_requires_nonzero_keeps_zero_when_thinking_off(self):
        """0.0 is the right value for deterministic classification with
        thinking off -- selfhosted's config default for exactly that reason."""
        kw = {"temperature": 0.0}
        self.R(kw, {"requires_nonzero_temperature_with_thinking": True}, thinking_active=False)
        assert kw == {"temperature": 0.0}

    def test_requires_nonzero_warns_once_per_model(self, capsys):
        cfg = {"requires_nonzero_temperature_with_thinking": True}
        for _ in range(3):
            self.R({"temperature": 0.0}, cfg, thinking_active=True, model_label="selfhosted/a")
        self.R({"temperature": 0.0}, cfg, thinking_active=True, model_label="selfhosted/b")
        out = capsys.readouterr().out
        assert out.count("selfhosted/a: temperature=0.0") == 1
        assert out.count("selfhosted/b: temperature=0.0") == 1

    def test_no_flags_is_a_no_op(self):
        kw = {"temperature": 0.0}
        self.R(kw, {}, thinking_active=True)
        assert kw == {"temperature": 0.0}


# ---------------------------------------------------------------------------
# On the request actually sent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bedrock_claude_with_thinking_drops_temperature(captured):
    await _call("bedrock", "us.anthropic.claude-opus-4-8", reasoning_effort="high", temperature=0.5)
    assert "temperature" not in captured
    assert captured.get("thinking") == {"type": "adaptive"}


@pytest.mark.asyncio
async def test_bedrock_claude_legacy_thinking_drops_temperature(captured):
    await _call("bedrock", "us.anthropic.claude-sonnet-4-6", reasoning_effort="high", temperature=0.5)
    assert "temperature" not in captured
    assert captured.get("reasoning_effort") == "high"


@pytest.mark.asyncio
async def test_bedrock_claude_without_thinking_keeps_temperature(captured):
    await _call("bedrock", "us.anthropic.claude-opus-4-8", reasoning_effort="disable", temperature=0.5)
    assert captured.get("temperature") == 0.5


@pytest.mark.asyncio
async def test_bedrock_claude_thinking_keeps_temperature_one(captured):
    await _call("bedrock", "us.anthropic.claude-opus-4-8", reasoning_effort="high", temperature=1.0)
    assert captured.get("temperature") == 1.0


@pytest.mark.asyncio
@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
async def test_selfhosted_thinking_with_zero_drops_it(captured, selfhosted_env, model):
    await _call("selfhosted", model, reasoning_effort="enable", temperature=0.0)
    assert "temperature" not in captured


@pytest.mark.asyncio
@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
async def test_selfhosted_thinking_keeps_nonzero(captured, selfhosted_env, model):
    await _call("selfhosted", model, reasoning_effort="enable", temperature=0.6)
    assert captured.get("temperature") == 0.6


@pytest.mark.asyncio
@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
async def test_selfhosted_no_thinking_keeps_zero(captured, selfhosted_env, model):
    await _call("selfhosted", model, reasoning_effort="disable", temperature=0.0)
    assert captured.get("temperature") == 0.0


@pytest.mark.asyncio
async def test_selfhosted_graded_level_counts_as_thinking(captured, selfhosted_env):
    await _call("selfhosted", "qwen3.8-27b", reasoning_effort="medium", temperature=0.0)
    assert "temperature" not in captured


@pytest.mark.asyncio
async def test_bedrock_non_claude_is_not_flagged(captured):
    """Deliberate narrowing. The agents drop temperature for EVERY bedrock
    model under thinking because they match the provider name; the Anthropic
    constraint is only known for Claude. Nothing changes while the agents'
    copy exists -- revisit when it is deleted (harmonization 5d)."""
    await _call("bedrock", "us.deepseek.r1-v1:0", reasoning_effort="high", temperature=0.5)
    assert captured.get("temperature") == 0.5


@pytest.mark.asyncio
async def test_stream_selfhosted_thinking_with_zero_drops_it(captured, selfhosted_env):
    await _stream("selfhosted", "qwen3-8b", reasoning_effort="enable", temperature=0.0)
    assert "temperature" not in captured


@pytest.mark.asyncio
async def test_stream_bedrock_claude_keeps_temperature(captured):
    """stream_llm has never sent reasoning to non-selfhosted models, so thinking
    is off there and temperature is legitimately kept."""
    await _stream("bedrock", "us.anthropic.claude-opus-4-8", reasoning_effort="high", temperature=0.5)
    assert captured.get("temperature") == 0.5
