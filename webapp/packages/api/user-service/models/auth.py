# webapp/packages/api/user-service/models/auth.py
"""Client-facing auth models.

The frontend queries ``GET /auth/providers`` (unauthenticated — for
LoginPage) to discover what sign-in options to render. This module is
that response's schema.
"""
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class AuthProviderInfo(BaseModel):
    """Public metadata about an enabled auth provider.

    Returned to the unauthenticated frontend so LoginPage can render a
    button per provider. Must not contain any secrets.
    """
    # Stable identifier used in URLs (/auth/login/{type}).
    type: str

    # Human-readable name shown on the sign-in button.
    # e.g. "Apache Software Foundation", "Dev stub login".
    display_name: str = Field(..., alias="displayName")

    # Optional hint for the frontend icon ("asf", "google", "github", ...).
    # Frontend maps this to a component; unknown values fall back to a
    # generic lock icon.
    icon: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class AuthProvidersResponse(BaseModel):
    """Response shape for GET /auth/providers."""

    providers: List[AuthProviderInfo] = Field(default_factory=list)

    # True when the legacy Firebase auth path is still active. Frontend
    # can use this to decide whether to also render a Firebase login
    # button (Phase B rollout) or to replace Firebase entirely (Phase B
    # post-migration).
    legacy_firebase_enabled: bool = Field(default=True, alias="legacyFirebaseEnabled")

    model_config = ConfigDict(populate_by_name=True)


class RefreshWorkspacesDiff(BaseModel):
    """Response shape for POST /auth/refresh-workspaces.

    Returns what changed between the previous session state and the
    freshly-queried one, so the UI can flash a toast if anything moved.
    """
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)
    role_changes: List[str] = Field(default_factory=list, alias="roleChanges")
    site_admin_changed: bool = Field(default=False, alias="siteAdminChanged")

    model_config = ConfigDict(populate_by_name=True)
