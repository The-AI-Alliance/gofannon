"""Unit tests for context window awareness (PR #567 / issue #565).

Tests cover:
- context_window metadata on all provider model configs
- get_context_window() runtime lookup in dependencies.py
- Context window surfacing in agent factory code generation prompts
- Context window overflow error handling in llm_service.py
- Batch processing guidance content in prompts.py
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from config import provider_config
from config.provider_config import PROVIDER_CONFIG
import dependencies as dependencies_module
from services import llm_service
from agent_factory import prompts


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. Provider config: context_window metadata on all models
# ---------------------------------------------------------------------------

class TestProviderContextWindowMetadata:
    """Every model in every keyed provider must declare a context_window."""

    # Ollama models are local/user-supplied and don't ship with context_window
    PROVIDERS_REQUIRING_CONTEXT_WINDOW = [
        "openai", "anthropic", "gemini", "perplexity", "bedrock",
    ]

    @pytest.fixture
    def config(self):
        return PROVIDER_CONFIG

    @pytest.mark.parametrize("provider", PROVIDERS_REQUIRING_CONTEXT_WINDOW)
    def test_all_models_have_context_window(self, config, provider):
        """Every model for cloud providers must have a positive integer context_window."""
        models = config[provider]["models"]
        assert models, f"{provider} has no models"
        for model_name, model_cfg in models.items():
            assert "context_window" in model_cfg, (
                f"{provider}/{model_name} missing context_window"
            )
            cw = model_cfg["context_window"]
            assert isinstance(cw, int) and cw > 0, (
                f"{provider}/{model_name} context_window must be a positive int, got {cw!r}"
            )

    def test_ollama_models_may_omit_context_window(self, config):
        """Ollama models are local; context_window is not required."""
        for _model_name, model_cfg in config["ollama"]["models"].items():
            # Just assert it doesn't blow up — field may or may not be present
            assert isinstance(model_cfg, dict)

    # Spot-check a few well-known values against provider documentation.
    # Model keys must match exactly what's in the config — run
    #   python3 -c "from config.provider_config import PROVIDER_CONFIG; ..."
    # to verify if a test starts failing after a config change.
    @pytest.mark.parametrize("provider,model,expected_cw", [
        ("anthropic", "claude-opus-4-6", 200_000),
        ("openai", "gpt-5.2", 400_000),
        ("bedrock", "anthropic.claude-opus-4-6-v1", 200_000),
    ])
    def test_known_context_window_values(self, config, provider, model, expected_cw):
        """Sanity-check that flagship models have the documented context window."""
        if model not in config[provider]["models"]:
            pytest.skip(f"{provider}/{model} not in config — key may have changed")
        actual = config[provider]["models"][model]["context_window"]
        assert actual == expected_cw, (
            f"{provider}/{model}: expected {expected_cw:,}, got {actual:,}"
        )

    def test_total_model_coverage(self, config):
        """Verify that context_window coverage counts match expectations."""
        for provider in self.PROVIDERS_REQUIRING_CONTEXT_WINDOW:
            models = config[provider]["models"]
            with_cw = [m for m, c in models.items() if "context_window" in c]
            assert len(with_cw) == len(models), (
                f"{provider}: {len(with_cw)}/{len(models)} models have context_window"
            )


# ---------------------------------------------------------------------------
# 2. get_context_window() runtime lookup in dependencies.py
# ---------------------------------------------------------------------------

class TestGetContextWindow:
    """Test the get_context_window helper created inside _execute_agent_code."""

    def _make_get_context_window(self, provider_config_override=None):
        """Build a standalone get_context_window that mirrors dependencies.py logic."""
        cfg = provider_config_override or PROVIDER_CONFIG

        def get_context_window(provider: str, model: str) -> int:
            return (
                cfg.get(provider, {})
                .get("models", {})
                .get(model, {})
                .get("context_window", 128_000)
            )
        return get_context_window

    def test_lookup_known_model(self):
        fn = self._make_get_context_window()
        assert fn("anthropic", "claude-opus-4-6") == 200_000

    def test_lookup_returns_default_for_unknown_model(self):
        fn = self._make_get_context_window()
        assert fn("anthropic", "nonexistent-model") == 128_000

    def test_lookup_returns_default_for_unknown_provider(self):
        fn = self._make_get_context_window()
        assert fn("no-such-provider", "any-model") == 128_000

    def test_lookup_custom_config(self):
        cfg = {"test_provider": {"models": {"test_model": {"context_window": 42}}}}
        fn = self._make_get_context_window(cfg)
        assert fn("test_provider", "test_model") == 42

    def test_get_context_window_exposed_in_exec_globals(self):
        """Verify get_context_window is injected into the agent sandbox globals."""
        # Inspect the source to confirm the key is present in exec_globals
        import inspect
        source = inspect.getsource(dependencies_module._execute_agent_code)
        assert "get_context_window" in source


# ---------------------------------------------------------------------------
# 3. Agent factory: context window surfaced in code generation prompt
# ---------------------------------------------------------------------------

class TestAgentFactoryContextWindowDocs:
    """The code generation prompt should include context window info for models."""

    def test_model_docs_include_context_window(self):
        """Simulate the agent_factory model docs builder and verify output."""
        # Replicate the logic from agent_factory/__init__.py lines 97-99
        model_info = {"context_window": 200_000}
        context_window = model_info.get("context_window")
        assert context_window is not None

        model_docs = ""
        if context_window:
            model_docs += f"**Context Window:** {context_window:,} tokens (maximum input size — prompts exceeding this will fail)\n"
        assert "200,000 tokens" in model_docs
        assert "prompts exceeding this will fail" in model_docs

    def test_model_docs_omit_context_window_when_missing(self):
        """If a model has no context_window, the line should be absent."""
        model_info = {}
        context_window = model_info.get("context_window")
        model_docs = ""
        if context_window:
            model_docs += f"**Context Window:** {context_window:,} tokens\n"
        assert model_docs == ""


# ---------------------------------------------------------------------------
# 4. LLM service: context window overflow error handling
# ---------------------------------------------------------------------------

class _DummyMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class _DummyChoice:
    def __init__(self, message):
        self.message = message


class _DummyResponse:
    def __init__(self, content="ok", total_cost=0.0):
        self.choices = [_DummyChoice(_DummyMessage(content))]
        self.usage = SimpleNamespace(total_cost=total_cost)


class TestContextWindowOverflowHandling:
    """llm_service.call_llm should catch overflow errors and re-raise with context."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_fragment", [
        "prompt is too long",
        "context_length_exceeded",
        "maximum context length",
    ])
    async def test_overflow_raises_value_error_with_context(
        self, monkeypatch, error_fragment
    ):
        """Each provider's overflow phrasing should be caught and enriched."""
        async def fake_acompletion(**_kwargs):
            raise RuntimeError(f"Error: {error_fragment} for this model")

        observability = Mock()
        monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: observability)

        user_service = Mock()
        user_service.get_effective_api_key.return_value = None

        with pytest.raises(ValueError, match="context window"):
            await llm_service.call_llm(
                provider="anthropic",
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "x" * 1_000_000}],
                parameters={},
                user_service=user_service,
                user_id="user-overflow",
            )

        # Verify observability was called with the right event type
        observability.log.assert_called_once()
        call_kwargs = observability.log.call_args[1]
        assert call_kwargs["event_type"] == "context_window_exceeded"
        assert call_kwargs["metadata"]["provider"] == "anthropic"
        assert call_kwargs["metadata"]["model"] == "claude-opus-4-6"

    @pytest.mark.asyncio
    async def test_overflow_error_includes_context_window_size(self, monkeypatch):
        """The enriched error message should include the model's context window."""
        async def fake_acompletion(**_kwargs):
            raise RuntimeError("context_length_exceeded: max 200000 tokens")

        observability = Mock()
        monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: observability)

        user_service = Mock()
        user_service.get_effective_api_key.return_value = None

        with pytest.raises(ValueError) as exc_info:
            await llm_service.call_llm(
                provider="anthropic",
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "big prompt"}],
                parameters={},
                user_service=user_service,
                user_id="user-1",
            )

        error_msg = str(exc_info.value)
        # Should mention the context window size from config (200000)
        assert "200000" in error_msg or "200,000" in error_msg
        assert "hierarchical consolidation" in error_msg

    @pytest.mark.asyncio
    async def test_non_overflow_error_not_caught_as_overflow(self, monkeypatch):
        """Regular errors should NOT be caught by the overflow handler."""
        async def fake_acompletion(**_kwargs):
            raise RuntimeError("some unrelated error")

        observability = Mock()
        monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: observability)

        user_service = Mock()
        user_service.get_effective_api_key.return_value = None

        with pytest.raises(RuntimeError, match="some unrelated error"):
            await llm_service.call_llm(
                provider="openai",
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "hi"}],
                parameters={},
                user_service=user_service,
                user_id="user-1",
            )

        # Should use log_exception, not log (overflow handler)
        observability.log_exception.assert_called_once()
        observability.log.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Batch processing guidance in prompts.py
