"""Unit tests for dependencies utilities."""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import dependencies as dependencies_module
from config import settings
from dependencies import _execute_agent_code, process_chat, require_admin_access, get_available_providers
from models.chat import ChatMessage, ChatRequest


pytestmark = pytest.mark.unit


@pytest.fixture
def prevent_direct_llm_calls(monkeypatch):
    """Prevent any direct LLM calls by mocking call_llm to fail."""
    async def _fail(*args, **kwargs):
        raise AssertionError("Unexpected call_llm call in agent code")

    # Mock call_llm at the dependencies module level
    monkeypatch.setattr(dependencies_module, "call_llm", _fail)


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
async def test_execute_agent_code_success():
    """Test basic agent code execution without LLM calls."""
    code = """
async def run(input_dict, tools):
    return {"outputText": input_dict["message"]}
"""
    db_service = Mock()

    result = await _execute_agent_code(code, {"message": "hello"}, {}, [], db_service)

    assert result == {"outputText": "hello"}


@pytest.mark.asyncio
async def test_execute_agent_code_missing_run():
    """Test error when agent code doesn't define run function."""
    code = """
async def not_run(input_dict, tools):
    return {"outputText": "nope"}
"""

    with pytest.raises(ValueError, match="async def run"):
        await _execute_agent_code(code, {}, {}, [], Mock())


@pytest.mark.asyncio
async def test_execute_agent_code_non_async_run():
    """Test error when run function is not async."""
    code = """

def run(input_dict, tools):
    return {"outputText": "nope"}
"""

    with pytest.raises(ValueError, match="async def run"):
        await _execute_agent_code(code, {}, {}, [], Mock())


@pytest.mark.asyncio
async def test_execute_agent_code_with_call_llm(monkeypatch):
    """Test agent code that uses call_llm with user context."""
    call_llm_args = {}

    async def fake_call_llm(**kwargs):
        call_llm_args.update(kwargs)
        return "LLM response content", None

    # Agent code that uses call_llm
    code = """
async def run(input_dict, tools):
    content, _ = await call_llm(
        provider="openai",
        model="gpt-4",
        messages=[{"role": "user", "content": input_dict["message"]}],
        parameters={},
    )
    return {"outputText": content}
"""
    db_service = Mock()

    # We need to patch call_llm at the module level before exec_globals is created
    monkeypatch.setattr(dependencies_module, "call_llm", fake_call_llm)

    result = await _execute_agent_code(
        code, 
        {"message": "test prompt"}, 
        {}, 
        [], 
        db_service,
        user_id="test-user",
        user_basic_info={"email": "test@example.com"}
    )

    assert result == {"outputText": "LLM response content"}
    assert call_llm_args["provider"] == "openai"
    assert call_llm_args["model"] == "gpt-4"
    # Verify user context is passed
    assert call_llm_args["user_id"] == "test-user"
    assert call_llm_args["user_basic_info"] == {"email": "test@example.com"}


@pytest.mark.asyncio
async def test_process_chat_gofannon_flow(monkeypatch):
    """Test chat processing for gofannon provider (agent execution)."""
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

    async def fake_execute_agent_code(*, code, input_dict, tools, gofannon_agents, db, user_id=None, user_basic_info=None):
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
async def test_process_chat_non_gofannon_flow(monkeypatch):
    """Test chat processing for non-gofannon providers (direct LLM call)."""
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


