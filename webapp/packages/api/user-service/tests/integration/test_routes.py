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


def _override_current_user(request: Request):
    user = {"uid": "user-123", "email": "user@example.com", "auth_mode": "test"}
    request.state.user = user
    return user


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
    app.dependency_overrides[get_current_user] = _override_current_user
    client = TestClient(app)

    try:
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
    finally:
        app.dependency_overrides = {}


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

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = {"uid": "user-123"}
        return await call_next(request)

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
        assert fake_logger.log.call_args.kwargs["user_id"] == "user-123"
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
    app.dependency_overrides[get_current_user] = _override_current_user

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


def test_user_routes_reject_missing_session(monkeypatch):
    app = create_app()
    client = TestClient(app)

    for app_env in ("local", "dev", "test", "production", "firebase"):
        monkeypatch.setattr(settings, "APP_ENV", app_env)
        response = client.get("/users/me")
        assert response.status_code == 401


def test_expired_session_cookie_returns_401(monkeypatch):
    import routes as routes_module

    async def missing_session(request: Request, sid: str):
        return None

    monkeypatch.setattr(routes_module, "_verify_session_cookie", missing_session)

    app = create_app()
    client = TestClient(app)
    response = client.get("/users/me", cookies={"gofannon_sid": "expired"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Session expired or invalid"


# backend half of the session-expiry UX. The X-Auth-Reason header
# distinguishes expired-cookie cases (the SPA should pop the AuthExpiryModal)
# from never-authenticated cases (handled by route guards / redirects). The
# frontend's services/fetchInterceptor.js reads this header to decide whether
# to fire the auth:session-expired event.

def test_expired_session_emits_x_auth_reason_session_expired(monkeypatch):
    """Expired/invalid cookie -> 401 + X-Auth-Reason: session_expired."""
    import routes as routes_module

    async def missing_session(request: Request, sid: str):
        return None

    monkeypatch.setattr(routes_module, "_verify_session_cookie", missing_session)

    app = create_app()
    client = TestClient(app)
    response = client.get("/users/me", cookies={"gofannon_sid": "expired"})

    assert response.status_code == 401
    assert response.headers.get("X-Auth-Reason") == "session_expired"


def test_no_cookie_emits_x_auth_reason_not_authenticated(monkeypatch):
    """No cookie at all -> 401 + X-Auth-Reason: not_authenticated.

    Different reason from session_expired so the SPA can render
    'sign in' vs 'sign in again' messaging appropriately.
    """
    monkeypatch.setattr(settings, "APP_ENV", "production")

    app = create_app()
    client = TestClient(app)
    response = client.get("/users/me")  # no cookie

    assert response.status_code == 401
    assert response.headers.get("X-Auth-Reason") == "not_authenticated"


def test_valid_session_no_x_auth_reason_header(monkeypatch):
    """Valid session -> no X-Auth-Reason header on the success response.

    The header is a 401-only signal. Adding it to 2xx responses would
    confuse the interceptor and could fire spurious expiry modals.
    """
    import routes as routes_module

    async def valid_session(request: Request, sid: str):
        return {"uid": "user-1", "email": "u@example.com", "auth_mode": "session"}

    monkeypatch.setattr(routes_module, "_verify_session_cookie", valid_session)

    app = create_app()
    client = TestClient(app)
    response = client.get("/users/me", cookies={"gofannon_sid": "valid"})

    assert response.status_code == 200
    assert "X-Auth-Reason" not in response.headers


def test_dev_stub_picker_returns_404_outside_dev_env(monkeypatch):
    auth_config = {
        "providers": [
            {
                "type": "dev_stub",
                "enabled": True,
                "config": {
                    "users": [
                        {
                            "uid": "alice",
                            "display_name": "Alice Dev",
                            "email": "alice@example.com",
                            "workspaces": [],
                        }
                    ]
                },
            }
        ],
        "site_admins": [],
        "session_ttl_hours": 24,
        "workspace_refresh_minutes": 15,
        "legacy_firebase_enabled": True,
    }
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AUTH_CONFIG", auth_config)

    app = create_app()
    client = TestClient(app)
    response = client.get(
        "/auth/dev-stub-picker",
        params={
            "state": "state",
            "redirect_uri": "http://test/auth/callback/dev_stub",
            "users": "alice",
        },
    )

    assert response.status_code == 404


def test_get_current_user_short_circuits_on_middleware_populated_user(monkeypatch):
    """When the ObservabilityMiddleware (PR-35) has already resolved the
    session cookie into ``request.state.user``, ``get_current_user`` reuses
    that dict instead of re-running the session lookup. Guards against a
    double DB roundtrip on every authenticated request."""
    import routes as routes_module

    verify_call_count = {"n": 0}

    async def counting_verify(request, sid):
        verify_call_count["n"] += 1
        # Return the same shape _verify_session_cookie would.
        user = {
            "uid": "session-user",
            "email": "session@example.com",
            "auth_mode": "session",
        }
        request.state.user = user
        return user

    monkeypatch.setattr(routes_module, "_verify_session_cookie", counting_verify)

    app = create_app()

    @app.middleware("http")
    async def fake_obs_middleware(request: Request, call_next):
        # Simulate what ObservabilityMiddleware does in PR-35: pre-populate
        # request.state.user from a session lookup, before routes run.
        request.state.user = {
            "uid": "session-user",
            "email": "session@example.com",
            "auth_mode": "session",
        }
        return await call_next(request)

    client = TestClient(app)
    response = client.get("/users/me", cookies={"gofannon_sid": "doesnt-matter"})

    # The endpoint protected by get_current_user should respond successfully
    # and _verify_session_cookie must NOT have been called -- the
    # short-circuit handed back the middleware-populated user.
    assert response.status_code in (200, 404)  # 404 if user-service mock missing; either way auth was bypassed
    assert verify_call_count["n"] == 0, (
        "get_current_user should have reused the middleware-populated user "
        "instead of re-verifying the session cookie"
    )
