# webapp/packages/api/user-service/auth/base.py
"""Abstract base for Phase B pluggable auth providers.

Each concrete provider implements the abstract methods. The rest of the
application interacts only through this interface — so swapping ASF for
Google or adding GitHub later doesn't touch any business logic.

Minimum contract:
    - get_authorize_url(state, redirect_uri) -> str
    - exchange_code(code, redirect_uri) -> UserInfo
    - get_workspace_memberships(user_info) -> List[Membership]
    - evaluate_login(user_info, memberships, site_admins) -> LoginDecision
      (default implementation provided)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Union


# ---------------------------------------------------------------------------
# Data types crossing the provider boundary
# ---------------------------------------------------------------------------


@dataclass
class UserInfo:
    """Identity returned from a completed OAuth/login exchange.

    ``external_id`` is whatever the provider uses as stable primary key
    (ASF uid, GitHub login, Google sub, etc.). The app never treats it
    as globally unique — always compose with ``provider_type`` first via
    the ``uid`` property.
    """
    provider_type: str
    external_id: str
    display_name: str
    email: Optional[str] = None

    @property
    def uid(self) -> str:
        """Globally-unique uid: ``{provider_type}:{external_id}``.

        This is what goes on session docs, audit logs, data-store userId
        fields, and anywhere else the system identifies a user.
        """
        return f"{self.provider_type}:{self.external_id}"


@dataclass
class Membership:
    """A workspace the user has access to, as reported by a provider."""
    workspace_id: str
    role: str  # "member" | "admin"
    display_name: str
    source: str  # MembershipSource from models.workspace


@dataclass
class LoginAllow:
    """Login permitted."""
    site_admin: bool = False


@dataclass
class LoginDeny:
    """Login refused; ``reason`` shown to the user."""
    reason: str


# Type alias for provider login decisions.
LoginDecision = Union[LoginAllow, LoginDeny]


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class AuthProvider(ABC):
    """Contract for a pluggable authentication provider.

    A provider is instantiated once at startup from its slice of
    ``AUTH_CONFIG["providers"]`` and reused for the process lifetime.
    Subclasses should treat ``__init__`` as the place to validate config;
    raising there will cause the service to fail-fast rather than
    mysteriously erroring at login time.
    """

    # Stable identifier used in URLs and config.
    # Subclasses override this with a class attribute.
    type: str = ""

    def __init__(self, config: dict):
        # Provider-specific config; subclasses read keys they care about.
        # Storing the whole dict makes config debugging easier.
        self.config = config

    # --- Abstract methods --------------------------------------------------

    @abstractmethod
    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """URL to redirect the browser to for the first OAuth leg.

        For providers that aren't OAuth (dev_stub), return a URL
        to a backend endpoint that completes the flow without user
        interaction.
        """

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> UserInfo:
        """Exchange an authorization code for a ``UserInfo``.

        Subclasses may raise on any provider error; the route handler
        turns these into a 4xx response.
        """

    @abstractmethod
    async def get_workspace_memberships(self, user_info: UserInfo) -> List[Membership]:
        """Enumerate the user's current workspace memberships.

        Called at login and at refresh time. Should include the auto-created
        personal workspace only if the provider is responsible for it —
        most providers return just the provider-derived memberships and
        let ``SessionService`` prepend the personal workspace.
        """

    # --- Default implementations -----------------------------------------

    @property
    def display_name(self) -> str:
        """Human-readable provider name for the sign-in button.

        Subclasses usually override. Falls back to the provider type
        capitalized.
        """
        return self.type.capitalize()

    @property
    def icon_hint(self) -> Optional[str]:
        """Optional icon hint returned to the frontend."""
        return None

    async def evaluate_login(
        self,
        user_info: UserInfo,
        memberships: List[Membership],
        site_admins: List[str],
    ) -> LoginDecision:
        """Default login policy: allow if user has memberships or is
        in the site-admin allowlist; otherwise deny.

        Subclasses can override to add provider-specific checks (e.g.,
        ASF's banned-group check).
        """
        if user_info.uid in site_admins:
            return LoginAllow(site_admin=True)
        if memberships:
            return LoginAllow(site_admin=False)
        return LoginDeny(
            reason="No active workspace memberships. "
                   "Contact your administrator if this is in error."
        )
