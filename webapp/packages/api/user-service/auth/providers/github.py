# webapp/packages/api/user-service/auth/providers/github.py
"""GitHub auth provider.

Flow:
    1. Browser redirected to GitHub's OAuth authorize endpoint.
    2. User approves with ``read:org`` scope (org visibility is private
       by default — without this scope, /user/orgs returns empty even
       for genuine org members).
    3. Browser lands on ``/auth/callback/github``.
    4. ``exchange_code`` trades the code for an access token, then GETs
       /user for identity.
    5. ``get_workspace_memberships`` GETs /user/orgs and, if configured,
       /user/memberships/orgs/{org}/teams for per-team granularity.

Modes:
    - ``allowlist`` (default): only allow users in at least one
      ``allowed_orgs``. Safer default for internal tools — prevents
      "any GitHub user can sign in" footgun.
    - ``open_github``: allow any authenticated GitHub user. For public
      SaaS deployments.

Role mapping:
    GitHub's /user/memberships/orgs/{org} returns ``role`` = ``admin``
    or ``member``. Admins get workspace role ``admin``, members get
    ``member``. We call the membership endpoint per allowlisted org
    since /user/orgs alone doesn't include role.

Caveats:
    - ``read:org`` is a required scope — without it, orgs that set
     "Third-party application access" to "Policy enforced" will have
      their membership data hidden even from the user themselves.
    - Personal accounts (unaffiliated with an org) can only log in
      in ``open_github`` mode. In allowlist mode they see deny.
    - We don't read team memberships here — workspace granularity
      is per-org. Per-team scoping is a future PR (B-1.2 if needed).

Config shape (under AUTH_CONFIG["providers"][...]["config"]):

    client_id: "..."
    client_secret: "${GITHUB_OAUTH_CLIENT_SECRET}"
    mode: allowlist              # or "open_github"
    allowed_orgs:                # org login slugs (case-insensitive)
      - acme-corp
      - acme-internal
    org_display_names:           # optional overrides
      acme-corp: "ACME Corporation"
"""
from typing import List, Optional
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


AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
ORGS_URL = "https://api.github.com/user/orgs"
MEMBERSHIP_URL_TEMPLATE = "https://api.github.com/user/memberships/orgs/{org}"

DEFAULT_SCOPES = ["read:user", "user:email", "read:org"]


