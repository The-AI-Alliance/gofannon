from unittest.mock import Mock

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app_factory import create_app
from config import settings
from dependencies import get_db, get_logger, get_user_service_dep
from routes import get_current_user


def _build_user_response(
    user_id: str = "user-123",
    monthly_allowance: float = 100.0,
    allowance_reset_date: float = 0.0,
    spend_remaining: float = 100.0,
):
    return {
        "_id": user_id,
        "basicInfo": {"email": "user@example.com"},
        "usageInfo": {
            "monthlyAllowance": monthly_allowance,
            "allowanceResetDate": allowance_reset_date,
            "spendRemaining": spend_remaining,
            "usage": [],
        },
    }


class FakeUserService:
    def __init__(self):
        self.calls = []

    def get_user(self, user_id, user):
        self.calls.append(("get_user", user_id))
        return _build_user_response(user_id=user_id)

    def set_monthly_allowance(self, user_id, monthly_allowance, user):
        self.calls.append(("set_monthly_allowance", user_id, monthly_allowance))
        return _build_user_response(user_id=user_id, monthly_allowance=monthly_allowance)

    def set_reset_date(self, user_id, allowance_reset_date, user):
        self.calls.append(("set_reset_date", user_id, allowance_reset_date))
        return _build_user_response(user_id=user_id, allowance_reset_date=allowance_reset_date)

    def update_spend_remaining(self, user_id, spend_remaining, user):
        self.calls.append(("update_spend_remaining", user_id, spend_remaining))
        return _build_user_response(user_id=user_id, spend_remaining=spend_remaining)

    def add_usage(self, user_id, response_cost, metadata, user):
        self.calls.append(("add_usage", user_id, response_cost, metadata))
        return _build_user_response(user_id=user_id, spend_remaining=92.5)

    def list_users(self):
        self.calls.append(("list_users",))
        return [_build_user_response(user_id="user-123"), _build_user_response(user_id="user-456")]

    def update_user_usage_info(self, user_id, monthly_allowance, allowance_reset_date, spend_remaining):
        self.calls.append(("update_user_usage_info", user_id, monthly_allowance, allowance_reset_date, spend_remaining))
        return _build_user_response(
            user_id=user_id,
            monthly_allowance=monthly_allowance or 100.0,
            allowance_reset_date=allowance_reset_date or 0.0,
            spend_remaining=spend_remaining or 50.0,
        )


def test_provider_routes_return_data_and_404(monkeypatch):
    import routes as routes_module

    fake_providers = {
        "openai": {
            "models": {
                "gpt-4": {"context_length": 8192},
            }
        }
    }

    monkeypatch.setattr(routes_module, "get_available_providers", lambda user_id=None, user_basic_info=None: fake_providers)

    app = create_app()
    client = TestClient(app)

    assert client.get("/providers").json() == fake_providers

    response = client.get("/providers/openai")
    assert response.status_code == 200
    assert response.json() == fake_providers["openai"]

    assert client.get("/providers/missing").status_code == 404

    response = client.get("/providers/openai/models")
    assert response.status_code == 200
    assert response.json() == ["gpt-4"]

    assert client.get("/providers/missing/models").status_code == 404

    response = client.get("/providers/openai/models/gpt-4")
    assert response.status_code == 200
    assert response.json() == {"context_length": 8192}

    assert client.get("/providers/openai/models/unknown").status_code == 404


def test_user_routes_use_dependency_overrides():
    app = create_app()
    fake_user_service = FakeUserService()

    def override_current_user(request: Request):
        user = {"uid": "user-123", "email": "user@example.com"}
        request.state.user = user
        return user

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_user_service_dep] = lambda: fake_user_service

    client = TestClient(app)
    try:
        response = client.get("/users/me")
        assert response.status_code == 200
        assert response.json()["_id"] == "user-123"

        response = client.put("/users/me/monthly-allowance", json={"monthlyAllowance": 42.0})
        assert response.status_code == 200
        assert response.json()["usageInfo"]["monthlyAllowance"] == 42.0

        response = client.put("/users/me/allowance-reset-date", json={"allowanceResetDate": 10.0})
        assert response.status_code == 200
        assert response.json()["usageInfo"]["allowanceResetDate"] == 10.0

        response = client.put("/users/me/spend-remaining", json={"spendRemaining": 77.5})
        assert response.status_code == 200
        assert response.json()["usageInfo"]["spendRemaining"] == 77.5

        response = client.post(
            "/users/me/usage",
            json={"responseCost": 7.5, "metadata": {"model": "gpt-4"}},
        )
        assert response.status_code == 200
        assert response.json()["usageInfo"]["spendRemaining"] == 92.5
    finally:
        app.dependency_overrides = {}


