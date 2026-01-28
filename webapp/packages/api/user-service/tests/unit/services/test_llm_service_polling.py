"""Unit tests for LLM service aresponses polling feature.

These tests verify that the OpenAI Responses API polling correctly handles
API keys and response status polling.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch, call

import pytest
import asyncio

from services import llm_service


pytestmark = pytest.mark.unit


class _DummyResponseObj:
    """Mock response object from aresponses."""
    def __init__(self, response_id: str):
        self.id = response_id


class _DummyResponseStatus:
    """Mock response status from aget_responses."""
    def __init__(self, status: str, output=None):
        self.status = status
        self.output = output or []


class TestLLMServicePolling:
    """Test suite for aresponses polling with API keys."""

    @pytest.mark.asyncio
    async def test_polling_passes_api_key_to_both_calls(self, monkeypatch):
        """Test that API key is passed to both aresponses and aget_responses.
        
        This is the regression test for the bug where aget_responses was not
        receiving the API key, causing auth failures when using user-specific keys.
        """
        aresponses_calls = []
        aget_responses_calls = []
        
        async def fake_aresponses(**kwargs):
            aresponses_calls.append(kwargs)
            return _DummyResponseObj("resp-123")
        
        async def fake_aget_responses(**kwargs):
            aget_responses_calls.append(kwargs)
            # Return completed on first poll
            return _DummyResponseStatus("completed", output=[
                {"type": "message", "content": [{"type": "text", "text": "Hello"}]}
            ])
        
        monkeypatch.setattr(llm_service.litellm, "aresponses", fake_aresponses)
        monkeypatch.setattr(llm_service.litellm, "aget_responses", fake_aget_responses)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
        monkeypatch.setattr(llm_service, "PROVIDER_CONFIG", {
            "openai": {
                "models": {
                    "gpt-4o": {"api_style": "responses"}
                }
            }
        })
        
        # Speed up the test by reducing sleep time
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            return await original_sleep(0.01)
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        
        user_service = Mock()
        user_service.get_effective_api_key.return_value = "user-specific-key-123"
        
        content, thoughts = await llm_service.call_llm(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            parameters={},
            tools=[{"type": "web_search"}],  # Trigger aresponses path
            user_service=user_service,
            user_id="user-1",
        )
        
        # Verify aresponses received the API key
        assert len(aresponses_calls) == 1
        assert aresponses_calls[0].get("api_key") == "user-specific-key-123"
        
        # Verify aget_responses ALSO received the API key (this was the bug)
        assert len(aget_responses_calls) == 1
        assert aget_responses_calls[0].get("api_key") == "user-specific-key-123"
        assert aget_responses_calls[0].get("response_id") == "resp-123"

    @pytest.mark.asyncio
    async def test_polling_without_api_key(self, monkeypatch):
        """Test that polling works correctly when no user API key is set."""
        aresponses_calls = []
        aget_responses_calls = []
        
        async def fake_aresponses(**kwargs):
            aresponses_calls.append(kwargs)
            return _DummyResponseObj("resp-456")
        
        async def fake_aget_responses(**kwargs):
            aget_responses_calls.append(kwargs)
            return _DummyResponseStatus("completed", output=[
                {"type": "message", "content": [{"type": "text", "text": "No key response"}]}
            ])
        
        monkeypatch.setattr(llm_service.litellm, "aresponses", fake_aresponses)
        monkeypatch.setattr(llm_service.litellm, "aget_responses", fake_aget_responses)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
        monkeypatch.setattr(llm_service, "PROVIDER_CONFIG", {
            "openai": {
                "models": {
                    "gpt-4o": {"api_style": "responses"}
                }
            }
        })
        
        async def fast_sleep(seconds):
            pass
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        
        user_service = Mock()
        user_service.get_effective_api_key.return_value = None  # No user key
        
        content, thoughts = await llm_service.call_llm(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            parameters={},
            tools=[{"type": "web_search"}],
            user_service=user_service,
            user_id="user-1",
        )
        
        # Verify aresponses was called without api_key
        assert len(aresponses_calls) == 1
        assert "api_key" not in aresponses_calls[0]
        
        # Verify aget_responses was called without api_key
        assert len(aget_responses_calls) == 1
        assert "api_key" not in aget_responses_calls[0]
        assert aget_responses_calls[0].get("response_id") == "resp-456"

    @pytest.mark.asyncio
    async def test_polling_multiple_times_before_completion(self, monkeypatch):
        """Test that polling continues until status is 'completed'."""
        aget_responses_calls = []
        poll_count = [0]
        
        async def fake_aresponses(**kwargs):
            return _DummyResponseObj("resp-789")
        
        async def fake_aget_responses(**kwargs):
            aget_responses_calls.append(kwargs)
            poll_count[0] += 1
            
            # Return in_progress for first 2 calls, then completed
            if poll_count[0] < 3:
                return _DummyResponseStatus("in_progress")
            return _DummyResponseStatus("completed", output=[
                {"type": "message", "content": [{"type": "text", "text": "Final answer"}]}
            ])
        
        monkeypatch.setattr(llm_service.litellm, "aresponses", fake_aresponses)
        monkeypatch.setattr(llm_service.litellm, "aget_responses", fake_aget_responses)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
        monkeypatch.setattr(llm_service, "PROVIDER_CONFIG", {
            "openai": {
                "models": {
                    "gpt-4o": {"api_style": "responses"}
                }
            }
        })
        
        async def fast_sleep(seconds):
            pass
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        
        user_service = Mock()
        user_service.get_effective_api_key.return_value = "test-key"
        
        content, thoughts = await llm_service.call_llm(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            parameters={},
            tools=[{"type": "web_search"}],
            user_service=user_service,
            user_id="user-1",
        )
        
        # Verify we polled 3 times
        assert poll_count[0] == 3
        
        # Verify the API key was passed in all polling calls
        for call_kwargs in aget_responses_calls:
            assert call_kwargs.get("api_key") == "test-key"
            assert call_kwargs.get("response_id") == "resp-789"

    @pytest.mark.asyncio
    async def test_polling_timeout_raises_exception(self, monkeypatch):
        """Test that polling raises an exception if it times out."""
        
        async def fake_aresponses(**kwargs):
            return _DummyResponseObj("resp-timeout")
        
        poll_count = [0]
        async def fake_aget_responses(**kwargs):
            poll_count[0] += 1
            # Always return in_progress to trigger timeout
            return _DummyResponseStatus("in_progress")
        
        monkeypatch.setattr(llm_service.litellm, "aresponses", fake_aresponses)
        monkeypatch.setattr(llm_service.litellm, "aget_responses", fake_aget_responses)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
        monkeypatch.setattr(llm_service, "PROVIDER_CONFIG", {
            "openai": {
                "models": {
                    "gpt-4o": {"api_style": "responses"}
                }
            }
        })
        
        # Patch the range in llm_service module directly
        import builtins
        original_range = builtins.range
        
        def short_range(*args):
            # For the polling loop (15), return only 3 iterations
            if len(args) == 1 and args[0] == 15:
                return original_range(3)
            return original_range(*args)
        
        monkeypatch.setattr(builtins, "range", short_range)
        
        async def fast_sleep(seconds):
            pass
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        
        user_service = Mock()
        user_service.get_effective_api_key.return_value = "test-key"
        
        with pytest.raises(Exception, match="Polling for OpenAI Responses API timed out"):
            await llm_service.call_llm(
                provider="openai",
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello"}],
                parameters={},
                tools=[{"type": "web_search"}],
                user_service=user_service,
                user_id="user-1",
            )
        
        # Verify we polled 3 times before giving up
        assert poll_count[0] == 3

    @pytest.mark.asyncio
    async def test_polling_extracts_content_from_response(self, monkeypatch):
        """Test that content is properly extracted from the polling response."""
        
        async def fake_aresponses(**kwargs):
            return _DummyResponseObj("resp-content")
        
        async def fake_aget_responses(**kwargs):
            return _DummyResponseStatus("completed", output=[
                {
                    "type": "reasoning",
                    "summary": [{"type": "text", "text": "Thinking process"}]
                },
                {
                    "type": "message",
                    "content": [{"type": "text", "text": "The final answer"}]
                }
            ])
        
        monkeypatch.setattr(llm_service.litellm, "aresponses", fake_aresponses)
        monkeypatch.setattr(llm_service.litellm, "aget_responses", fake_aget_responses)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
        monkeypatch.setattr(llm_service, "PROVIDER_CONFIG", {
            "openai": {
                "models": {
                    "gpt-4o": {"api_style": "responses"}
                }
            }
        })
        
        async def fast_sleep(seconds):
            pass
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        
        user_service = Mock()
        user_service.get_effective_api_key.return_value = "test-key"
        
        content, thoughts = await llm_service.call_llm(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            parameters={},
            tools=[{"type": "web_search"}],
            user_service=user_service,
            user_id="user-1",
        )
        
        # Verify content was extracted from the second output item
        assert content == "The final answer"
        
        # Verify thoughts were extracted from the first output item
        assert thoughts is not None
        assert thoughts.get("summary") == ["Thinking process"]


class TestLLMServiceResponsesApiKeyHandling:
    """Test API key handling specifically for the responses API path."""

    @pytest.mark.asyncio
    async def test_user_key_takes_precedence_over_env_var(self, monkeypatch):
        """Test that user-specific API key is used when available."""
        captured_keys = {"aresponses": None, "aget_responses": None}
        
        async def fake_aresponses(**kwargs):
            captured_keys["aresponses"] = kwargs.get("api_key")
            return _DummyResponseObj("resp-key-test")
        
        async def fake_aget_responses(**kwargs):
            captured_keys["aget_responses"] = kwargs.get("api_key")
            return _DummyResponseStatus("completed", output=[
                {"type": "message", "content": [{"type": "text", "text": "Done"}]}
            ])
        
        monkeypatch.setattr(llm_service.litellm, "aresponses", fake_aresponses)
        monkeypatch.setattr(llm_service.litellm, "aget_responses", fake_aget_responses)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
        monkeypatch.setattr(llm_service, "PROVIDER_CONFIG", {
            "openai": {
                "models": {
                    "gpt-4o": {"api_style": "responses"}
                }
            }
        })
        
        async def fast_sleep(seconds):
            pass
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        
        user_service = Mock()
        # Simulate a user-specific key
        user_service.get_effective_api_key.return_value = "user-personal-key"
        
        await llm_service.call_llm(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            parameters={},
            tools=[{"type": "web_search"}],
            user_service=user_service,
            user_id="user-1",
        )
        
        # Verify the user's key was used in both calls
        assert captured_keys["aresponses"] == "user-personal-key"
        assert captured_keys["aget_responses"] == "user-personal-key"

    @pytest.mark.asyncio
    async def test_empty_string_key_not_passed_to_polling(self, monkeypatch):
        """Test that empty string API key is treated as no key."""
        captured_keys = {"aresponses": None, "aget_responses": None}
        
        async def fake_aresponses(**kwargs):
            captured_keys["aresponses"] = kwargs.get("api_key")
            return _DummyResponseObj("resp-empty")
        
        async def fake_aget_responses(**kwargs):
            captured_keys["aget_responses"] = kwargs.get("api_key")
            return _DummyResponseStatus("completed", output=[
                {"type": "message", "content": [{"type": "text", "text": "Done"}]}
            ])
        
        monkeypatch.setattr(llm_service.litellm, "aresponses", fake_aresponses)
        monkeypatch.setattr(llm_service.litellm, "aget_responses", fake_aget_responses)
        monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())
        monkeypatch.setattr(llm_service, "PROVIDER_CONFIG", {
            "openai": {
                "models": {
                    "gpt-4o": {"api_style": "responses"}
                }
            }
        })
        
        async def fast_sleep(seconds):
            pass
        monkeypatch.setattr(asyncio, "sleep", fast_sleep)
        
        user_service = Mock()
        # Empty string should be treated as no key
        user_service.get_effective_api_key.return_value = ""
        
        await llm_service.call_llm(
            provider="openai",
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}],
            parameters={},
            tools=[{"type": "web_search"}],
            user_service=user_service,
            user_id="user-1",
        )
        
        # Empty string is falsy, so no api_key should be passed
        assert captured_keys["aresponses"] is None
        assert captured_keys["aget_responses"] is None
