# webapp/packages/api/user-service/auth/providers/google.py
"""Google (Workspace) auth provider.

Flow:
    1. Browser redirected to Google's OAuth2 authorize endpoint.
    2. User consents, including the ``admin.directory.group.readonly``
       scope if group memberships are desired.
    3. Browser lands on ``/auth/callback/google`` with ``code`` and ``state``.
    4. ``exchange_code`` POSTs to the token endpoint, then GETs userinfo.
    5. ``get_workspace_memberships`` enumerates the user's Google Groups
       via the Admin SDK Directory API. Groups are the workspace unit.

Modes:
    - ``allowlist`` (default): deny login unless user is in at least one
      configured ``allowed_groups``. Safer default; non-allowlisted
      users are emeritus-denied even inside the Workspace domain.
    - ``open_domain``: allow anyone in the configured ``hosted_domain``;
      still uses group memberships for workspace assignment. Set this
      for company-wide deployments where "anyone at @acme.com can use
      the tool".

Role mapping:
    Admin SDK returns ``role`` per group membership: OWNER, MANAGER,
    MEMBER. OWNER and MANAGER map to workspace role ``admin``; MEMBER
    maps to ``member``.

Caveats:
    - Listing groups requires a service account with domain-wide
      delegation OR the user's own consent to ``directory.group.readonly``
      (user-consent scope is available since 2022 and is what we use).
      Either way, the Admin SDK can 403 for users who aren't in any
      Admin-SDK-visible group — we treat that as "no memberships".
    - The ``hosted_domain`` config acts as a hard filter at login time;
      a Gmail.com user will be denied even if they're somehow in an
      allowlisted group.

Config shape (under AUTH_CONFIG["providers"][...]["config"]):

    client_id: "123...apps.googleusercontent.com"
    client_secret: "${GOOGLE_OAUTH_CLIENT_SECRET}"
    hosted_domain: acme.com       # required; enforces single-tenant
    mode: allowlist               # or "open_domain"
    allowed_groups:               # required if mode=allowlist
      - engineering@acme.com
      - data-platform@acme.com
    # Optional display-name overrides (same pattern as ASF).
    group_display_names:
      engineering@acme.com: "Engineering"
"""
import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from ..base import (
    AuthProvider,
    LoginAllow,
    LoginDecision,
    LoginDeny,
    Membership,
    UserInfo,
)


AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
# Admin SDK — "groups of user" endpoint. Requires directory.group.readonly.
GROUPS_URL = "https://admin.googleapis.com/admin/directory/v1/groups"

# Scopes requested at login. ``directory.group.readonly`` is user-consent
# eligible since 2022, so no service account or domain-wide delegation is
# required for the groups lookup.
DEFAULT_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/admin.directory.group.readonly",
]


