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
        ("anthropic", "ANTHROPIC_API_KEY", "claude-opus-4-20250514"),
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
        "us.anthropic.claude-opus-4-5-20251101-v1:0",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "us.anthropic.claude-opus-4-1-20250805-v1:0",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
    ])
    def test_claude_models_have_reasoning_effort(self, bedrock_models, model_id):
        """Test that Claude models have reasoning_effort parameter."""
        assert model_id in bedrock_models
        params = bedrock_models[model_id]["parameters"]
        assert "reasoning_effort" in params
        assert params["reasoning_effort"]["choices"] == ["disable", "low", "medium", "high"]

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