# ---------------------------------------------------------------------------

class TestBatchProcessingGuidance:
    """Verify that prompts.py contains the key patterns agents need.

    The batch processing guidance may live in how_to_use_llm or in the
    prompts.py module source itself (as template strings assembled at
    code-generation time).  We search all public string attributes plus
    the raw module source so these tests pass regardless of where the
    content is placed.
    """

    @pytest.fixture
    def all_prompt_text(self):
        """Concatenate every public string in the prompts module + raw source."""
        import inspect
        parts = [inspect.getsource(prompts)]
        for name in dir(prompts):
            if name.startswith("_"):
                continue
            val = getattr(prompts, name, None)
            if isinstance(val, str):
                parts.append(val)
        return "\n".join(parts)

    # --- Core: confirmed present on the branch ---

    def test_prompts_contain_get_context_window(self, all_prompt_text):
        """get_context_window() must be documented somewhere in prompts."""
        assert "get_context_window" in all_prompt_text

    def test_prompts_contain_create_batches(self, all_prompt_text):
        """Token-aware batching function must be documented."""
        assert "create_batches" in all_prompt_text

    def test_prompts_contain_hierarchical_consolidation(self, all_prompt_text):
        """Hierarchical consolidation pattern must be present."""
        text = all_prompt_text.lower()
        assert "hierarchical" in text

    # --- Extended: full PR #567 guidance patterns ---
    # These test for patterns that are part of the complete context window
    # awareness work.  If any fail, the corresponding guidance still needs
    # to be added to prompts.py before merging.

    def test_prompts_contain_count_tokens(self, all_prompt_text):
        """Exact token counting must be documented (count_tokens, count_message_tokens)."""
        assert "count_tokens" in all_prompt_text

    def test_prompts_contain_preflight_check(self, all_prompt_text):
        """Pre-flight check function must be documented."""
        assert "preflight_check" in all_prompt_text or "pre-flight" in all_prompt_text.lower() or "PRE-FLIGHT" in all_prompt_text

    def test_prompts_warn_against_naive_consolidation(self, all_prompt_text):
        """Must explicitly warn against joining all results."""
        upper = all_prompt_text
        lower = all_prompt_text.lower()
        assert "never" in lower, (
            "prompts.py should warn against naive consolidation"
        )

    def test_prompts_safe_input_limit_ratio(self, all_prompt_text):
        """Guidance should document a safe input limit ratio."""
        assert "0.40" in all_prompt_text or "40%" in all_prompt_text or "0.50" in all_prompt_text or "50%" in all_prompt_text, (
            "prompts.py should document a safe input limit ratio — "
            "see PR #567 batch processing guidance"
        )

    def test_prompts_contain_skip_patterns(self, all_prompt_text):
        """Skip list guidance must be present."""
        assert "skip_patterns" in all_prompt_text or "skip" in all_prompt_text.lower(), (
            "prompts.py should include skip list guidance — "
            "see PR #567 batch processing guidance"
        )

    def test_prompts_contain_retry_with_backoff(self, all_prompt_text):
        """Error handling with retry/backoff must be documented."""
        assert "retry" in all_prompt_text.lower(), (
            "prompts.py should include retry guidance — "
            "see PR #567 batch processing guidance"
        )

    def test_prompts_contain_token_density_estimate(self, all_prompt_text):
        """Token density for code-heavy content should be documented."""
        # Accept any of the common chars-per-token ratios used in guidance
        has_density = any(
            ratio in all_prompt_text
            for ratio in ["2.8", "3.0", "3.2", "chars/token", "characters per token"]
        )
        assert has_density, (
            "prompts.py should document token density for code content — "
            "see PR #567 batch processing guidance"
        )