def test_admin_routes_require_password(monkeypatch):
    app = create_app()
    fake_user_service = FakeUserService()
    app.dependency_overrides[get_user_service_dep] = lambda: fake_user_service
    client = TestClient(app)

    try:
        monkeypatch.setattr(settings, "ADMIN_PANEL_ENABLED", False)
        response = client.get("/admin/users")
        assert response.status_code == 403

        monkeypatch.setattr(settings, "ADMIN_PANEL_ENABLED", True)
        monkeypatch.setattr(settings, "ADMIN_PANEL_PASSWORD", "secret")
        response = client.get("/admin/users", headers={"X-Admin-Password": "wrong"})
        assert response.status_code == 401

        response = client.get("/admin/users", headers={"X-Admin-Password": "secret"})
        assert response.status_code == 200
        assert len(response.json()) == 2

        response = client.put(
            "/admin/users/user-123",
            json={"monthlyAllowance": 150.0, "allowanceResetDate": 30.0, "spendRemaining": 80.0},
            headers={"X-Admin-Password": "secret"},
        )
        assert response.status_code == 200
        assert response.json()["usageInfo"]["monthlyAllowance"] == 150.0
    finally:
        app.dependency_overrides = {}


def test_log_client_enriches_metadata_with_dependency_overrides():
    app = create_app()
    fake_logger = Mock()
    fake_logger.log = Mock()
    fake_user_service = FakeUserService()
    fake_db = Mock()

    def override_current_user(request: Request):
        user = {"uid": "user-123"}
        request.state.user = user
        return user

    app.dependency_overrides[get_logger] = lambda: fake_logger
    app.dependency_overrides[get_user_service_dep] = lambda: fake_user_service
    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    try:
        response = client.post(
            "/log/client",
            json={
                "eventType": "client_event",
                "message": "hello",
                "level": "INFO",
                "metadata": {"extra": "value"},
            },
            headers={"User-Agent": "TestAgent/1.0"},
        )
        assert response.status_code == 202

        fake_logger.log.assert_called_once()
        metadata = fake_logger.log.call_args.kwargs["metadata"]
        assert metadata["extra"] == "value"
        assert metadata["client_host"] == "testclient"
        assert metadata["user_agent"] == "TestAgent/1.0"
    finally:
        app.dependency_overrides = {}


def test_session_config_routes_create_read_delete():
    app = create_app()
    storage = {}

    class FakeDb:
        def get(self, collection, key):
            if collection != "sessions" or key not in storage:
                raise HTTPException(status_code=404, detail="Not found")
            return storage[key]

        def save(self, collection, key, data):
            storage[key] = data
            return {"rev": "1-test"}

        def delete(self, collection, key):
            storage.pop(key, None)

    fake_db = FakeDb()
    app.dependency_overrides[get_db] = lambda: fake_db

    client = TestClient(app)
    try:
        payload = {
            "provider": "openai",
            "model": "gpt-4.1-nano",
            "parameters": {"temperature": 0.2},
        }
        response = client.post("/sessions/session-1/config", json=payload)
        assert response.status_code == 200
        assert response.json()["session_id"] == "session-1"

        response = client.get("/sessions/session-1/config")
        assert response.status_code == 200
        config_payload = response.json()
        assert config_payload["provider"] == payload["provider"]
        assert config_payload["model"] == payload["model"]
        assert config_payload["parameters"] == payload["parameters"]

        response = client.delete("/sessions/session-1")
        assert response.status_code == 200
        assert response.json()["message"] == "Session deleted"
    finally:
        app.dependency_overrides = {}
