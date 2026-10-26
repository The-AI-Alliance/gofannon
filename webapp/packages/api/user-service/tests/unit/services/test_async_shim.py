"""Unit tests for AsyncDatabaseService."""
import asyncio
from unittest.mock import MagicMock

import pytest

from services.database_service.async_shim import AsyncDatabaseService


@pytest.mark.asyncio
async def test_async_get_delegates_to_sync():
    sync = MagicMock()
    sync.get.return_value = {"_id": "abc", "name": "test"}
    async_db = AsyncDatabaseService(sync)

    result = await async_db.get("agents", "abc")

    assert result == {"_id": "abc", "name": "test"}
    sync.get.assert_called_once_with("agents", "abc")


@pytest.mark.asyncio
async def test_async_save_delegates_to_sync():
    sync = MagicMock()
    sync.save.return_value = {"ok": True, "id": "abc", "rev": "1-foo"}
    async_db = AsyncDatabaseService(sync)

    result = await async_db.save("agents", "abc", {"name": "test"})

    assert result["ok"] is True
    sync.save.assert_called_once_with("agents", "abc", {"name": "test"})


@pytest.mark.asyncio
async def test_async_list_all_runs_in_thread():
    """A slow sync call should not block other coroutines on the same loop."""
    import time

    sync = MagicMock()
    def slow_list_all(db_name):
        time.sleep(0.1)
        return [{"_id": "a"}, {"_id": "b"}]
    sync.list_all = slow_list_all
    async_db = AsyncDatabaseService(sync)

    other_ran = False

    async def other_coroutine():
        nonlocal other_ran
        await asyncio.sleep(0.05)
        other_ran = True

    # Run both concurrently. If list_all were blocking the loop, the
    # other coroutine would have to wait the full 0.1s. With to_thread,
    # other_ran flips well before list_all returns.
    results = await asyncio.gather(async_db.list_all("agents"), other_coroutine())

    assert results[0] == [{"_id": "a"}, {"_id": "b"}]
    assert other_ran is True


@pytest.mark.asyncio
async def test_sync_property_returns_underlying_service():
    sync = MagicMock()
    async_db = AsyncDatabaseService(sync)
    assert async_db.sync is sync
