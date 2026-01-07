"""Unit tests for dependencies utilities."""
from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import dependencies as dependencies_module
from config import settings
from dependencies import _execute_agent_code, process_chat, require_admin_access
from models.chat import ChatMessage, ChatRequest


pytestmark = pytest.mark.unit


@pytest.fixture
def prevent_litellm_calls(monkeypatch):
    async def _fail(*args, **kwargs):
        raise AssertionError("Unexpected litellm call")

    monkeypatch.setattr(dependencies_module.litellm, "aresponses", _fail)
    monkeypatch.setattr(dependencies_module.litellm, "aget_responses", _fail)
    monkeypatch.setattr(dependencies_module.litellm, "acompletion", _fail)


def _build_request() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/chat",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 1234),
    }
    return Request(scope)


def test_require_admin_access_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PANEL_ENABLED", False)

    with pytest.raises(HTTPException) as exc_info:
        require_admin_access("secret")

    assert exc_info.value.status_code == 403


def test_require_admin_access_invalid_password(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PANEL_ENABLED", True)
    monkeypatch.setattr(settings, "ADMIN_PANEL_PASSWORD", "secret")

    with pytest.raises(HTTPException) as exc_info:
        require_admin_access("wrong")

    assert exc_info.value.status_code == 401


def test_require_admin_access_valid_password(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PANEL_ENABLED", True)
    monkeypatch.setattr(settings, "ADMIN_PANEL_PASSWORD", "secret")

    assert require_admin_access("secret") is None


@pytest.mark.asyncio
async def test_execute_agent_code_success(prevent_litellm_calls):
    code = """
async def run(input_dict, tools):
    return {"outputText": input_dict["message"]}
"""
    db_service = Mock()

    result = await _execute_agent_code(code, {"message": "hello"}, {}, [], db_service)

    assert result == {"outputText": "hello"}


@pytest.mark.asyncio
async def test_execute_agent_code_missing_run(prevent_litellm_calls):
    code = """
async def not_run(input_dict, tools):
    return {"outputText": "nope"}
"""

    with pytest.raises(ValueError, match="async def run"):
        await _execute_agent_code(code, {}, {}, [], Mock())


@pytest.mark.asyncio
async def test_execute_agent_code_non_async_run(prevent_litellm_calls):
    code = """

def run(input_dict, tools):
    return {"outputText": "nope"}
"""

    with pytest.raises(ValueError, match="async def run"):
        await _execute_agent_code(code, {}, {}, [], Mock())


@pytest.mark.asyncio
async def test_process_chat_gofannon_flow(monkeypatch, prevent_litellm_calls):
    ticket_saves = []
    db_service = Mock()

    def save(collection, key, data):
        ticket_saves.append((collection, key, data))

    def get(collection, key):
        if collection == "deployments":
            return {"agentId": "agent-1"}
        if collection == "agents":
            return {
                "_id": "agent-1",
                "name": "Test Agent",
                "description": "Test",
                "code": "async def run(input_dict, tools):\n    return {\"outputText\": \"ok\"}",
            }
        if collection == "tickets":
            return ticket_saves[-1][2]
        raise KeyError(f"Unexpected collection {collection}")

    db_service.save.side_effect = save
    db_service.get.side_effect = get

    fake_user_service = Mock()

    class FakeLogger:
        def __init__(self):
            self.calls = []

        def log(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    fake_logger = FakeLogger()

    async def fake_execute_agent_code(*, code, input_dict, tools, gofannon_agents, db):
        return {"outputText": f"agent:{input_dict['inputText']}"}

    monkeypatch.setattr(dependencies_module, "get_database_service", lambda _settings: db_service)
    monkeypatch.setattr(dependencies_module, "get_user_service", lambda _db: fake_user_service)
    monkeypatch.setattr(dependencies_module, "get_observability_service", lambda: fake_logger)
    monkeypatch.setattr(dependencies_module, "_execute_agent_code", fake_execute_agent_code)

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="hello")],
        provider="gofannon",
        model="agent-friendly",
        parameters={},
    )
    user = {"uid": "user-1", "email": "user@example.com", "name": "Test User"}

    await process_chat("ticket-1", request, user, _build_request())

    assert ticket_saves[0][2]["status"] == "processing"
    assert ticket_saves[-1][2]["status"] == "completed"
    assert ticket_saves[-1][2]["result"]["content"] == "agent:hello"
    assert ticket_saves[-1][2]["result"]["model"] == "gofannon/agent-friendly"


@pytest.mark.asyncio
async def test_process_chat_non_gofannon_flow(monkeypatch, prevent_litellm_calls):
    ticket_saves = []
    db_service = Mock()

    def save(collection, key, data):
        ticket_saves.append((collection, key, data))

    db_service.save.side_effect = save
    db_service.get = Mock()

    fake_user_service = Mock()

    class FakeLogger:
        def __init__(self):
            self.calls = []

        def log(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    fake_logger = FakeLogger()
    call_args = {}

    async def fake_call_llm(**kwargs):
        call_args.update(kwargs)
        return "llm response", {"notes": "done"}

    monkeypatch.setattr(dependencies_module, "get_database_service", lambda _settings: db_service)
    monkeypatch.setattr(dependencies_module, "get_user_service", lambda _db: fake_user_service)
    monkeypatch.setattr(dependencies_module, "get_observability_service", lambda: fake_logger)
    monkeypatch.setattr(dependencies_module, "call_llm", fake_call_llm)

    request = ChatRequest(
        messages=[ChatMessage(role="user", content="hello")],
        provider="openai",
        model="gpt-4o-mini",
        parameters={"temperature": 0.1},
    )
    user = {"uid": "user-2", "email": "user@example.com"}

    await process_chat("ticket-2", request, user, _build_request())

    assert call_args["provider"] == "openai"
    assert call_args["model"] == "gpt-4o-mini"
    assert ticket_saves[0][2]["status"] == "processing"
    assert ticket_saves[-1][2]["status"] == "completed"
    assert ticket_saves[-1][2]["result"]["content"] == "llm response"
    assert ticket_saves[-1][2]["result"]["model"] == "openai/gpt-4o-mini"
