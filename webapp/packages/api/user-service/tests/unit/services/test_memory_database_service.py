"""Unit tests for in-memory database service."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.database_service.memory import MemoryDBService


pytestmark = pytest.mark.unit


def test_memory_db_crud_flow():
    service = MemoryDBService()

    result = service.save("agents", "agent-1", {"name": "agent"})

    assert result == {"id": "agent-1", "rev": "memory-rev"}
    assert service.get("agents", "agent-1") == {"name": "agent"}
    assert service.list_all("agents") == [{"name": "agent"}]

    service.delete("agents", "agent-1")

    assert service.list_all("agents") == []


def test_memory_db_missing_get_raises():
    service = MemoryDBService()

    with pytest.raises(HTTPException) as exc_info:
        service.get("agents", "missing")

    assert exc_info.value.status_code == 404
    assert "missing" in exc_info.value.detail


def test_memory_db_missing_delete_raises():
    service = MemoryDBService()

    with pytest.raises(HTTPException) as exc_info:
        service.delete("agents", "missing")

    assert exc_info.value.status_code == 404
    assert "missing" in exc_info.value.detail
