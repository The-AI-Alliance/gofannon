"""Unit tests for route configuration resolution."""
from __future__ import annotations

import sys
import types

import pytest
from fastapi import APIRouter

from config.routes_config import RouterConfig, resolve_router_configs


pytestmark = pytest.mark.unit


def test_resolve_router_configs_returns_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("APP_ROUTER_CONFIG", raising=False)
    default_router = APIRouter()
    default_config = RouterConfig(router=default_router, prefix="/default")

    resolved = resolve_router_configs([default_config])

    assert resolved == [default_config]


def test_resolve_router_configs_ignores_empty_configs(monkeypatch):
    default_router = APIRouter()
    default_config = RouterConfig(router=default_router, prefix="/default")

    dummy_module = types.ModuleType("empty_router_config")
    dummy_module.ROUTER_CONFIGS = []
    monkeypatch.setitem(sys.modules, "empty_router_config", dummy_module)
    monkeypatch.setenv("APP_ROUTER_CONFIG", "empty_router_config")

    resolved = resolve_router_configs([default_config])

    assert resolved == [default_config]