class GitHubProvider(AuthProvider):
    type = "github"

    def __init__(self, config: dict):
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.mode = config.get("mode", "allowlist")
        # Normalize to lowercase — GitHub org logins are case-insensitive.
        self.allowed_orgs = {
            o.lower() for o in (config.get("allowed_orgs") or [])
        }
        self.org_display_names = {
            k.lower(): v
            for k, v in (config.get("org_display_names") or {}).items()
        }

        if not self.client_id or not self.client_secret:
            raise ValueError("github: client_id and client_secret are required")
        if self.mode not in ("allowlist", "open_github"):
            raise ValueError(
                f"github: mode must be 'allowlist' or 'open_github', got {self.mode!r}"
            )
        if self.mode == "allowlist" and not self.allowed_orgs:
            raise ValueError(
                "github: allowed_orgs is required when mode=allowlist"
            )

    @property
    def display_name(self) -> str:
        return self.config.get("display_name", "Sign in with GitHub")

    @property
    def icon_hint(self) -> Optional[str]:
        return "github"

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        params = urlencode({
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(DEFAULT_SCOPES),
            "state": state,
            "allow_signup": "false",
        })
        return f"{AUTHORIZE_URL}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> UserInfo:
        """Exchange code -> access_token, then GET /user.

        GitHub returns the token as ``application/x-www-form-urlencoded``
        by default; requesting ``application/json`` keeps parsing simple.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_resp.status_code != 200:
                raise RuntimeError(
                    f"GitHub OAuth token exchange failed: "
                    f"{token_resp.status_code} {token_resp.text}"
                )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                # GitHub sometimes 200s with an error payload instead of
                # a non-200. Surface the error field if present.
                err = token_data.get("error_description") or token_data.get("error")
                raise RuntimeError(
                    f"GitHub token response missing access_token: {err or token_data}"
                )

            user_resp = await client.get(
                USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if user_resp.status_code != 200:
                raise RuntimeError(
                    f"GitHub /user fetch failed: "
                    f"{user_resp.status_code} {user_resp.text}"
                )
            user = user_resp.json()

        login = user.get("login")
        if not login:
            raise RuntimeError(f"GitHub /user response missing 'login': {user}")

        # GitHub ``id`` is a stable numeric; prefer that over ``login``
        # for external_id since logins can be renamed.
        gh_id = user.get("id")
        external_id = str(gh_id) if gh_id is not None else login

        user_info = UserInfo(
            provider_type=self.type,
            external_id=external_id,
            display_name=user.get("name") or login,
            email=user.get("email"),
        )
        user_info._access_token = access_token  # type: ignore[attr-defined]
        # Also stash login — needed for membership URL templating.
        user_info._login = login  # type: ignore[attr-defined]
        return user_info

    async def get_workspace_memberships(self, user_info: UserInfo) -> List[Membership]:
        """Enumerate org memberships.

        For each allowlisted org, we hit /user/memberships/orgs/{org}
        to get role. In open_github mode we don't know the set of orgs
        in advance, so we first GET /user/orgs then call the membership
        endpoint for each.
        """
        access_token = getattr(user_info, "_access_token", None)
        if not access_token:
            return []

        async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        ) as client:
            if self.mode == "open_github":
                # Discover the user's orgs first.
                orgs_resp = await client.get(ORGS_URL, params={"per_page": 100})
                if orgs_resp.status_code == 403:
                    return []
                if orgs_resp.status_code != 200:
                    raise RuntimeError(
                        f"GitHub /user/orgs failed: "
                        f"{orgs_resp.status_code} {orgs_resp.text}"
                    )
                orgs_to_check = [
                    o.get("login").lower()
                    for o in orgs_resp.json()
                    if o.get("login")
                ]
            else:
                # Allowlist mode: only check orgs we care about. This is
                # both faster and avoids leaking info about orgs the user
                # belongs to that we don't allow.
                orgs_to_check = sorted(self.allowed_orgs)

            memberships: List[Membership] = []
            for org in orgs_to_check:
                url = MEMBERSHIP_URL_TEMPLATE.format(org=org)
                m_resp = await client.get(url)
                # 404 = not a member. 403 = lack of scope / SSO not granted.
                if m_resp.status_code in (404, 403):
                    continue
                if m_resp.status_code != 200:
                    # Log & skip individual org failures — don't take down
                    # the whole login because one org lookup glitched.
                    continue
                m_data = m_resp.json()
                # Active memberships only. Pending/unsubscribed = not in.
                if m_data.get("state") != "active":
                    continue

                role_raw = (m_data.get("role") or "member").lower()
                role = "admin" if role_raw == "admin" else "member"
                display = self.org_display_names.get(org, org)
                memberships.append(Membership(
                    workspace_id=f"github:{org}",
                    role=role,
                    display_name=display,
                    source="github_org",
                ))

        return memberships

    async def evaluate_login(
        self,
        user_info: UserInfo,
        memberships: List[Membership],
        site_admins: List[str],
    ) -> LoginDecision:
        """Allow if site admin, has memberships, or open_github mode.

        open_github + no memberships = allowed as a user with just
        their personal workspace. Useful for OSS-style tools where
        anyone can sign up.
        """
        if user_info.uid in site_admins:
            return LoginAllow(site_admin=True)
        if memberships:
            return LoginAllow(site_admin=False)
        if self.mode == "open_github":
            return LoginAllow(site_admin=False)
        return LoginDeny(
            reason=(
                "Your GitHub account is valid, but you're not a member "
                "of any allowlisted organization. Contact your administrator."
            )
        )
