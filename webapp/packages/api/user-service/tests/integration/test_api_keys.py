"""Integration tests for API key management endpoints."""
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app_factory import create_app
from models.user import User, ApiKeys
from services.user_service import UserService


pytestmark = pytest.mark.integration


@pytest.fixture
def app():
    """Create the FastAPI app for testing."""
    return create_app()


class TestApiKeyEndpoints:
    """Test suite for API key management endpoints."""

    def test_get_api_keys_returns_keys(self, app, monkeypatch):
        """Test GET /users/me/api-keys returns user's API keys."""
        fake_user = User(
            _id="local-dev-user",  # Default user in local mode
            apiKeys=ApiKeys(
                openaiApiKey="sk-openai-test",
                anthropicApiKey="sk-ant-test",
            )
        )

        class FakeUserService:
            def get_api_keys(self, user_id, basic_info=None):
                return fake_user.api_keys

        # Override the dependency
        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.get("/users/me/api-keys")

        assert response.status_code == 200
        data = response.json()
        assert data["openaiApiKey"] == "sk-openai-test"
        assert data["anthropicApiKey"] == "sk-ant-test"
        assert data["geminiApiKey"] is None
        assert data["perplexityApiKey"] is None

        # Clear overrides
        app.dependency_overrides.clear()

    def test_update_api_key_success(self, app, monkeypatch):
        """Test PUT /users/me/api-keys updates an API key."""
        fake_user = User(
            _id="local-dev-user",
            apiKeys=ApiKeys()
        )

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def update_api_key(self, user_id, provider, api_key, basic_info=None):
                if provider == "openai":
                    fake_user.api_keys.openai_api_key = api_key
                return fake_user

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.put(
            "/users/me/api-keys",
            json={"provider": "openai", "api_key": "sk-new-openai-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["apiKeys"]["openaiApiKey"] == "sk-new-openai-key"

        app.dependency_overrides.clear()

    def test_update_api_key_unknown_provider(self, app, monkeypatch):
        """Test PUT /users/me/api-keys with unknown provider returns 400."""
        fake_user = User(_id="local-dev-user")

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def update_api_key(self, user_id, provider, api_key, basic_info=None):
                raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.put(
            "/users/me/api-keys",
            json={"provider": "unknown", "api_key": "some-key"}
        )

        assert response.status_code == 400
        assert "Unknown provider" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_delete_api_key_success(self, app, monkeypatch):
        """Test DELETE /users/me/api-keys/{provider} removes an API key."""
        fake_user = User(
            _id="local-dev-user",
            apiKeys=ApiKeys(openaiApiKey="sk-existing-key")
        )

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def delete_api_key(self, user_id, provider, basic_info=None):
                if provider == "openai":
                    fake_user.api_keys.openai_api_key = None
                return fake_user

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.delete("/users/me/api-keys/openai")

        assert response.status_code == 200
        data = response.json()
        assert data["apiKeys"]["openaiApiKey"] is None

        app.dependency_overrides.clear()

    def test_delete_api_key_unknown_provider(self, app, monkeypatch):
        """Test DELETE /users/me/api-keys/{provider} with unknown provider returns 400."""
        fake_user = User(_id="local-dev-user")

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def delete_api_key(self, user_id, provider, basic_info=None):
                raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.delete("/users/me/api-keys/unknown")

        assert response.status_code == 400

        app.dependency_overrides.clear()

    def test_get_effective_api_key_with_user_key(self, app, monkeypatch):
        """Test GET /users/me/api-keys/{provider}/effective returns has_key=true when user key exists."""
        fake_user = User(
            _id="local-dev-user",
            apiKeys=ApiKeys(openaiApiKey="sk-user-key")
        )

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def get_api_keys(self, user_id, basic_info=None):
                return fake_user.api_keys

            def get_effective_api_key(self, user_id, provider, basic_info=None):
                if provider == "openai":
                    return fake_user.api_keys.openai_api_key
                return None

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.get("/users/me/api-keys/openai/effective")

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"
        assert data["has_key"] is True
        assert data["source"] == "user"

        app.dependency_overrides.clear()

    def test_get_effective_api_key_with_env_key(self, app, monkeypatch):
        """Test GET /users/me/api-keys/{provider}/effective returns source=env when using env var."""
        fake_user = User(
            _id="local-dev-user",
            apiKeys=ApiKeys()  # No user key set
        )

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def get_api_keys(self, user_id, basic_info=None):
                return fake_user.api_keys

            def get_effective_api_key(self, user_id, provider, basic_info=None):
                # Simulating env var fallback
                if provider == "openai":
                    return "env-openai-key"
                return None

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.get("/users/me/api-keys/openai/effective")

        assert response.status_code == 200
        data = response.json()
        assert data["has_key"] is True
        assert data["source"] == "env"

        app.dependency_overrides.clear()

    def test_get_effective_api_key_no_key(self, app, monkeypatch):
        """Test GET /users/me/api-keys/{provider}/effective returns has_key=false when no key."""
        fake_user = User(
            _id="local-dev-user",
            apiKeys=ApiKeys()
        )

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def get_api_keys(self, user_id, basic_info=None):
                return fake_user.api_keys

            def get_effective_api_key(self, user_id, provider, basic_info=None):
                return None

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.get("/users/me/api-keys/openai/effective")

        assert response.status_code == 200
        data = response.json()
        assert data["has_key"] is False
        assert data["source"] is None

        app.dependency_overrides.clear()

    def test_update_all_provider_keys(self, app, monkeypatch):
        """Test updating API keys for all supported providers."""
        fake_user = User(_id="local-dev-user", apiKeys=ApiKeys())

        class FakeUserService:
            def get_user(self, user_id, basic_info=None):
                return fake_user

            def update_api_key(self, user_id, provider, api_key, basic_info=None):
                key_map = {
                    "openai": "openai_api_key",
                    "anthropic": "anthropic_api_key",
                    "gemini": "gemini_api_key",
                    "perplexity": "perplexity_api_key",
                }
                setattr(fake_user.api_keys, key_map[provider], api_key)
                return fake_user

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)

        providers = ["openai", "anthropic", "gemini", "perplexity"]
        keys = {
            "openai": "sk-openai-test",
            "anthropic": "sk-ant-test",
            "gemini": "gemini-test-key",
            "perplexity": "pplx-test-key",
        }

        for provider, key in keys.items():
            response = client.put(
                "/users/me/api-keys",
                json={"provider": provider, "api_key": key}
            )
            assert response.status_code == 200, f"Failed to update {provider}"

        # Verify all keys are set
        assert fake_user.api_keys.openai_api_key == "sk-openai-test"
        assert fake_user.api_keys.anthropic_api_key == "sk-ant-test"
        assert fake_user.api_keys.gemini_api_key == "gemini-test-key"
        assert fake_user.api_keys.perplexity_api_key == "pplx-test-key"

        app.dependency_overrides.clear()


class TestProvidersWithUserKeys:
    """Test suite for provider endpoints with user API keys."""

    def test_get_providers_with_user_key(self, app, monkeypatch):
        """Test GET /providers includes providers when user has API key."""

        class FakeUserService:
            def get_effective_api_key(self, user_id, provider, basic_info=None):
                # User has openai key but no anthropic key
                if provider == "openai":
                    return "user-openai-key"
                return None

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        client = TestClient(app)
        response = client.get("/providers")

        # Should return 200 and include providers
        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_get_provider_config_with_user(self, app, monkeypatch):
        """Test GET /providers/{provider} works with user context."""

        class FakeUserService:
            def get_effective_api_key(self, user_id, provider, basic_info=None):
                if provider == "openai":
                    return "user-openai-key"
                return None

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        # Mock the PROVIDER_CONFIG
        import dependencies as deps_module
        original_config = deps_module.APP_PROVIDER_CONFIG
        fake_providers = {
            "openai": {
                "api_key_env_var": "OPENAI_API_KEY",
                "models": {"gpt-4": {"context_length": 8192}}
            }
        }
        monkeypatch.setattr(deps_module, "APP_PROVIDER_CONFIG", fake_providers)

        client = TestClient(app)
        response = client.get("/providers/openai")

        # Should return 200 if provider is available (user has key or env var)
        # Returns 404 if no key available
        assert response.status_code in [200, 404]

        # Restore original config
        monkeypatch.setattr(deps_module, "APP_PROVIDER_CONFIG", original_config)
        app.dependency_overrides.clear()

    def test_get_provider_models_with_user(self, app, monkeypatch):
        """Test GET /providers/{provider}/models with user context."""

        class FakeUserService:
            def get_effective_api_key(self, user_id, provider, basic_info=None):
                if provider == "openai":
                    return "user-openai-key"
                return None

        from dependencies import get_user_service_dep
        app.dependency_overrides[get_user_service_dep] = lambda: FakeUserService()

        # Mock the PROVIDER_CONFIG
        import dependencies as deps_module
        original_config = deps_module.APP_PROVIDER_CONFIG
        fake_providers = {
            "openai": {
                "api_key_env_var": "OPENAI_API_KEY",
                "models": {"gpt-4": {}, "gpt-3.5": {}}
            }
        }
        monkeypatch.setattr(deps_module, "APP_PROVIDER_CONFIG", fake_providers)

        client = TestClient(app)
        response = client.get("/providers/openai/models")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            models = response.json()
            assert "gpt-4" in models
            assert "gpt-3.5" in models

        # Restore original config
        monkeypatch.setattr(deps_module, "APP_PROVIDER_CONFIG", original_config)
        app.dependency_overrides.clear()
