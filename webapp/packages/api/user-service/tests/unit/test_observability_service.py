import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from services.observability_service import (
    ObservabilityMiddleware,
    ObservabilityService,
    get_sanitized_request_data,
)


def _make_request(headers=None, method="POST", path="/test", query_string=b""):
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


def test_get_sanitized_request_data_redacts_sensitive_headers_and_body():
    headers = [
        (b"authorization", b"Bearer secret"),
        (b"cookie", b"sessionid=secret"),
        (b"x-api-key", b"secret-key"),
        (b"content-type", b"application/json"),
    ]
    request = _make_request(headers=headers, query_string=b"foo=bar")

    data = get_sanitized_request_data(request)

    assert data["method"] == "POST"
    assert data["path"] == "/test"
    assert data["query_params"] == "foo=bar"
    assert data["client_host"] == "127.0.0.1"
    assert "authorization" not in {key.lower() for key in data["headers"]}
    assert "cookie" not in {key.lower() for key in data["headers"]}
    assert "x-api-key" not in {key.lower() for key in data["headers"]}
    assert data["headers"]["content-type"] == "application/json"
    assert "body" not in data


@pytest.mark.asyncio
async def test_observability_log_formats_payload_and_metadata(monkeypatch):
    provider = AsyncMock()
    tasks = []
    original_create_task = asyncio.create_task

    def _create_task(coro):
        task = original_create_task(coro)
        tasks.append(task)
        return task

    monkeypatch.setattr(asyncio, "create_task", _create_task)
    monkeypatch.setattr(ObservabilityService, "_initialize_providers", lambda self: None)

    service = ObservabilityService()
    service.providers = [provider]

    service.log(
        event_type="audit",
        message="hello",
        level="info",
        service="user-service",
        user_id="user-123",
        metadata={"request_id": "req-1"},
    )

    await asyncio.gather(*tasks)

    provider.log.assert_awaited_once()
    payload = provider.log.await_args.args[0]
    assert payload["level"] == "INFO"
    assert payload["eventType"] == "audit"
    assert payload["service"] == "user-service"
    assert payload["userId"] == "user-123"
    assert payload["message"] == "hello"
    assert payload["metadata"] == {"request_id": "req-1"}
    assert "timestamp" in payload


def test_observability_middleware_logs_request_and_response(monkeypatch):
    mock_logger = Mock()
    mock_logger.log = Mock()
    monkeypatch.setattr(
        "services.observability_service.get_observability_service",
        lambda: mock_logger,
    )

    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/ping")
    async def ping(request: Request):
        request.state.user = {"uid": "user-456"}
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ping", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 200
    assert mock_logger.log.call_count == 2

    start_call = mock_logger.log.call_args_list[0].kwargs
    end_call = mock_logger.log.call_args_list[1].kwargs

    assert start_call["event_type"] == "api_request_start"
    assert start_call["user_id"] == "user-456"
    assert start_call["metadata"]["path"] == "/ping"
    assert start_call["metadata"]["method"] == "GET"
    assert "authorization" not in {
        key.lower() for key in start_call["metadata"]["headers"]
    }

    assert end_call["event_type"] == "api_request_end"
    assert end_call["user_id"] == "user-456"
    assert end_call["metadata"]["status_code"] == 200
    assert end_call["metadata"]["path"] == "/ping"
    assert end_call["metadata"]["method"] == "GET"
    assert "process_time" in end_call["metadata"]


def test_observability_middleware_resolves_session_cookie(monkeypatch):
    mock_logger = Mock()
    mock_logger.log = Mock()
    monkeypatch.setattr(
        "services.observability_service.get_observability_service",
        lambda: mock_logger,
    )

    session = SimpleNamespace(
        user_uid="session-user",
        email="user@example.com",
        display_name="Session User",
        provider_type="dev_stub",
        workspaces=[],
        is_site_admin=False,
    )

    class FakeSessionService:
        async def get_by_id(self, sid):
            assert sid == "sid-123"
            return session

    monkeypatch.setattr(
        "services.database_service.get_database_service",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        "services.session_service.get_session_service",
        lambda _db: FakeSessionService(),
    )

    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)

    @app.post("/public")
    async def public_endpoint(request: Request):
        return {"user": request.state.user["uid"]}

    client = TestClient(app)
    response = client.post("/public", cookies={"gofannon_sid": "sid-123"})

    assert response.status_code == 200
    assert response.json() == {"user": "session-user"}

    start_call = mock_logger.log.call_args_list[0].kwargs
    end_call = mock_logger.log.call_args_list[1].kwargs
    assert start_call["user_id"] == "session-user"
    assert end_call["user_id"] == "session-user"


def test_observability_middleware_uses_anonymous_without_user(monkeypatch):
    mock_logger = Mock()
    mock_logger.log = Mock()
    monkeypatch.setattr(
        "services.observability_service.get_observability_service",
        lambda: mock_logger,
    )

    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/public")
    async def public_endpoint():
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/public")

    assert response.status_code == 200
    start_call = mock_logger.log.call_args_list[0].kwargs
    end_call = mock_logger.log.call_args_list[1].kwargs
    assert start_call["user_id"] == "anonymous"
    assert end_call["user_id"] == "anonymous"


def test_observability_middleware_logs_breadcrumb_on_session_lookup_failure(monkeypatch, caplog):
    """When the session lookup raises, the middleware must downgrade to
    anonymous logging WITHOUT failing the request, but should leave a
    debug-level breadcrumb so an operator can find out it happened."""
    import logging

    mock_logger = Mock()
    mock_logger.log = Mock()
    monkeypatch.setattr(
        "services.observability_service.get_observability_service",
        lambda: mock_logger,
    )

    class FlakySessionService:
        async def get_by_id(self, sid):
            raise RuntimeError("simulated DB outage")

    monkeypatch.setattr(
        "services.database_service.get_database_service",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        "services.session_service.get_session_service",
        lambda _db: FlakySessionService(),
    )

    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)

    @app.get("/public")
    async def public_endpoint(request: Request):
        # Request must succeed regardless of the session-service explosion.
        return {"user": getattr(request.state, "user", None)}

    caplog.set_level(logging.DEBUG, logger="services.observability_service")
    client = TestClient(app)
    response = client.get("/public", cookies={"gofannon_sid": "sid-boom"})

    assert response.status_code == 200
    assert response.json() == {"user": None}

    # Anonymous user_id should still appear in the logs.
    start_call = mock_logger.log.call_args_list[0].kwargs
    assert start_call["user_id"] == "anonymous"

    # A breadcrumb at DEBUG level must have been emitted with the exception.
    breadcrumbs = [
        rec for rec in caplog.records
        if "Session lookup failed in ObservabilityMiddleware" in rec.getMessage()
    ]
    assert len(breadcrumbs) == 1
    assert "simulated DB outage" in breadcrumbs[0].getMessage()
