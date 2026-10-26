"""What gofannon actually sends to selfhosted, for reasoning control.

These assert on the kwargs handed to litellm rather than on any response,
because every bug this file guards against was a parameter going to the
wrong place -- or nowhere -- while the call still succeeded.

Three things went wrong before these existed:

  1. reasoning_effort was not declared in selfhosted's _params(), so the gate's
     fallback of 'disable' fired on every call and no tier could turn
     reasoning on.
  2. stream_llm popped reasoning_effort and discarded it with the note "not
     typically used in streaming". For Bedrock that was harmless; for selfhosted
     it left each model at its own default, and two of three think by
     default -- on qwen3-8b that means a stream carrying zero content.
  3. An attempt to set a per-model default in selfhosted's catalog looked like it
     worked. LiteLLM accepts extra keys in litellm_params at /model/new with
     a 200 and silently drops them, so there is no server-side default to
     defer to and the caller must decide every time.

None of the three raised. That is why these assert on the request.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from config.provider_config import PROVIDER_CONFIG
from services import llm_service

pytestmark = pytest.mark.unit

SELFHOSTED_MODELS = ["gemma4-26b", "qwen3.8-27b", "qwen3-8b"]


class _Msg:
    def __init__(self, content="ok"):
        self.content = content
        self.tool_calls = None


class _Resp:
    def __init__(self, content="ok"):
        self.choices = [SimpleNamespace(message=_Msg(content))]
        self.usage = SimpleNamespace(total_cost=0.0)


@pytest.fixture
def selfhosted_env(monkeypatch):
    """The two env vars the selfhosted provider refuses to run without."""
    monkeypatch.setenv("SELFHOSTED_API_BASE", "https://llm.example.com/v1")
    monkeypatch.setenv("SELFHOSTED_API_KEY", "sk-test")
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())


@pytest.fixture
def captured(monkeypatch):
    """Capture the kwargs litellm is called with, without calling it."""
    seen = {}

    async def fake_acompletion(**kwargs):
        seen.clear()
        seen.update(kwargs)
        return _Resp()

    monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
    return seen


def _thinking(kwargs):
    """enable_thinking as sent, or None if the key is absent entirely.

    Absent and False are different outcomes and the distinction matters: the
    first leaves the model at its own default, which on two of the three
    models means reasoning stays on.
    """
    extra = kwargs.get("extra_body") or {}
    ctk = extra.get("chat_template_kwargs") or {}
    return ctk.get("enable_thinking")


# ---------------------------------------------------------------------------
# The catalog declares the parameter at all
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
def test_reasoning_effort_is_declared(model):
    """Without this key in the params dict, the gate's fallback of 'disable'
    fires on every call and no tier can ever turn reasoning on."""
    cfg = PROVIDER_CONFIG["selfhosted"]["models"][model]
    params = cfg["parameters"]
    assert "reasoning_effort" in params, f"{model}: reasoning_effort must be declared or tiers cannot choose"
    spec = params["reasoning_effort"]
    assert spec["default"] == "disable", (
        f"{model}: default must be 'disable'. There is no server-side "
        f"default to defer to -- LiteLLM drops extra litellm_params keys at "
        f"/model/new -- and this model's own default leaves reasoning on."
    )
    # Binary UNLESS the model grades its reasoning, in which case those
    # levels are offered too. Qwen3.8-27B does, and the difference is large:
    # xhigh -- its own default -- costs 1.9x the wall time of medium to
    # produce HALF the content, measured on a 38k audit prompt.
    levels = cfg.get("thinking_levels") or []
    assert set(spec["choices"]) == {"disable", "enable", *levels}, (
        f"{model}: choices must be disable/enable plus any declared thinking_levels {levels}, got {spec['choices']}"
    )


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
def test_thinking_levels_are_declared_only_where_measured(model):
    """Graded reasoning is a per-model fact, not a family one.

    qwen3.8-27b grades it: low/medium/xhigh, and the default is xhigh. gemma
    was measured at all three levels on the same 38k prompt and ignores them
    -- 28-32s and ~2,500-3,000c of content at every setting. Declaring levels
    it does not honor would put choices in the UI that do nothing.
    """
    cfg = PROVIDER_CONFIG["selfhosted"]["models"][model]
    levels = cfg.get("thinking_levels")
    if model == "qwen3.8-27b":
        assert levels == ["low", "medium", "xhigh"], (
            "qwen3.8-27b grades its reasoning inside chat_template_kwargs; "
            "without these declared, llm_service cannot send a level and "
            "every call runs at the model's xhigh default"
        )
    else:
        assert not levels, (
            f"{model}: no measured graded behavior. Declaring levels here would offer settings that do nothing."
        )


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
def test_supports_thinking_is_true(model):
    """The gate requires it. False would mean enable_thinking is never sent
    and the model runs at its own default."""
    cfg = PROVIDER_CONFIG["selfhosted"]["models"][model]
    assert cfg.get("supports_thinking") is True


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
def test_supports_effort_is_false(model):
    """True would send OpenAI's reasoning_effort scale to vLLM. qwen3.8-27b
    accepts only xhigh/medium/low and 400s on 'high', which is what several
    clients send by default; the other two reject the parameter outright."""
    cfg = PROVIDER_CONFIG["selfhosted"]["models"][model]
    assert cfg.get("supports_effort") is False


# ---------------------------------------------------------------------------
# call_llm
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
@pytest.mark.asyncio
async def test_call_llm_disable_sends_false(model, selfhosted_env, captured):
    await llm_service.call_llm(
        provider="selfhosted",
        model=model,
        messages=[{"role": "user", "content": "hi"}],
        parameters={"reasoning_effort": "disable"},
        user_service=Mock(),
        user_id="u",
    )
    assert _thinking(captured) is False


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
@pytest.mark.asyncio
async def test_call_llm_enable_sends_true(model, selfhosted_env, captured):
    await llm_service.call_llm(
        provider="selfhosted",
        model=model,
        messages=[{"role": "user", "content": "hi"}],
        parameters={"reasoning_effort": "enable"},
        user_service=Mock(),
        user_id="u",
    )
    assert _thinking(captured) is True


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
@pytest.mark.asyncio
async def test_call_llm_never_sends_reasoning_effort(model, selfhosted_env, captured):
    """Our reasoning_effort is an internal intent, not a wire parameter. It
    must be translated and dropped, never forwarded -- vLLM accepts it on one
    of these three models and rejects it on the others."""
    for value in ("disable", "enable"):
        await llm_service.call_llm(
            provider="selfhosted",
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            parameters={"reasoning_effort": value},
            user_service=Mock(),
            user_id="u",
        )
        assert "reasoning_effort" not in captured


# ---------------------------------------------------------------------------
# stream_llm -- the path agents actually use
# ---------------------------------------------------------------------------


async def _drain(gen):
    async for _ in gen:
        pass


@pytest.fixture
def captured_stream(monkeypatch):
    seen = {}

    async def fake_acompletion(**kwargs):
        seen.clear()
        seen.update(kwargs)

        async def _chunks():
            yield SimpleNamespace(choices=[])

        return _chunks()

    monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
    return seen


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
@pytest.mark.asyncio
async def test_stream_disable_sends_false(model, selfhosted_env, captured_stream):
    """Regression: this path used to pop reasoning_effort and throw it away,
    so nothing was sent and every model ran at its own default. On qwen3-8b
    that produced a stream of 400 chunks carrying no content at all."""
    await _drain(
        llm_service.stream_llm(
            provider="selfhosted",
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            parameters={"reasoning_effort": "disable"},
            user_service=Mock(),
            user_id="u",
        )
    )
    assert _thinking(captured_stream) is False


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
@pytest.mark.asyncio
async def test_stream_enable_sends_true(model, selfhosted_env, captured_stream):
    await _drain(
        llm_service.stream_llm(
            provider="selfhosted",
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            parameters={"reasoning_effort": "enable"},
            user_service=Mock(),
            user_id="u",
        )
    )
    assert _thinking(captured_stream) is True


@pytest.mark.asyncio
async def test_stream_never_sends_reasoning_effort(selfhosted_env, captured_stream):
    await _drain(
        llm_service.stream_llm(
            provider="selfhosted",
            model="qwen3-8b",
            messages=[{"role": "user", "content": "hi"}],
            parameters={"reasoning_effort": "enable"},
            user_service=Mock(),
            user_id="u",
        )
    )
    assert "reasoning_effort" not in captured_stream


@pytest.mark.asyncio
async def test_stream_preserves_other_extra_body(selfhosted_env, captured_stream):
    """The gate merges into extra_body rather than replacing it, so a tier can
    pass vLLM sampling parameters alongside."""
    await _drain(
        llm_service.stream_llm(
            provider="selfhosted",
            model="qwen3-8b",
            messages=[{"role": "user", "content": "hi"}],
            parameters={
                "reasoning_effort": "disable",
                "extra_body": {"top_k": 20, "chat_template_kwargs": {"other": 1}},
            },
            user_service=Mock(),
            user_id="u",
        )
    )
    extra = captured_stream["extra_body"]
    assert extra["top_k"] == 20
    assert extra["chat_template_kwargs"]["other"] == 1
    assert extra["chat_template_kwargs"]["enable_thinking"] is False


# ---------------------------------------------------------------------------
# Bedrock must be untouched by any of this
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bedrock_never_gets_extra_body(monkeypatch, captured):
    """Gating on supports_thinking alone attached extra_body to Sonnet and
    failed every architecture classification batch on 2026-07-23. Converse
    rejects unknown top-level fields with 400 "extra_body: Extra inputs are
    not permitted". api_base_env_var is the real discriminator, and only the
    selfhosted provider sets it."""
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    bedrock_models = list(PROVIDER_CONFIG.get("bedrock", {}).get("models", {}))
    if not bedrock_models:
        pytest.skip("no bedrock models configured")

    model = bedrock_models[0]
    await llm_service.call_llm(
        provider="bedrock",
        model=model,
        messages=[{"role": "user", "content": "hi"}],
        parameters={"reasoning_effort": "disable"},
        user_service=Mock(),
        user_id="u",
    )
    assert "extra_body" not in captured


def test_only_selfhosted_declares_api_base_env_var():
    """The gate's discriminator. If another provider ever sets this, it will
    start receiving chat_template_kwargs -- which is a vLLM concept and will
    be rejected by anything else."""
    with_base = [p for p, cfg in PROVIDER_CONFIG.items() if cfg.get("api_base_env_var")]
    assert with_base == ["selfhosted"], (
        f"providers declaring api_base_env_var: {with_base}. The reasoning gate assumes selfhosted is the only one."
    )


# ---------------------------------------------------------------------------
# Context arithmetic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model,served",
    [
        ("gemma4-26b", 131072),
        ("qwen3.8-27b", 131072),
        ("qwen3-8b", 40960),
    ],
)
def test_context_plus_max_tokens_fits_the_served_window(model, served):
    """vLLM rejects a request whose input + max_tokens exceeds
    --max-model-len. context_window here is the INPUT budget, so the two must
    sum under the served window with margin to spare."""
    cfg = PROVIDER_CONFIG["selfhosted"]["models"][model]
    ceiling = cfg["parameters"]["max_tokens"]["max"]
    total = cfg["context_window"] + ceiling
    assert total <= served, (
        f"{model}: context_window {cfg['context_window']} + max_tokens "
        f"ceiling {ceiling} = {total}, over the served window of {served}"
    )


@pytest.mark.parametrize("model", SELFHOSTED_MODELS)
def test_max_tokens_default_is_under_its_ceiling(model):
    spec = PROVIDER_CONFIG["selfhosted"]["models"][model]["parameters"]["max_tokens"]
    assert spec["default"] <= spec["max"]


def test_qwen3_8b_default_budget_leaves_room_for_reasoning():
    """This model produced 3,400+ characters of reasoning on 'what is
    17 x 23'. Thinking consumes the same budget as the response, so a default
    sized for the answer alone returns content=None whenever a tier enables
    reasoning."""
    spec = PROVIDER_CONFIG["selfhosted"]["models"]["qwen3-8b"]["parameters"]["max_tokens"]
    assert spec["default"] >= 2048
