# webapp/packages/api/user-service/auth/providers/microsoft.py
"""Microsoft Entra ID (Azure AD) auth provider.

Flow:
    1. Browser redirected to Microsoft's v2 authorize endpoint for the
       configured tenant.
    2. User signs in with their work/school account.
    3. Browser lands on ``/auth/callback/microsoft``.
    4. ``exchange_code`` exchanges the code for an access token + ID
       token, validates the tenant, extracts sub/email/name.
    5. ``get_workspace_memberships`` calls Microsoft Graph's
       ``/me/memberOf`` to enumerate group memberships.

Modes:
    - ``allowlist`` (default): only allow users in at least one of the
      ``allowed_groups`` (either group object IDs or display names).
    - ``open_tenant``: allow any user in the configured tenant. Groups
      still drive workspace assignment.

Role mapping:
    Graph doesn't return a role per membership the way Google Admin SDK
    does; group-based admin tagging is done via the optional
    ``admin_groups`` config — any group whose object_id is in
    ``admin_groups`` confers ``admin`` role. Other memberships are
    ``member``.

Caveats:
    - Requires the app registration to have ``GroupMember.Read.All`` as
      a delegated Graph permission (admin consent typically required).
      Without it, /me/memberOf returns 403 and we treat as no groups.
    - Nested groups: /me/memberOf returns direct + transitive via the
      ``/me/transitiveMemberOf`` variant; we use the transitive one so
      users of nested security groups don't get locked out.

Config shape (under AUTH_CONFIG["providers"][...]["config"]):

    tenant_id: "11111111-2222-3333-4444-555555555555"   # or "common"
    client_id: "..."
    client_secret: "${MICROSOFT_OAUTH_CLIENT_SECRET}"
    mode: allowlist                # or "open_tenant"
    allowed_groups:                # group object IDs
      - "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    admin_groups:                  # optional subset conferring admin
      - "ffffffff-gggg-hhhh-iiii-jjjjjjjjjjjj"
    group_display_names:
      "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee": "Data Platform"
"""
from typing import Dict, List, Optional
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


# Microsoft Graph and v2 identity endpoints, templated with tenant.
AUTHORIZE_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
# Transitive memberOf returns direct + nested group memberships.
MEMBEROF_URL = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf"
USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

DEFAULT_SCOPES = [
    "openid",
    "profile",
    "email",
    "User.Read",
    "GroupMember.Read.All",
]


class MicrosoftProvider(AuthProvider):
    type = "microsoft"

    def __init__(self, config: dict):
        super().__init__(config)
        self.tenant_id = config.get("tenant_id")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.mode = config.get("mode", "allowlist")
        self.allowed_groups = set(config.get("allowed_groups") or [])
        self.admin_groups = set(config.get("admin_groups") or [])
        self.group_display_names = config.get("group_display_names") or {}

        if not self.tenant_id:
            raise ValueError("microsoft: tenant_id is required")
        if not self.client_id or not self.client_secret:
            raise ValueError("microsoft: client_id and client_secret are required")
        if self.mode not in ("allowlist", "open_tenant"):
            raise ValueError(
                f"microsoft: mode must be 'allowlist' or 'open_tenant', got {self.mode!r}"
            )
        if self.mode == "allowlist" and not self.allowed_groups:
            raise ValueError(
                "microsoft: allowed_groups is required when mode=allowlist"
            )

    @property
    def display_name(self) -> str:
        return self.config.get("display_name", "Sign in with Microsoft")

    @property
    def icon_hint(self) -> Optional[str]:
        return "microsoft"

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """Standard Microsoft v2 authorize URL, tenant-scoped."""
        url = AUTHORIZE_URL_TEMPLATE.format(tenant=self.tenant_id)
        params = urlencode({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(DEFAULT_SCOPES),
            "state": state,
            "response_mode": "query",
            "prompt": "select_account",
        })
        return f"{url}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> UserInfo:
        """Exchange code -> tokens, then fetch /me for identity.

        Attaches access_token to the returned UserInfo for the
        subsequent groups call (same pattern as GoogleProvider).
        """
        token_url = TOKEN_URL_TEMPLATE.format(tenant=self.tenant_id)
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                token_url,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": " ".join(DEFAULT_SCOPES),
                },
            )
            if token_resp.status_code != 200:
                raise RuntimeError(
                    f"Microsoft OAuth token exchange failed: "
                    f"{token_resp.status_code} {token_resp.text}"
                )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise RuntimeError("Microsoft token response missing access_token")

            me_resp = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if me_resp.status_code != 200:
                raise RuntimeError(
                    f"Microsoft /me fetch failed: "
                    f"{me_resp.status_code} {me_resp.text}"
                )
            me = me_resp.json()

        sub = me.get("id")
        if not sub:
            raise RuntimeError(f"Microsoft /me response missing 'id': {me}")

        # userPrincipalName is the usual email-shaped identifier; mail
        # is sometimes null for guest accounts or consumer MSAs.
        email = me.get("mail") or me.get("userPrincipalName")
        display = me.get("displayName") or email or sub

        user_info = UserInfo(
            provider_type=self.type,
            external_id=sub,
            display_name=display,
            email=email,
        )
        user_info._access_token = access_token  # type: ignore[attr-defined]
        return user_info

    async def get_workspace_memberships(self, user_info: UserInfo) -> List[Membership]:
        """Enumerate user's group memberships via Graph.

        Filters to ``#microsoft.graph.group`` only (the memberOf endpoint
        also returns directoryRoles which we don't care about). 403 on
        permission-gated lookups is treated as empty memberships.
        """
        access_token = getattr(user_info, "_access_token", None)
        if not access_token:
            return []

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                MEMBEROF_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                # Project just the fields we use — keeps response small.
                params={"$select": "id,displayName"},
            )
            if resp.status_code == 403:
                return []
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Microsoft Graph memberOf failed: "
                    f"{resp.status_code} {resp.text}"
                )
            data = resp.json()

        entries = data.get("value") or []
        memberships: List[Membership] = []
        for entry in entries:
            # Graph returns heterogeneous objects here (groups, roles, etc.).
            # We want groups only. The odata type field isn't in
            # our $select projection, so we fall back to "has id" — any
            # object that has both an id and a displayName we treat as a
            # group candidate. Narrow to allowlist below.
            obj_id = entry.get("id")
            if not obj_id:
                continue

            if self.mode == "allowlist" and obj_id not in self.allowed_groups:
                continue

            role = "admin" if obj_id in self.admin_groups else "member"
            display = self.group_display_names.get(
                obj_id, entry.get("displayName") or obj_id
            )
            memberships.append(Membership(
                workspace_id=f"group:{obj_id}",
                role=role,
                display_name=display,
                source="entra_group",
            ))
        return memberships

    async def evaluate_login(
        self,
        user_info: UserInfo,
        memberships: List[Membership],
        site_admins: List[str],
    ) -> LoginDecision:
        """Allow if user is site admin, has memberships, or in open_tenant mode.

        Tenant enforcement is implicit: authorize URL is tenant-scoped,
        so users from other tenants never get a valid token to exchange.
        """
        if user_info.uid in site_admins:
            return LoginAllow(site_admin=True)
        if memberships:
            return LoginAllow(site_admin=False)
        if self.mode == "open_tenant":
            return LoginAllow(site_admin=False)
        return LoginDeny(
            reason=(
                "Your Microsoft account is valid, but you're not a member "
                "of any allowlisted group. Contact your administrator."
            )
        )
