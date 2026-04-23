# webapp/packages/api/user-service/auth/providers/asf.py
"""ASF auth provider: oauth.apache.org + ldap-eu.apache.org.

Flow:
    1. Browser redirected to ``OAUTH_URL_INIT`` with state.
    2. User approves at oauth.apache.org.
    3. Browser lands back on ``/auth/callback/asf?code=...&state=...``.
    4. ``exchange_code`` POSTs the code to ``OAUTH_URL_CALLBACK`` and
       parses the user info from the response.
    5. ``get_workspace_memberships`` queries LDAP for committer and PMC
       groups, and the banned list.

The two steps (OAuth + LDAP) happen sequentially in the auth route:
first ``exchange_code`` → then ``get_workspace_memberships``. ASF is
the outlier here — most providers put group info in the OAuth response
itself — but the cost is one extra LDAP query per login (~50ms).
"""
import asyncio
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
from ..ldap_client import LdapClient

# Default endpoints; overridable via provider config.
OAUTH_URL_INIT = "https://oauth.apache.org/auth"
OAUTH_URL_CALLBACK = "https://oauth.apache.org/token"

# Optional per-project display-name overrides. Callers can extend via
# AUTH_CONFIG["providers"][asf]["config"]["project_display_names"].
# Keys are project slugs; values are human-readable names.
DEFAULT_PROJECT_DISPLAY_NAMES = {
    # A small seed set; extend via config.
    "httpd":   "Apache HTTP Server",
    "tomcat":  "Apache Tomcat",
    "kafka":   "Apache Kafka",
    "spark":   "Apache Spark",
    "beam":    "Apache Beam",
    "airflow": "Apache Airflow",
}


class AsfProvider(AuthProvider):
    type = "asf"

    def __init__(self, config: dict):
        super().__init__(config)
        self.oauth_init = config.get("oauth_init_url", OAUTH_URL_INIT)
        self.oauth_callback = config.get("oauth_callback_url", OAUTH_URL_CALLBACK)
        self.display_names = {
            **DEFAULT_PROJECT_DISPLAY_NAMES,
            **(config.get("project_display_names") or {}),
        }
        # LDAP config; the client's defaults match production ldap-eu.apache.org.
        ldap_cfg = config.get("ldap") or {}
        self._ldap = LdapClient(
            server=ldap_cfg.get("server", "ldaps://ldap-eu.apache.org"),
            committer_base=ldap_cfg.get(
                "committer_base", "ou=project,ou=groups,dc=apache,dc=org"
            ),
            pmc_base=ldap_cfg.get(
                "pmc_base", "ou=pmc,ou=project,ou=groups,dc=apache,dc=org"
            ),
            banned_group=ldap_cfg.get(
                "banned_group", "cn=asf-banned,ou=groups,dc=apache,dc=org"
            ),
            bind_dn=ldap_cfg.get("bind_dn"),
            bind_password=ldap_cfg.get("bind_password"),
            timeout_seconds=ldap_cfg.get("timeout_seconds", 10),
        )

    @property
    def display_name(self) -> str:
        return self.config.get("display_name", "Apache Software Foundation")

    @property
    def icon_hint(self) -> Optional[str]:
        return "asf"

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """Redirect URL for the ASF OAuth authorize leg.

        oauth.apache.org uses a non-standard flow: it takes ``state`` and
        ``redirect_uri`` directly as query params (no client_id / scopes).
        """
        params = urlencode({
            "state": state,
            "redirect_uri": redirect_uri,
        })
        return f"{self.oauth_init}?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> UserInfo:
        """Exchange the OAuth ``code`` for user identity.

        oauth.apache.org returns JSON with at least ``uid``, ``fullname``,
        ``email``. Field shape has varied historically — we defend against
        missing fields with sensible fallbacks and raise on a missing uid.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                self.oauth_callback,
                params={"code": code},
            )
            if resp.status_code != 200:
                raise RuntimeError(
                    f"ASF OAuth token exchange failed: {resp.status_code} {resp.text}"
                )
            data = resp.json()

        uid = data.get("uid")
        if not uid:
            raise RuntimeError(f"ASF OAuth response missing 'uid': {data}")

        return UserInfo(
            provider_type=self.type,
            external_id=uid,
            display_name=data.get("fullname") or uid,
            email=data.get("email"),
        )

    async def get_workspace_memberships(self, user_info: UserInfo) -> List[Membership]:
        """Query LDAP for committer + PMC memberships.

        The actual LDAP call is synchronous (ldap3 has no async API);
        we run it in a thread executor so it doesn't block the event
        loop. Ordering inside the returned list doesn't matter; the
        session service sorts by display_name when rendering.
        """
        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(
            None,
            self._ldap.get_memberships,
            user_info.external_id,
        )

        # Soft-fail: LDAP unavailable. Return empty — evaluate_login
        # handles the policy (deny-on-no-memberships unless site admin).
        # The on-refresh path in SessionService has its own fallback
        # that preserves existing memberships when query_succeeded=False.
        if not snapshot.query_succeeded:
            return []

        memberships: List[Membership] = []
        for project in sorted(snapshot.committer_groups):
            # Intersection with PMC groups upgrades role to admin.
            role = "admin" if project in snapshot.pmc_groups else "member"
            source = "ldap_pmc" if role == "admin" else "ldap_committer"
            display = self.display_names.get(project, f"Apache {project.title()}")
            memberships.append(Membership(
                workspace_id=f"project:{project}",
                role=role,
                display_name=display,
                source=source,
            ))
        return memberships

    async def evaluate_login(
        self,
        user_info: UserInfo,
        memberships: List[Membership],
        site_admins: List[str],
    ) -> LoginDecision:
        """ASF-specific login policy.

        Layered on top of the default policy:
          - banned users are always denied (site-admin allowlist does not
            override a ban — we never want site admin bypass of bans)
          - emeritus committers (uid valid but no memberships and not
            site-admin) are denied with a specific message
          - site admin without memberships: allowed with site_admin=True
            (so ASF infra can still log in even if they're not on any PMC)
        """
        # Re-query the banned group. We already did the full snapshot in
        # get_workspace_memberships, but we don't have the is_banned
        # field on the Membership list alone, so we run one more check.
        loop = asyncio.get_event_loop()
        snapshot = await loop.run_in_executor(
            None,
            self._ldap.get_memberships,
            user_info.external_id,
        )
        # Soft-fail: don't deny on LDAP outage. The refresh cycle will
        # catch a ban the next time LDAP is reachable.
        if snapshot.query_succeeded and snapshot.is_banned:
            return LoginDeny(reason="Your account has been suspended by ASF Infrastructure.")

        if user_info.uid in site_admins:
            return LoginAllow(site_admin=True)
        if memberships:
            return LoginAllow(site_admin=False)
        return LoginDeny(
            reason=(
                "Your apache.org account is valid, but you're not currently "
                "a committer on any project. Contact ASF Infrastructure if "
                "this is in error."
            )
        )
