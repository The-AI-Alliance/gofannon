import os
import time
from unittest.mock import Mock

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

import dependencies as dependencies_module
from app_factory import create_app
from config.provider_config import PROVIDER_CONFIG
from routes import get_current_user
from services.database_service.memory import MemoryDBService


pytestmark = pytest.mark.integration


def _override_current_user(request: Request):
    """/chat requires a session. These tests exercise the provider round-trip,
    not authentication, so stand in an authenticated user the way the other
    integration tests do."""
    user = {"uid": "user-123", "email": "user@example.com", "auth_mode": "test"}
    request.state.user = user
    return user


def _wait_for_ticket(client: TestClient, ticket_id: str, attempts: int = 5) -> dict:
    response_data = None
    for _ in range(attempts):
        response = client.get(f"/chat/{ticket_id}")
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "completed":
                return response_data
        time.sleep(0.01)
    return response_data or {}


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("openai", "gpt-5"),
        ("bedrock", "us.anthropic.claude-opus-4-5-v1:0"),
        ("gemini", "gemini-2.5-pro"),
    ],
)
def test_chat_returns_thoughts_for_provider(monkeypatch, provider, model):
    api_key_env_var = PROVIDER_CONFIG.get(provider, {}).get("api_key_env_var")
    if api_key_env_var and not os.getenv(api_key_env_var):
        pytest.skip(f"Missing {api_key_env_var} for {provider} integration test.")

    memory_db = MemoryDBService()
    fake_logger = Mock()
    fake_logger.log = Mock()
    fake_logger.log_exception = Mock()

    monkeypatch.setattr(dependencies_module, "get_database_service", lambda settings: memory_db)
    monkeypatch.setattr(dependencies_module, "get_observability_service", lambda: fake_logger)

    app = create_app()
    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        client = TestClient(app)

        response = client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": provider,
                "model": model,
                "parameters": {"reasoning_effort": "low"},
            },
        )
        assert response.status_code == 200
        ticket_id = response.json()["ticket_id"]

        ticket_data = _wait_for_ticket(client, ticket_id)

        assert ticket_data.get("status") == "completed", ticket_data
        thoughts = (ticket_data.get("result") or {}).get("thoughts")
        assert thoughts, ticket_data
    finally:
        app.dependency_overrides = {}
