# webapp/packages/api/user-service/auth/providers/dev_stub.py
"""Dev-stub auth provider for local development and tests.

Instead of an OAuth flow, this provider renders a simple HTML page
listing the configured test users; clicking one completes login
immediately as that user. The workspace memberships are taken
directly from config — no LDAP, no network calls.

Config shape (under AUTH_CONFIG["providers"][...]["config"]):

    users:
      - uid: alice
        display_name: Alice Dev
        email: alice@dev.local
        workspaces:
          - id: project:tomcat
            role: admin
            display_name: Apache Tomcat
          - id: project:httpd
            role: member
            display_name: Apache HTTPD
      - uid: bob
        display_name: Bob Emeritus
        email: bob@dev.local
        workspaces: []   # deliberately empty — tests emeritus-deny path

The ``dev_stub`` provider must never be enabled in production. The
session service logs a warning if it sees ``dev_stub`` enabled while
``APP_ENV`` is set to anything other than ``local``/``dev``/``test``.
"""
from typing import List, Optional
from urllib.parse import urlencode

from ..base import AuthProvider, UserInfo, Membership


class DevStubProvider(AuthProvider):
    type = "dev_stub"

    def __init__(self, config: dict):
        super().__init__(config)
        # Validate users list once at init; fail fast if misconfigured.
        users = config.get("users") or []
        if not isinstance(users, list):
            raise ValueError("dev_stub: 'users' must be a list")
        self._users_by_uid = {}
        for u in users:
            if "uid" not in u:
                raise ValueError(f"dev_stub: user entry missing 'uid': {u}")
            self._users_by_uid[u["uid"]] = u

    @property
    def display_name(self) -> str:
        return self.config.get("display_name", "Dev stub login")

    @property
    def icon_hint(self) -> Optional[str]:
        return "dev"

    def get_authorize_url(self, state: str, redirect_uri: str) -> str:
        """Return a URL pointing to the /auth/dev-stub-picker route.

        That route renders a <select> of the configured users and posts
        the chosen uid back to /auth/callback/dev_stub, completing the
        login as that user. No real OAuth roundtrip.

        Note: we encode state + redirect_uri as query params so the
        picker page can pass them back to the callback unchanged. If
        the picker route is mounted at a non-default path, the auth
        router's ``get_authorize_url`` call knows the mount point.
        """
        params = urlencode({
            "state": state,
            "redirect_uri": redirect_uri,
            "users": ",".join(sorted(self._users_by_uid.keys())),
        })
        return f"/auth/dev-stub-picker?{params}"

    async def exchange_code(self, code: str, redirect_uri: str) -> UserInfo:
        """For dev_stub, ``code`` is the selected uid from the picker."""
        user = self._users_by_uid.get(code)
        if not user:
            raise ValueError(f"Unknown dev_stub user: {code}")
        return UserInfo(
            provider_type=self.type,
            external_id=user["uid"],
            display_name=user.get("display_name", user["uid"]),
            email=user.get("email"),
        )

    async def get_workspace_memberships(self, user_info: UserInfo) -> List[Membership]:
        user = self._users_by_uid.get(user_info.external_id)
        if not user:
            return []
        return [
            Membership(
                workspace_id=w["id"],
                role=w.get("role", "member"),
                display_name=w.get("display_name", w["id"]),
                source="dev_stub",
            )
            for w in (user.get("workspaces") or [])
        ]
