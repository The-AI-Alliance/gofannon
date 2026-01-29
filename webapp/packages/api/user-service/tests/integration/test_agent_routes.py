"""Integration tests for agent routes including generate-code endpoint."""
from unittest.mock import Mock, patch, AsyncMock

from fastapi import Request
from fastapi.testclient import TestClient

from app_factory import create_app
from dependencies import get_user_service_dep, get_db
from routes import get_current_user


class FakeUserService:
    """Fake user service that tracks API key calls."""
    def __init__(self):
        self.calls = []
        self.api_keys = {}

    def get_api_keys(self, user_id, user):
        self.calls.append(("get_api_keys", user_id))
        return self.api_keys

    def get_effective_api_key(self, user_id, provider, user):
        self.calls.append(("get_effective_api_key", user_id, provider))
        # Return user-specific key if set, otherwise None (would fall back to env)
        return self.api_keys.get(provider, {}).get("key")


def _build_valid_generate_code_request():
    """Builds a valid request body for the generate-code endpoint."""
    return {
        "description": "Create a simple agent",
        "tools": {},
        "inputSchema": {"type": "object"},
        "outputSchema": {"type": "object"},
        "modelConfig": {
            "provider": "openai",
            "model": "gpt-4",
            "parameters": {"temperature": 0.7}
        }
    }


def test_generate_code_endpoint_passes_user_context():
    """Test that generate-code endpoint correctly passes user context to LLM calls.
    
    This test verifies the bug fix where user_id was defaulting to "anonymous"
    instead of being passed from the authenticated user.
    """
    app = create_app()
    fake_user_service = FakeUserService()
    fake_user_service.api_keys = {
        "openai": {"key": "user-specific-openai-key", "name": "My OpenAI Key"}
    }

    def override_current_user(request: Request):
        user = {
            "uid": "test-user-123",
            "email": "test@example.com",
            "name": "Test User"
        }
        request.state.user = user
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_user_service_dep] = lambda: fake_user_service

    # Mock the agent_factory.generate_agent_code function to capture arguments
    captured_calls = {}

    async def mock_generate_code(request, user_id=None, user_basic_info=None):
        captured_calls["user_id"] = user_id
        captured_calls["user_basic_info"] = user_basic_info
        return {
            "code": "# Generated code",
            "friendlyName": "TestAgent",
            "description": "A test agent",
            "docstring": "Docstring here"
        }

    client = TestClient(app)
    try:
        with patch("agent_factory.generate_agent_code", mock_generate_code):
            response = client.post(
                "/agents/generate-code",
                json=_build_valid_generate_code_request()
            )

        assert response.status_code == 200
        # Verify user context was passed correctly
        assert captured_calls["user_id"] == "test-user-123"
        assert captured_calls["user_basic_info"] == {
            "email": "test@example.com",
            "name": "Test User"
        }
    finally:
        app.dependency_overrides = {}


def test_generate_code_endpoint_user_context_flow_to_llm():
    """Integration test verifying user context flows from route -> agent_factory -> call_llm.
    
    This test mocks call_llm to verify the complete user context propagation chain.
    Verifies that user_id and user_basic_info are correctly passed through.
    """
    app = create_app()
    fake_user_service = FakeUserService()

    def override_current_user(request: Request):
        user = {
            "uid": "integration-user-456",
            "email": "integration@example.com",
            "displayName": "Integration Test User"
        }
        request.state.user = user
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_user_service_dep] = lambda: fake_user_service

    captured_llm_calls = []

    async def mock_call_llm(provider, model, messages, parameters=None, tools=None, 
                           user_service=None, user_id=None, user_basic_info=None, **kwargs):
        captured_llm_calls.append({
            "provider": provider,
            "user_id": user_id,
            "user_basic_info": user_basic_info,
        })
        # Return tuple as expected by generate_agent_code
        return ("# Generated code\ndef example(): pass", None)

    client = TestClient(app)
    try:
        # Patch call_llm at the module level where it's used
        with patch("agent_factory.call_llm", mock_call_llm):
            response = client.post(
                "/agents/generate-code",
                json=_build_valid_generate_code_request()
            )

        assert response.status_code == 200
        # Verify call_llm was invoked (there are 2 calls: code generation and name/doc generation)
        assert len(captured_llm_calls) == 2
        
        # Verify all calls have the correct user context
        for call in captured_llm_calls:
            assert call["user_id"] == "integration-user-456"
            assert call["user_basic_info"] == {
                "email": "integration@example.com",
                "name": "Integration Test User"
            }
    finally:
        app.dependency_overrides = {}


def test_generate_code_endpoint_without_user_defaults_to_anonymous():
    """Test that without authentication, user defaults to anonymous.
    
    This documents the expected behavior when no user is authenticated.
    """
    app = create_app()

    def override_current_user(request: Request):
        # Return minimal user info (no uid)
        user = {"email": "anon@example.com"}
        request.state.user = user
        return user

    app.dependency_overrides[get_current_user] = override_current_user

    captured_calls = {}

    async def mock_generate_code(request, user_id=None, user_basic_info=None):
        captured_calls["user_id"] = user_id
        captured_calls["user_basic_info"] = user_basic_info
        return {
            "code": "# Generated code",
            "friendlyName": "TestAgent",
            "description": "A test agent",
            "docstring": "Docstring here"
        }

    client = TestClient(app)
    try:
        with patch("agent_factory.generate_agent_code", mock_generate_code):
            response = client.post(
                "/agents/generate-code",
                json=_build_valid_generate_code_request()
            )

        assert response.status_code == 200
        # When no uid in user, user_id should be None (will default to "anonymous" in call_llm)
        assert captured_calls["user_id"] is None
        assert captured_calls["user_basic_info"]["email"] == "anon@example.com"
    finally:
        app.dependency_overrides = {}