class TestGetAvailableProviders:
    """Test suite for get_available_providers with API key management."""

    @patch.dict("os.environ", {"OPENAI_API_KEY": "env-openai-key"}, clear=True)
    def test_get_available_providers_with_env_var_only(self, monkeypatch):
        """Test providers available when only env var is set."""
        mock_db = Mock()
        mock_db.list_all.return_value = []
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        providers = get_available_providers()

        assert "openai" in providers
        assert "ollama" in providers  # Ollama doesn't require API key

    @patch.dict("os.environ", {}, clear=True)
    def test_get_available_providers_no_keys_set(self, monkeypatch):
        """Test providers when no keys are set."""
        mock_db = Mock()
        mock_db.list_all.return_value = []
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        providers = get_available_providers()

        # OpenAI should not be available without API key
        assert "openai" not in providers
        # Ollama should still be available (no key required)
        assert "ollama" in providers

    def test_get_available_providers_with_user_key(self, monkeypatch):
        """Test providers available when user has API key set."""
        mock_db = Mock()
        mock_db.list_all.return_value = []
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        fake_user_service = Mock()
        # User has OpenAI key set
        fake_user_service.get_effective_api_key.return_value = "user-openai-key"
        monkeypatch.setattr(dependencies_module, "get_user_service", lambda _: fake_user_service)

        # No env var set, but user has key
        with patch.dict("os.environ", {}, clear=True):
            providers = get_available_providers(user_id="user-1")

        # OpenAI should be available because user has key
        assert "openai" in providers
        fake_user_service.get_effective_api_key.assert_called()

    def test_get_available_providers_user_key_takes_precedence(self, monkeypatch):
        """Test that user key is checked before env var."""
        mock_db = Mock()
        mock_db.list_all.return_value = []
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        fake_user_service = Mock()
        fake_user_service.get_effective_api_key.return_value = "user-key"
        monkeypatch.setattr(dependencies_module, "get_user_service", lambda _: fake_user_service)

        with patch.dict("os.environ", {"OPENAI_API_KEY": "env-key"}, clear=True):
            providers = get_available_providers(user_id="user-1")

        assert "openai" in providers
        # Verify get_effective_api_key was called which checks user key first
        fake_user_service.get_effective_api_key.assert_called()

    @patch.dict("os.environ", {}, clear=True)
    def test_get_available_providers_multiple_providers_user_keys(self, monkeypatch):
        """Test availability of multiple providers with different user keys."""
        mock_db = Mock()
        mock_db.list_all.return_value = []
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        fake_user_service = Mock()

        def mock_get_effective_key(user_id, provider, basic_info=None):
            # User has keys for openai and anthropic only
            keys = {
                "openai": "user-openai-key",
                "anthropic": "user-anthropic-key",
                "gemini": None,
                "perplexity": None,
            }
            return keys.get(provider)

        fake_user_service.get_effective_api_key.side_effect = mock_get_effective_key
        monkeypatch.setattr(dependencies_module, "get_user_service", lambda _: fake_user_service)

        providers = get_available_providers(user_id="user-1")

        assert "openai" in providers
        assert "anthropic" in providers
        assert "gemini" not in providers
        assert "perplexity" not in providers
        assert "ollama" in providers  # Always available

    @patch.dict("os.environ", {"OPENAI_API_KEY": "env-key"}, clear=True)
    def test_get_available_providers_without_user_id_uses_env(self, monkeypatch):
        """Test that env vars are used when no user_id is provided."""
        mock_db = Mock()
        mock_db.list_all.return_value = []
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        providers = get_available_providers()

        assert "openai" in providers

    @patch.dict("os.environ", {}, clear=True)
    def test_get_available_providers_with_basic_info(self, monkeypatch):
        """Test that basic_info is passed to get_effective_api_key."""
        mock_db = Mock()
        mock_db.list_all.return_value = []
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        fake_user_service = Mock()
        fake_user_service.get_effective_api_key.return_value = "user-key"
        monkeypatch.setattr(dependencies_module, "get_user_service", lambda _: fake_user_service)

        basic_info = {"email": "test@example.com", "name": "Test User"}
        providers = get_available_providers(user_id="user-1", user_basic_info=basic_info)

        assert "openai" in providers
        # Verify basic_info was passed
        calls = fake_user_service.get_effective_api_key.call_args_list
        for call in calls:
            if call[0][1] == "openai":
                assert call[1]["basic_info"] == basic_info

    @patch.dict("os.environ", {}, clear=True)
    def test_get_available_providers_includes_gofannon_agents(self, monkeypatch):
        """Test that gofannon agents are included in available providers."""
        # Mock the database service at the module level before get_available_providers runs
        mock_db = Mock()
        mock_db.list_all.return_value = [
            {"_id": "my-agent", "agentId": "agent-1"}
        ]
        # Need to provide all required Agent fields
        mock_db.get.return_value = {
            "_id": "agent-1",
            "name": "TestAgent",
            "description": "A test agent",
            "code": "async def run(input_dict, tools):\n    return {}",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "tools": {},
            "gofannon_agents": [],
        }
        
        # We need to patch get_database_service in the dependencies module
        # but get_available_providers calls it internally
        # Let's patch it before calling the function
        original_get_db_service = dependencies_module.get_database_service
        monkeypatch.setattr(dependencies_module, "get_database_service", lambda _: mock_db)

        try:
            providers = get_available_providers()

            assert "gofannon" in providers
            assert "my-agent" in providers["gofannon"]["models"]
        finally:
            # Restore original
            monkeypatch.setattr(dependencies_module, "get_database_service", original_get_db_service)
