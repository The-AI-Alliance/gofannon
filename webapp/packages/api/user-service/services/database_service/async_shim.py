"""Async wrapper for the synchronous DatabaseService.

The ``couchdb`` Python library is fully synchronous. When an async route
handler calls one of its methods directly, the call blocks the asyncio
event loop until the HTTP roundtrip to CouchDB completes -- meaning the
worker cannot serve any other request during that time. With a single
long-running agent making thousands of sync CouchDB calls, the entire
worker is unresponsive.

This shim wraps each sync method in ``asyncio.to_thread`` so the call
runs on a thread-pool executor and the event loop stays free to serve
other coroutines. It does NOT make CouchDB itself faster -- if the CouchDB
server is the bottleneck (CPU, fsync, connection pool), the shim only
helps with API responsiveness, not raw throughput.

Use from async route handlers via the ``get_async_db`` dependency.

Sync access is still available (and preferred for code paths that arent
in an async context, like background scripts and the agent runner). The
shim wraps an existing sync service rather than replacing it.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .base import DatabaseService


class AsyncDatabaseService:
    """Async facade over a synchronous DatabaseService."""

    def __init__(self, sync_service: DatabaseService):
        self._sync = sync_service

    # --- read path ---

    async def get(self, db_name: str, doc_id: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync.get, db_name, doc_id)

    async def list_all(self, db_name: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._sync.list_all, db_name)

    async def find(
        self,
        db_name: str,
        selector: Dict[str, Any],
        **kwargs,
    ) -> List[Dict[str, Any]]:
        # kwargs passthrough so the shim doesn't need updating when the
        # sync find() signature changes. Current sync signature accepts
        # fields and limit; an earlier shim version enumerated a sort
        # kwarg that the sync class never supported, which exploded the
        # moment a real route exercised it.
        return await asyncio.to_thread(self._sync.find, db_name, selector, **kwargs)

    async def get_many(self, db_name: str, doc_ids: List[str]) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._sync.get_many, db_name, doc_ids)

    # --- write path ---

    async def save(self, db_name: str, doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        return await asyncio.to_thread(self._sync.save, db_name, doc_id, doc)

    async def save_many(self, db_name: str, docs: List[Dict[str, Any]]):
        return await asyncio.to_thread(self._sync.save_many, db_name, docs)

    async def delete(self, db_name: str, doc_id: str):
        return await asyncio.to_thread(self._sync.delete, db_name, doc_id)

    async def delete_many(self, db_name: str, doc_ids: List[str]):
        return await asyncio.to_thread(self._sync.delete_many, db_name, doc_ids)

    async def ensure_index(self, db_name: str, fields: List[str], **kwargs):
        # Sync signature uses index_name (not name); pass-through avoids
        # the naming mismatch.
        return await asyncio.to_thread(self._sync.ensure_index, db_name, fields, **kwargs)

    # --- escape hatch ---

    @property
    def sync(self) -> DatabaseService:
        """Access the underlying sync service for code paths that genuinely
        need it (background scripts, agent runtime that hasnt been
        converted). Use sparingly inside async route handlers."""
        return self._sync
