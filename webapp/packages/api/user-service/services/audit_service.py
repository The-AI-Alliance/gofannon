# webapp/packages/api/user-service/services/audit_service.py
"""Audit log for site-admin cross-workspace reads.

Purpose: every time a site admin reads (or writes) data outside their
own workspaces, append an immutable record with who-did-what-to-whom.
Serves as both a deterrent (visible to the admin themselves and to
peer site admins) and an incident-response tool.

B-1 scope: ship the storage and factory; the actual instrumentation
on cross-workspace route handlers happens in B-3 when workspace
filtering goes live. Having the service in place now keeps that PR
focused on filtering rather than scaffolding.

Events are append-only by convention: there's no update or delete API.
If the CouchDB backend allows it, we should also set per-doc ACLs
that prevent even admins from deleting entries — tracked for a later
hardening pass.
"""
import secrets
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from services.database_service import DatabaseService


_AUDIT_COLLECTION = "site_admin_audit"


class AuditEntry(BaseModel):
    """One audit record."""
    id: str = Field(..., alias="_id")
    rev: Optional[str] = Field(None, alias="_rev")

    actor_uid: str = Field(..., alias="actorUid")
    target_uid: Optional[str] = Field(None, alias="targetUid")
    workspace_id: Optional[str] = Field(None, alias="workspaceId")
    route: str
    method: str
    # Whether the admin had the "write mode" toggle on when this action ran.
    # Reads land here with write_mode=False; writes land with write_mode=True.
    write_mode: bool = Field(default=False, alias="writeMode")
    # Optional context string. Free-form; unbounded. UI truncates.
    detail: Optional[str] = None

    ts: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class AuditService:
    """Append-only audit log writer/reader.

    ``record`` is the only mutating operation. No update, no delete.
    """

    def __init__(self, db: DatabaseService):
        self.db = db

    async def record(
        self,
        actor_uid: str,
        target_uid: Optional[str],
        workspace_id: Optional[str],
        route: str,
        method: str,
        write_mode: bool = False,
        detail: Optional[str] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=secrets.token_urlsafe(16),
            actor_uid=actor_uid,
            target_uid=target_uid,
            workspace_id=workspace_id,
            route=route,
            method=method,
            write_mode=write_mode,
            detail=detail,
        )
        self.db.save(
            _AUDIT_COLLECTION,
            entry.id,
            entry.model_dump(by_alias=True, mode="json"),
        )
        return entry

    async def list_for_actor(self, actor_uid: str, limit: int = 100) -> List[AuditEntry]:
        """Return the most recent audit entries for one actor.

        Used by the self-service audit viewer in B-3. Ordering is
        best-effort by ``ts`` descending.
        """
        docs = self.db.find(_AUDIT_COLLECTION, {"actorUid": actor_uid})
        entries = []
        for doc in docs:
            try:
                entries.append(AuditEntry(**doc))
            except Exception:
                continue
        entries.sort(key=lambda e: e.ts, reverse=True)
        return entries[:limit]


def get_audit_service(db: DatabaseService) -> AuditService:
    return AuditService(db)