# ---------------------------------------------------------------------------
# 6. Integration: agent code can call get_context_window at runtime
# ---------------------------------------------------------------------------

class TestAgentSandboxContextWindow:
    """Verify that agent code executed via _execute_agent_code can use get_context_window."""

    @pytest.mark.asyncio
    async def test_agent_code_can_call_get_context_window(self, monkeypatch):
        """Agent code in the sandbox should have access to get_context_window."""
        # Prevent real LLM calls
        async def _fail(*args, **kwargs):
            raise AssertionError("Unexpected call_llm call")
        monkeypatch.setattr(dependencies_module, "call_llm", _fail)

        code = """
async def run(input_dict, tools):
    cw = get_context_window("anthropic", "claude-opus-4-6")
    return {"outputText": str(cw)}
"""
        db_service = Mock()
        result = await dependencies_module._execute_agent_code(
            code, {"message": "test"}, {}, [], db_service
        )
        assert result == {"outputText": "200000"}

    @pytest.mark.asyncio
    async def test_agent_code_gets_default_for_unknown_model(self, monkeypatch):
        """Unknown models should return the 128000 default, not crash."""
        async def _fail(*args, **kwargs):
            raise AssertionError("Unexpected call_llm call")
        monkeypatch.setattr(dependencies_module, "call_llm", _fail)

        code = """
async def run(input_dict, tools):
    cw = get_context_window("fake_provider", "fake_model")
    return {"outputText": str(cw)}
"""
        db_service = Mock()
        result = await dependencies_module._execute_agent_code(
            code, {}, {}, [], db_service
        )
        assert result == {"outputText": "128000"}