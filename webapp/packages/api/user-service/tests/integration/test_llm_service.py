"""Integration tests for the LLM service.

These tests verify that the llm_service properly integrates with real LLM providers.
Tests are skipped if the required API keys are not available.
"""
import os

import pytest

from config.provider_config import PROVIDER_CONFIG
from services import llm_service


pytestmark = pytest.mark.integration


def _get_api_key_env_var(provider: str) -> str | None:
    """Get the environment variable name for the provider's API key."""
    return PROVIDER_CONFIG.get(provider, {}).get("api_key_env_var")


def _skip_if_missing_api_key(provider: str):
    """Skip the test if the API key for the provider is not set."""
    api_key_env_var = _get_api_key_env_var(provider)
    if api_key_env_var and not os.getenv(api_key_env_var):
        pytest.skip(f"Missing {api_key_env_var} for {provider} integration test.")


@pytest.mark.asyncio
async def test_call_llm_openai_integration():
    """Test call_llm with OpenAI provider."""
    _skip_if_missing_api_key("openai")

    content, thoughts = await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
        parameters={"temperature": 0, "max_tokens": 10},
        user_service=None,
        user_id=None,
    )

    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0
    assert "hello" in content.lower()


@pytest.mark.asyncio
async def test_call_llm_bedrock_integration():
    """Test call_llm with a small Bedrock model."""
    _skip_if_missing_api_key("bedrock")

    content, thoughts = await llm_service.call_llm(
        provider="bedrock",
        model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
        parameters={"temperature": 0, "max_tokens": 10},
        user_service=None,
        user_id=None,
    )

    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0
    assert "hello" in content.lower()


@pytest.mark.asyncio
async def test_stream_llm_openai_integration():
    """Test stream_llm with OpenAI provider."""
    _skip_if_missing_api_key("openai")

    chunks = []
    async for chunk in llm_service.stream_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
        parameters={"temperature": 0, "max_tokens": 10},
        user_service=None,
        user_id=None,
    ):
        chunks.append(chunk)

    assert len(chunks) > 0
    # Verify we can extract content from chunks
    content_parts = []
    for chunk in chunks:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content:
                content_parts.append(delta.content)

    full_content = "".join(content_parts)
    assert "hello" in full_content.lower()


@pytest.mark.asyncio
async def test_call_llm_with_system_message():
    """Test call_llm with a system message."""
    _skip_if_missing_api_key("openai")

    content, thoughts = await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a pirate. Always respond like a pirate."},
            {"role": "user", "content": "Say hello."},
        ],
        parameters={"temperature": 0.5, "max_tokens": 50},
        user_service=None,
        user_id=None,
    )

    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.asyncio
async def test_call_llm_filters_none_parameters():
    """Test that call_llm properly filters out None parameters."""
    _skip_if_missing_api_key("openai")

    # This should not raise an error even with None values
    content, thoughts = await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'test'"}],
        parameters={"temperature": 0.5, "top_p": None, "max_tokens": 10},
        user_service=None,
        user_id=None,
    )

    assert content is not None
    assert isinstance(content, str)
