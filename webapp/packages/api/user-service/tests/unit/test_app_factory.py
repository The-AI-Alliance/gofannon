"""Unit tests for app factory helpers."""
from __future__ import annotations

import sys
import types

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    route_paths = {route.path for route in app.router.routes}
    assert "/dummy/ping" in route_paths
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
    assert cors_options["allow_origins"] == ["*"]
    assert cors_options["allow_methods"] == ["*"]
    assert cors_options["allow_headers"] == ["*"]
    assert cors_options["allow_credentials"] is True