class GoogleProvider(AuthProvider):
    type = "google"

    def __init__(self, config: dict):
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.hosted_domain = config.get("hosted_domain")
        self.mode = config.get("mode", "allowlist")
        self.allowed_groups = set(config.get("allowed_groups") or [])
        self.group_display_names = config.get("group_display_names") or {}

        if not self.client_id or not self.client_secret:
            raise ValueError("google: client_id and client_secret are required")
        if not self.hosted_domain:
            raise ValueError(
                "google: hosted_domain is required (single-tenant enforcement)"
            )
        if self.mode not in ("allowlist", "open_domain"):
            raise ValueError(
                f"google: mode must be 'allowlist' or 'open_domain', got {self.mode!r}"
            )
        if self.mode == "allowlist" and not self.allowed_groups:
            raise ValueError(
                "google: allowed_groups is required when mode=allowlist"
            )

    @property
    def display_name(self) -> str:
        return self.config.get("display_name", "Sign in with Google")

    @property
    def icon_hint(self) -> Optional[str]:
        return "google"

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """Standard Google OAuth2 authorize URL.

        ``hd`` restricts the account picker to the configured hosted
        domain — prevents users from accidentally picking a personal
        @gmail.com account. It's a hint, not a guarantee, so we
        re-enforce in exchange_code.
        """
        params = urlencode({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(DEFAULT_SCOPES),
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
            "hd": self.hosted_domain,
        })
        return f"{AUTHORIZE_URL}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> UserInfo:
        """Exchange ``code`` for access token, then fetch userinfo.

        We stash the access_token in ``user_info._access_token`` so the
        subsequent get_workspace_memberships call can use it without
        re-authenticating. This isn't pretty (dataclass + ad-hoc attr)
        but avoids threading the token through the auth-route plumbing.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise RuntimeError(
                    f"Google OAuth token exchange failed: "
                    f"{token_resp.status_code} {token_resp.text}"
                )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise RuntimeError("Google OAuth token response missing access_token")

            info_resp = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if info_resp.status_code != 200:
                raise RuntimeError(
                    f"Google userinfo fetch failed: "
                    f"{info_resp.status_code} {info_resp.text}"
                )
            info = info_resp.json()

        # Enforce hosted domain server-side (authorize param ``hd`` is
        # only a hint — can be bypassed).
        if info.get("hd") != self.hosted_domain:
            raise RuntimeError(
                f"Google account not in configured hosted domain "
                f"({self.hosted_domain!r})"
            )

        sub = info.get("sub")
        if not sub:
            raise RuntimeError(f"Google userinfo missing 'sub': {info}")

        user_info = UserInfo(
            provider_type=self.type,
            external_id=sub,
            display_name=info.get("name") or info.get("email") or sub,
            email=info.get("email"),
        )
        # Attach token for the subsequent groups call. See class docstring.
        user_info._access_token = access_token  # type: ignore[attr-defined]
        return user_info

    async def get_workspace_memberships(self, user_info: UserInfo) -> List[Membership]:
        """Enumerate Google Groups the user belongs to.

        Uses the access token from exchange_code. If the token isn't
        available (e.g. during refresh), returns [] — the refresh code
        in SessionService treats empty-with-outage as "keep existing".
        """
        access_token = getattr(user_info, "_access_token", None)
        if not access_token or not user_info.email:
            return []

        params = {
            "userKey": user_info.email,
            "maxResults": 200,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                GROUPS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            # 403 is common for users who have no directory visibility.
            # Treat as "no groups", not a hard failure.
            if resp.status_code == 403:
                return []
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Google Admin Directory lookup failed: "
                    f"{resp.status_code} {resp.text}"
                )
            data = resp.json()

        groups = data.get("groups") or []
        memberships: List[Membership] = []
        for g in groups:
            email = g.get("email")
            if not email:
                continue
            # Only emit workspaces the operator has allowlisted, unless
            # in open_domain mode where all domain groups count.
            if self.mode == "allowlist" and email not in self.allowed_groups:
                continue

            # Admin SDK uses OWNER/MANAGER/MEMBER here, upper-case.
            role_raw = (g.get("role") or "MEMBER").upper()
            role = "admin" if role_raw in ("OWNER", "MANAGER") else "member"
            display = self.group_display_names.get(email, g.get("name") or email)
            memberships.append(Membership(
                workspace_id=f"group:{email}",
                role=role,
                display_name=display,
                source="google_group",
            ))
        return memberships

    async def evaluate_login(
        self,
        user_info: UserInfo,
        memberships: List[Membership],
        site_admins: List[str],
    ) -> LoginDecision:
        """Allow if user is site admin OR has a workspace membership.

        In open_domain mode, anyone in the hosted domain is allowed
        even without group memberships — the hosted_domain check in
        exchange_code already filtered out external users.
        """
        if user_info.uid in site_admins:
            return LoginAllow(site_admin=True)
        if memberships:
            return LoginAllow(site_admin=False)
        if self.mode == "open_domain":
            return LoginAllow(site_admin=False)
        return LoginDeny(
            reason=(
                "Your Google account is valid, but you're not in any of "
                "the groups granted access. Contact your administrator."
            )
        )
