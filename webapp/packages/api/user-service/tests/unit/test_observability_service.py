import asyncio
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
