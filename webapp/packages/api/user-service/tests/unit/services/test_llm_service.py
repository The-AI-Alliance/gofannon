"""Unit tests for LLM service."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from services import llm_service


pytestmark = pytest.mark.unit


class _DummyMessage:
    def __init__(self, content: str):
        self.content = content
        self.tool_calls = None


class _DummyChoice:
    def __init__(self, message):
        self.message = message


class _DummyResponse:
    def __init__(self, content: str, total_cost: float = 0.0):
        self.choices = [_DummyChoice(_DummyMessage(content))]
        self.usage = SimpleNamespace(total_cost=total_cost)


@pytest.mark.asyncio
async def test_call_llm_acompletion_success(monkeypatch):
    async def fake_acompletion(**_kwargs):
        return _DummyResponse("hello", total_cost=1.23)

    monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: Mock())

    user_service = Mock()

    content, thoughts = await llm_service.call_llm(
        provider="openai",
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        parameters={},
        user_service=user_service,
        user_id="user-1",
    )

    assert content == "hello"
    assert thoughts is None
    user_service.require_allowance.assert_called_once_with("user-1", basic_info=None)
    user_service.add_usage.assert_called_once_with("user-1", 1.23, basic_info=None)


@pytest.mark.asyncio
async def test_call_llm_acompletion_error(monkeypatch):
    async def fake_acompletion(**_kwargs):
        raise RuntimeError("boom")

    observability = Mock()
    monkeypatch.setattr(llm_service.litellm, "acompletion", fake_acompletion)
    monkeypatch.setattr(llm_service, "get_observability_service", lambda: observability)

    user_service = Mock()

    with pytest.raises(RuntimeError, match="boom"):
        await llm_service.call_llm(
            provider="openai",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            parameters={},
            user_service=user_service,
            user_id="user-2",
        )

    observability.log_exception.assert_called_once()
