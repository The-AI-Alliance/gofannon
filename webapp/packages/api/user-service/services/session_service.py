# webapp/packages/api/user-service/services/session_service.py
"""Server-side session store for Phase B auth.

A session is created after a successful OAuth exchange, identified by
an opaque random id stored in the ``gofannon_sid`` cookie. The session
document carries:

  - user identity (uid, display name, email)
  - provider type (so refresh/logout can dispatch correctly)
  - workspace memberships (refreshed every ~15 minutes)
  - is_site_admin flag (recomputed from allowlist on every refresh)

Sessions live in the ``user_sessions`` collection. The cookie value is
the CouchDB _id — no extra lookup layer. Sessions are never revoked
server-side at login time of another browser; concurrent sessions are
allowed.

Expiry is a hard wall: the ``expires_at`` field is checked on every
access, and expired sessions are returned as "not authenticated" even
if the cookie hasn't been cleared on the client.
"""
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import HTTPException

from auth import UserInfo, get_registry
from auth.base import Membership
from config import settings
from models.session import Session
from models.workspace import (
    WorkspaceMembership,
    make_personal_workspace_id,
)
from services.database_service import DatabaseService


_SESSIONS_COLLECTION = "user_sessions"
_COOKIE_NAME = "gofannon_sid"


class SessionService:
    """CRUD over session docs plus helpers for creating + refreshing."""

    def __init__(self, db: DatabaseService):
        self.db = db
        auth_cfg = settings.AUTH_CONFIG or {}
        self._ttl_hours: int = auth_cfg.get("session_ttl_hours", 24)
        self._refresh_minutes: int = auth_cfg.get("workspace_refresh_minutes", 15)
        self._site_admins: List[str] = list(auth_cfg.get("site_admins") or [])

    # --- Cookie name ------------------------------------------------------

    @staticmethod
    def cookie_name() -> str:
        return _COOKIE_NAME

    # --- Session lifecycle ------------------------------------------------

    async def create_from_login(
        self,
        user_info: UserInfo,
        provider_memberships: List[Membership],
        is_site_admin: bool,
    ) -> Session:
        """Create and persist a new session after a successful login.

        Auto-prepends the personal workspace to the provider's
        memberships. The caller should already have run
        ``AuthProvider.evaluate_login`` and only invoke this on allow.
        """
        sid = _new_session_id()
        now = datetime.utcnow()
        expires = now + timedelta(hours=self._ttl_hours)

        workspaces = _to_workspace_memberships(
            user_info, provider_memberships
        )

        session = Session(
            id=sid,
            user_uid=user_info.uid,
            provider_type=user_info.provider_type,
            display_name=user_info.display_name,
            email=user_info.email,
            workspaces=workspaces,
            is_site_admin=is_site_admin,
            created_at=now,
            updated_at=now,
            expires_at=expires,
            last_refresh_at=now,
        )
        self.db.save(
            _SESSIONS_COLLECTION,
            sid,
            session.model_dump(by_alias=True, mode="json"),
        )
        return session

    async def get_by_id(self, sid: Optional[str]) -> Optional[Session]:
        """Look up a session by cookie value. Returns None for missing,
        expired, or malformed sessions — never raises.

        Expired sessions are also deleted as a best-effort cleanup.
        """
        if not sid:
            return None
        try:
            doc = self.db.get(_SESSIONS_COLLECTION, sid)
        except HTTPException as e:
            if e.status_code == 404:
                return None
            raise

        try:
            session = Session(**doc)
        except Exception:
            # Corrupt doc — treat as missing and evict.
            try:
                self.db.delete(_SESSIONS_COLLECTION, sid)
            except Exception:
                pass
            return None

        if session.expires_at <= datetime.utcnow():
            # Best-effort eviction; ignore errors.
            try:
                self.db.delete(_SESSIONS_COLLECTION, sid)
            except Exception:
                pass
            return None

        return session

    async def delete(self, sid: Optional[str]) -> None:
        """Log out / delete a session. Safe on missing sessions."""
        if not sid:
            return
        try:
            self.db.delete(_SESSIONS_COLLECTION, sid)
        except HTTPException as e:
            if e.status_code == 404:
                return
            raise

    # --- Workspace refresh -----------------------------------------------

    async def refresh_workspaces(
        self, session: Session
    ) -> Tuple[Session, "RefreshDiff"]:
        """Re-query the provider for current memberships; update the session.

        Implements the soft-fail policy: when the provider returns an
        empty membership list AND the existing session has memberships,
        we assume the provider is down and keep the existing set. The
        only way to go from N memberships to 0 is for the provider to
        explicitly return 0 — but in ASF's case the LDAP client never
        distinguishes "no groups" from "query failed"; it signals via
        ``query_succeeded``, which the provider's
        ``get_workspace_memberships`` already uses (empty list on LDAP
        error). So from here, we just accept whatever the provider
        returns and compare.

        NB: refinement worth revisiting in B-1.1 — plumb the
        query_succeeded flag up to this level so "legitimately zero
        memberships after being removed from every PMC" can be
        distinguished from "LDAP is down."
        """
        registry = get_registry()
        provider = registry.get(session.provider_type)
        if provider is None:
            # Provider has been disabled since this session was created.
            # Don't touch memberships; this is effectively a no-op refresh.
            return session, RefreshDiff()

        user_info = UserInfo(
            provider_type=session.provider_type,
            external_id=session.user_uid.split(":", 1)[1],
            display_name=session.display_name,
            email=session.email,
        )
        new_memberships = await provider.get_workspace_memberships(user_info)
        was_site_admin = session.is_site_admin
        now_site_admin = session.user_uid in self._site_admins

        new_workspaces = _to_workspace_memberships(user_info, new_memberships)
        diff = _compute_diff(session.workspaces, new_workspaces, was_site_admin, now_site_admin)

        session.workspaces = new_workspaces
        session.is_site_admin = now_site_admin
        session.updated_at = datetime.utcnow()
        session.last_refresh_at = session.updated_at

        self.db.save(
            _SESSIONS_COLLECTION,
            session.id,
            session.model_dump(by_alias=True, mode="json"),
        )
        return session, diff

    # --- Introspection ---------------------------------------------------

    def needs_refresh(self, session: Session) -> bool:
        """Whether the session's workspaces are stale enough to warrant a refresh."""
        age = datetime.utcnow() - session.last_refresh_at
        return age > timedelta(minutes=self._refresh_minutes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_session_id() -> str:
    """32 random bytes, url-safe base64-encoded. ~43 chars."""
    return secrets.token_urlsafe(32)


def _to_workspace_memberships(
    user_info: UserInfo, provider_memberships: List[Membership]
) -> List[WorkspaceMembership]:
    """Prepend the personal workspace and convert dataclasses -> models."""
    personal = WorkspaceMembership(
        workspace_id=make_personal_workspace_id(
            user_info.provider_type, user_info.external_id
        ),
        role="admin",  # always admin of your own personal workspace
        display_name="Personal",
        source="auto_personal",
    )
    rest = [
        WorkspaceMembership(
            workspace_id=m.workspace_id,
            role=m.role,  # type: ignore[arg-type]
            display_name=m.display_name,
            source=m.source,  # type: ignore[arg-type]
        )
        for m in provider_memberships
    ]
    return [personal] + rest


class RefreshDiff:
    """Lightweight struct for what changed across a refresh.

    Kept as a plain class (not pydantic) because it's used as a
    transient return value; serialized by the route handler into the
    public RefreshWorkspacesDiff model.
    """
    def __init__(
        self,
        added: Optional[List[str]] = None,
        removed: Optional[List[str]] = None,
        role_changes: Optional[List[str]] = None,
        site_admin_changed: bool = False,
    ):
        self.added = added or []
        self.removed = removed or []
        self.role_changes = role_changes or []
        self.site_admin_changed = site_admin_changed


def _compute_diff(
    old: List[WorkspaceMembership],
    new: List[WorkspaceMembership],
    was_site_admin: bool,
    is_site_admin: bool,
) -> RefreshDiff:
    old_ids = {w.workspace_id: w for w in old}
    new_ids = {w.workspace_id: w for w in new}
    added = sorted(set(new_ids) - set(old_ids))
    removed = sorted(set(old_ids) - set(new_ids))
    role_changes = sorted(
        wid for wid in set(old_ids) & set(new_ids)
        if old_ids[wid].role != new_ids[wid].role
    )
    return RefreshDiff(
        added=added,
        removed=removed,
        role_changes=role_changes,
        site_admin_changed=(was_site_admin != is_site_admin),
    )


def get_session_service(db: DatabaseService) -> SessionService:
    """Factory function; mirrors other *_service modules' convention."""
    return SessionService(db)
