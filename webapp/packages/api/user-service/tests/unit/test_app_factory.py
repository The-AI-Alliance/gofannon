"""Unit tests for app factory helpers."""
from __future__ import annotations

import sys
import types

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app_factory import _configure_cors, create_app
from services.observability_service import ObservabilityMiddleware


pytestmark = pytest.mark.unit


def test_create_app_includes_router_and_observability(monkeypatch):
    dummy_router = APIRouter(prefix="/dummy")

    @dummy_router.get("/ping")
    def _ping():
        return {"ok": True}

    dummy_module = types.ModuleType("routes")
    dummy_module.router = dummy_router
    monkeypatch.setitem(sys.modules, "routes", dummy_module)

    app = create_app()

    # Verify the router is wired up by calling the route, rather than
    # introspecting app.router.routes internals -- Starlette 1.3 nests
    # included routers inside a container object instead of flattening
    # their paths into the top-level route list, so structural
    # introspection is version-fragile. Behavior is not.
    client = TestClient(app)
    response = client.get("/dummy/ping")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    assert any(middleware.cls is ObservabilityMiddleware for middleware in app.user_middleware)


def test_configure_cors_adds_middleware():
    app = FastAPI()

    _configure_cors(app)

    cors_middleware = [
        middleware
        for middleware in app.user_middleware
        if middleware.cls is CORSMiddleware
    ]
    assert cors_middleware, "Expected CORSMiddleware to be configured"

    cors_options = cors_middleware[0].options
    assert cors_options["allow_origins"] == ["http://localhost:3000"]
    assert cors_options["allow_methods"] == ["*"]
    assert cors_options["allow_headers"] == ["*"]
    assert cors_options["allow_credentials"] is True