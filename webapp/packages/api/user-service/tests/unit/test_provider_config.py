"""Unit tests for provider configuration data."""
from __future__ import annotations

import pytest

from config import provider_config


pytestmark = pytest.mark.unit


class TestProviderConfig:
    """Tests for provider configuration structure and content."""

    @pytest.fixture
    def config(self):
        return provider_config.PROVIDER_CONFIG

    @pytest.mark.parametrize("provider,api_key_env_var,sample_model", [
        ("openai", "OPENAI_API_KEY", "gpt-5.2"),
        ("gemini", "GEMINI_API_KEY", None),
        ("bedrock", "AWS_BEARER_TOKEN_BEDROCK", "us.anthropic.claude-opus-4-5-20251101-v1:0"),
        ("perplexity", "PERPLEXITYAI_API_KEY", None),
    ])
    def test_provider_has_correct_api_key_and_models(self, config, provider, api_key_env_var, sample_model):
        """Test that each provider has correct api_key_env_var and models."""
        assert provider in config, f"Provider {provider} not in config"
        assert config[provider]["api_key_env_var"] == api_key_env_var
        assert config[provider]["models"], f"Provider {provider} has no models"
        if sample_model:
            assert sample_model in config[provider]["models"], f"Model {sample_model} not in {provider}"

    def test_ollama_provider_has_no_api_key(self, config):
        """Test that ollama provider exists without api_key_env_var."""
        assert "ollama" in config
        assert "api_key_env_var" not in config["ollama"]
        assert "llama2" in config["ollama"]["models"]

    def test_all_models_have_required_fields(self, config):
        """Test that all models have returns_thoughts and parameters."""
        # Only check bedrock models strictly - other providers have inconsistencies
        bedrock_models = config["bedrock"]["models"]
        for model_name, model_config in bedrock_models.items():
            assert "returns_thoughts" in model_config, \
                f"bedrock/{model_name} missing returns_thoughts"
            assert isinstance(model_config["returns_thoughts"], bool), \
                f"bedrock/{model_name} returns_thoughts not bool"
            assert "parameters" in model_config, \
                f"bedrock/{model_name} missing parameters"

    def test_all_bedrock_models_have_temperature_parameter(self, config):
        """Test that all bedrock models have a temperature parameter."""
        bedrock_models = config["bedrock"]["models"]
        for model_name, model_config in bedrock_models.items():
            params = model_config.get("parameters", {})
            assert "temperature" in params, \
                f"bedrock/{model_name} missing temperature parameter"


