# webapp/packages/api/user-service/models/workspace.py
"""Workspace models for Phase B.

Workspaces are provider-derived collaboration scopes (e.g., "project:tomcat",
"personal:asf:jdoe"). They namespace agents, deployments, demos, and
data-store entries — though workspace *filtering* on those resources
is introduced in B-3; B-1 only establishes the membership model.

Workspace IDs are structured:
    personal:{provider_type}:{external_id}   # auto-created per user
    project:{project_slug}                   # ASF PMC-derived
    org:{org_slug}                           # GitHub-org-derived (future)
    group:{group_slug}                       # generic OIDC-derived (future)

The provider prefix on personal workspaces (not on project/org workspaces)
is deliberate: a user logging in via multiple providers gets separate
personal workspaces (no silent identity merging), but project/org IDs
are usually unique within a single deployment's auth domain.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


# Role within a single workspace.
# Site-admin is not a workspace role — it's a separate global flag on the session.
WorkspaceRole = Literal["member", "admin"]

# Where this membership came from. Used for UX ("you're a PMC member")
# and to know whether a refresh can change it.
MembershipSource = Literal[
    "auto_personal",    # personal workspace, always member, never changes
    "ldap_committer",   # ASF committer group
    "ldap_pmc",         # ASF PMC group (role=admin)
    "dev_stub",         # dev_stub provider's config file
    "github_org",       # future
    "google_group",     # future
    "oidc_claim",       # future
    "manual",           # future: admin-created workspaces
]


class WorkspaceMembership(BaseModel):
    """A user's membership in a single workspace."""

    # Globally-unique workspace id (see module docstring for format).
    workspace_id: str = Field(..., alias="workspaceId")

    # Member or admin within this workspace.
    # Role is per-workspace: you can be admin of `project:tomcat` and
    # just a member of `project:httpd`.
    role: WorkspaceRole = "member"

    # Human-readable name shown in the workspace switcher.
    # For personal workspaces: "Personal". For projects: "Apache Tomcat" if
    # we have a display override, otherwise derived from the id.
    display_name: str = Field(..., alias="displayName")

    # Where this membership came from. Drives UX labeling and
    # determines whether a refresh can change it.
    source: MembershipSource

    # Optional free-form description shown in the workspace details view.
    # For provider-derived workspaces this is unused in B-1; custom
    # workspaces (future) use it.
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


# ---------------------------------------------------------------------------
# Workspace ID helpers
# ---------------------------------------------------------------------------
# Thin wrappers so the rest of the codebase doesn't hardcode prefix strings.

_PERSONAL_PREFIX = "personal:"
_PROJECT_PREFIX = "project:"


def make_personal_workspace_id(provider_type: str, external_id: str) -> str:
    """Canonical personal workspace id: ``personal:{provider}:{external_id}``."""
    return f"{_PERSONAL_PREFIX}{provider_type}:{external_id}"


def make_project_workspace_id(project_slug: str) -> str:
    """Canonical project workspace id: ``project:{slug}``."""
    return f"{_PROJECT_PREFIX}{project_slug}"


def is_personal_workspace(workspace_id: str) -> bool:
    return workspace_id.startswith(_PERSONAL_PREFIX)


def is_project_workspace(workspace_id: str) -> bool:
    return workspace_id.startswith(_PROJECT_PREFIX)


def personal_workspace_owner(workspace_id: str) -> Optional[str]:
    """Extract the user_uid from a personal workspace id.

    Example: ``personal:asf:jdoe`` -> ``asf:jdoe``.
    Returns None if the workspace id isn't a personal one.
    """
    if not is_personal_workspace(workspace_id):
        return None
    return workspace_id[len(_PERSONAL_PREFIX):]
