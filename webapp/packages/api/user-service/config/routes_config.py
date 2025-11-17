"""Route configuration for FastAPI app.

This file defines how route registrars are located so that extension
repositories can add new API endpoints by providing additional registrars
without modifying the FastAPI initialization logic.
"""
import json
import os
from importlib import import_module
from typing import Callable, Iterable, List

DEFAULT_ROUTE_REGISTRARS: List[str] = ["main:register_builtin_routes"]


def _parse_registrar_list(raw_value) -> List[str]:
    if raw_value is None:
        return []

    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                return [entry for entry in parsed if isinstance(entry, str)]
        except json.JSONDecodeError:
            return []

    if isinstance(raw_value, Iterable):
        return [entry for entry in raw_value if isinstance(entry, str)]

    return []


def _resolve_registrar(import_path: str) -> Callable:
    """Load a registrar from a string like ``module:function``."""
    if ":" not in import_path:
        raise ValueError(f"Invalid registrar path '{import_path}'. Expected format module:function")

    module_name, func_name = import_path.split(":", 1)
    module = import_module(module_name)
    registrar = getattr(module, func_name)
    if not callable(registrar):
        raise ValueError(f"Registrar '{import_path}' is not callable")
    return registrar


def load_route_registrars() -> List[Callable]:
    env_override = _parse_registrar_list(os.getenv("GOFANNON_API_ROUTE_REGISTRARS"))
    configured_registrars = []

    for registrar_path in [*DEFAULT_ROUTE_REGISTRARS, *env_override]:
        try:
            registrar_callable = _resolve_registrar(registrar_path)
            configured_registrars.append(registrar_callable)
        except Exception as error:  # pragma: no cover - defensive logging only
            print(f"Failed to load route registrar '{registrar_path}': {error}")

    return configured_registrars