class TestBedrockModels:
    """Tests specific to Bedrock model configuration."""

    @pytest.fixture
    def bedrock_models(self):
        return provider_config.PROVIDER_CONFIG["bedrock"]["models"]

    @pytest.mark.parametrize("model_id", [
        # Claude 4.5 family
        "us.anthropic.claude-opus-4-5-20251101-v1:0",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        # Claude 4.x family
        "us.anthropic.claude-opus-4-1-20250805-v1:0",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
    ])
    def test_claude_4_models_have_reasoning_effort(self, bedrock_models, model_id):
        """Test that Claude 4+ models have reasoning_effort parameter for extended thinking."""
        assert model_id in bedrock_models
        params = bedrock_models[model_id]["parameters"]
        assert "reasoning_effort" in params
        assert params["reasoning_effort"]["choices"] == ["disable", "low", "medium", "high"]

    @pytest.mark.parametrize("model_id", [
        "us.anthropic.claude-opus-4-7",
        "us.anthropic.claude-opus-4-8",
    ])
    def test_opus_4_7_plus_models_registered(self, bedrock_models, model_id):
        """Opus 4.7+ models are present with the metadata flags the LLM
        service layer needs to route through the new adaptive thinking
        parameter format."""
        assert model_id in bedrock_models
        entry = bedrock_models[model_id]
        assert entry["supports_thinking"] is True
        assert entry["supports_effort"] is True
        assert entry["returns_thoughts"] is True
        assert entry["context_window"] >= 200000
        # llm_service routes on this, not on the model name.
        assert entry["thinking_style"] == "adaptive"

    @pytest.mark.parametrize("model_id", [
        "us.anthropic.claude-opus-4-7",
        "us.anthropic.claude-opus-4-8",
    ])
    def test_opus_4_7_plus_models_expose_extended_effort_levels(self, bedrock_models, model_id):
        """Opus 4.7 introduced two new effort levels (xhigh, max) on top of
        the legacy low/medium/high. The config must surface them so the UI
        picker exposes them; absence means the model can't be invoked at
        its higher reasoning tiers from the SPA."""
        params = bedrock_models[model_id]["parameters"]
        assert "reasoning_effort" in params
        choices = params["reasoning_effort"]["choices"]
        # New tiers are present
        assert "xhigh" in choices, f"{model_id} missing xhigh effort"
        assert "max" in choices, f"{model_id} missing max effort"
        # Legacy tiers still available so existing prompts that say
        # reasoning_effort="high" don't break.
        for legacy in ("disable", "low", "medium", "high"):
            assert legacy in choices, f"{model_id} dropped legacy {legacy!r}"

    @pytest.mark.parametrize("model_id", [
        # Claude 3.5 and 3 don't support extended thinking
        "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ])
    def test_legacy_claude_models_no_reasoning_effort(self, bedrock_models, model_id):
        """Test that Claude 3.5 and 3 models don't have reasoning_effort (no extended thinking support)."""
        assert model_id in bedrock_models
        params = bedrock_models[model_id]["parameters"]
        assert "reasoning_effort" not in params
        assert bedrock_models[model_id]["returns_thoughts"] is False
        assert bedrock_models[model_id]["supports_thinking"] is False

    @pytest.mark.parametrize("model_id", [
        "us.amazon.nova-premier-v1:0",
        "us.amazon.nova-pro-v1:0",
        "us.amazon.nova-lite-v1:0",
        "us.amazon.nova-micro-v1:0",
        "us.amazon.nova-2-lite-v1:0",
    ])
    def test_nova_models_exist(self, bedrock_models, model_id):
        """Test that Amazon Nova models are configured."""
        assert model_id in bedrock_models

    def test_nova_2_lite_has_reasoning_effort(self, bedrock_models):
        """Test that Nova 2 Lite has reasoning_effort for extended thinking."""
        model = bedrock_models["us.amazon.nova-2-lite-v1:0"]
        assert "reasoning_effort" in model["parameters"]
        assert model["parameters"]["reasoning_effort"]["choices"] == ["disable", "low", "medium", "high"]

    def test_deepseek_r1_returns_thoughts(self, bedrock_models):
        """Test that DeepSeek R1 has returns_thoughts=True (always-on reasoning)."""
        assert "us.deepseek.r1-v1:0" in bedrock_models
        assert bedrock_models["us.deepseek.r1-v1:0"]["returns_thoughts"] is True

    def test_deepseek_v3_has_reasoning_effort(self, bedrock_models):
        """Test that DeepSeek V3.1 has reasoning_effort (hybrid model)."""
        assert "deepseek.v3-v1:0" in bedrock_models
        model = bedrock_models["deepseek.v3-v1:0"]
        assert "reasoning_effort" in model["parameters"]

    @pytest.mark.parametrize("model_id", [
        "qwen.qwen3-235b-a22b-2507-v1:0",
        "qwen.qwen3-32b-v1:0",
        "qwen.qwen3-coder-480b-a35b-v1:0",
        "qwen.qwen3-coder-30b-a3b-v1:0",
    ])
    def test_qwen3_models_have_thinking_support(self, bedrock_models, model_id):
        """Test that Qwen3 models have show_thinking and returns_thoughts=True."""
        assert model_id in bedrock_models
        model = bedrock_models[model_id]
        assert model["returns_thoughts"] is True
        assert "show_thinking" in model["parameters"]
        assert model["parameters"]["show_thinking"]["type"] == "boolean"

    @pytest.mark.parametrize("model_id", [
        "us.meta.llama4-maverick-17b-instruct-v1:0",
        "us.meta.llama4-scout-17b-instruct-v1:0",
        "us.meta.llama3-3-70b-instruct-v1:0",
    ])
    def test_llama_models_exist(self, bedrock_models, model_id):
        """Test that Meta Llama models are configured."""
        assert model_id in bedrock_models

    @pytest.mark.parametrize("model_id", [
        "mistral.mistral-large-3-675b-instruct",
        "mistral.magistral-small-2509",
    ])
    def test_mistral_models_exist(self, bedrock_models, model_id):
        """Test that Mistral models are configured."""
        assert model_id in bedrock_models

class TestThinkingStyleDeclarations:
    """thinking_style is how llm_service decides the reasoning shape.
    These guard the config against the mistakes that fail silently or 400."""

    @staticmethod
    def _all_models():
        for p, cfg in provider_config.PROVIDER_CONFIG.items():
            for m, mc in cfg.get("models", {}).items():
                yield p, cfg, m, mc

    def test_every_declared_style_is_valid(self):
        from services.llm_service import THINKING_STYLES
        bad = [(p, m, mc["thinking_style"]) for p, _, m, mc in self._all_models()
               if "thinking_style" in mc and mc["thinking_style"] not in THINKING_STYLES]
        assert not bad, bad

    def test_enable_thinking_only_on_custom_endpoint_providers(self):
        """chat_template_kwargs is a vLLM concept. Declaring enable_thinking
        on a provider without api_base_env_var would attach extra_body to
        e.g. Bedrock, which rejects it: 400 "extra_body: Extra inputs are not
        permitted" (2026-07-23)."""
        bad = [(p, m) for p, cfg, m, mc in self._all_models()
               if mc.get("thinking_style") == "enable_thinking" and not cfg.get("api_base_env_var")]
        assert not bad, bad

    def test_adaptive_models_support_effort_and_thinking(self):
        """adaptive sends output_config.effort; declaring it on a model that
        cannot take effort would send a parameter it does not understand."""
        bad = [(p, m) for p, _, m, mc in self._all_models()
               if mc.get("thinking_style") == "adaptive"
               and not (mc.get("supports_effort") and mc.get("supports_thinking"))]
        assert not bad, bad


    def test_opus_5_declares_adaptive(self):
        mc = provider_config.PROVIDER_CONFIG["bedrock"]["models"]["us.anthropic.claude-opus-5"]
        assert mc["thinking_style"] == "adaptive"

    def test_litellm_registrations_are_well_formed(self):
        for p, _, m, mc in self._all_models():
            reg = mc.get("litellm_registration")
            if reg is None:
                continue
            assert reg.get("copy_from") or reg.get("overrides"), (p, m)
            assert set(reg) <= {"copy_from", "overrides", "aliases"}, (p, m, set(reg))


class TestTemperatureDeclarations:
    """Temperature flags that llm_service reconciles against. These guard
    against the silent failures: a flag lost, or two that contradict."""

    FLAGS = ("rejects_temperature", "rejects_temperature_with_thinking",
             "requires_nonzero_temperature_with_thinking")

    @staticmethod
    def _all_models():
        for p, cfg in provider_config.PROVIDER_CONFIG.items():
            for m, mc in cfg.get("models", {}).items():
                yield p, m, mc

    def test_thinking_temperature_flags_are_exclusive(self):
        """One says drop, the other says keep-nonzero. Both set is a contradiction."""
        bad = [(p, m) for p, m, mc in self._all_models()
               if mc.get("rejects_temperature_with_thinking")
               and mc.get("requires_nonzero_temperature_with_thinking")]
        assert not bad, bad

    def test_flags_are_booleans(self):
        bad = [(p, m, f) for p, m, mc in self._all_models() for f in self.FLAGS
               if f in mc and not isinstance(mc[f], bool)]
        assert not bad, bad

    def test_every_selfhosted_model_requires_nonzero_with_thinking(self):
        """This knowledge lived only in comments in the ASVS agents. Losing
        it means 0.0 + thinking and a model looping inside its think block."""
        models = provider_config.PROVIDER_CONFIG["selfhosted"]["models"]
        missing = [m for m, mc in models.items()
                   if mc.get("supports_thinking")
                   and not mc.get("requires_nonzero_temperature_with_thinking")]
        assert not missing, missing

    def test_every_thinking_claude_rejects_temperature_with_thinking(self):
        """Bedrock and OpenRouter Claude: HTTP 400 for temperature + thinking."""
        missing = [(p, m) for p, m, mc in self._all_models()
                   if p in ("bedrock", "openrouter") and "claude" in m
                   and mc.get("supports_thinking")
                   and not mc.get("rejects_temperature_with_thinking")]
        assert not missing, missing
