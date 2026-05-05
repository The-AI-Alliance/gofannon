# webapp/packages/api/user-service/auth/ldap_client.py
"""Thin wrapper around ldap3 for ASF workspace-membership queries.

ASF's directory lives at ``ldap-eu.apache.org`` and organizes group
memberships as:

    ou=project,ou=groups,dc=apache,dc=org
        cn=tomcat              (committer group: attr memberUid=[...])
        cn=httpd
        ...
    ou=pmc,ou=project,ou=groups,dc=apache,dc=org
        cn=tomcat              (PMC group: attr member=[dn, ...])
        cn=httpd
        ...
    ou=groups,dc=apache,dc=org
        cn=asf-banned          (banned users: attr memberUid or member)

All three are read anonymously by default. This module keeps the
queries small and well-labeled so adding a new ASF-sourced workspace
type later is mechanical.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Set


# Default DNs. Override via AUTH_CONFIG["providers"][asf]["config"] if
# a test/staging LDAP is needed.
DEFAULT_SERVER = "ldaps://ldap-eu.apache.org"
DEFAULT_COMMITTER_BASE = "ou=project,ou=groups,dc=apache,dc=org"
DEFAULT_PMC_BASE = "ou=pmc,ou=project,ou=groups,dc=apache,dc=org"
DEFAULT_BANNED_GROUP = "cn=asf-banned,ou=groups,dc=apache,dc=org"


@dataclass
class AsfMembershipSnapshot:
    """Result of a single LDAP query pass.

    Includes enough info to compute workspace memberships deterministically.
    """
    # Committer group slugs the user is in (e.g. {"tomcat", "httpd"}).
    committer_groups: Set[str] = field(default_factory=set)
    # PMC group slugs. Intersection with committer_groups = admin roles.
    pmc_groups: Set[str] = field(default_factory=set)
    # True if the user is on the banned group — denies login regardless
    # of committer status.
    is_banned: bool = False
    # True if the LDAP query actually ran and returned a result. When
    # False (e.g. LDAP unavailable), callers use the soft-fail policy:
    # keep the existing session memberships rather than revoking.
    query_succeeded: bool = False


class LdapClient:
    """Synchronous LDAP client.

    Synchronous on purpose — the ``ldap3`` library doesn't ship a
    native async client, and our query volume is low (once per login,
    once per 15-minute refresh). Callers run this in a thread executor
    when they need to avoid blocking an async event loop.
    """

    def __init__(
        self,
        server: str = DEFAULT_SERVER,
        committer_base: str = DEFAULT_COMMITTER_BASE,
        pmc_base: str = DEFAULT_PMC_BASE,
        banned_group: str = DEFAULT_BANNED_GROUP,
        bind_dn: Optional[str] = None,
        bind_password: Optional[str] = None,
        timeout_seconds: int = 10,
    ):
        self.server = server
        self.committer_base = committer_base
        self.pmc_base = pmc_base
        self.banned_group = banned_group
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.timeout_seconds = timeout_seconds

    def get_memberships(self, uid: str) -> AsfMembershipSnapshot:
        """Query committer + PMC + banned groups for a uid.

        On any LDAP error, returns ``AsfMembershipSnapshot(query_succeeded=False)``
        rather than raising. Callers apply the soft-fail policy: don't
        revoke existing session memberships on LDAP outages.
        """
        try:
            import ldap3
        except ImportError:
            # ldap3 isn't installed. This shouldn't happen in a real
            # Phase B deployment (it's in requirements.txt) but we
            # degrade gracefully in dev environments that skip it.
            print("Warning: ldap3 not installed; ASF LDAP queries disabled")
            return AsfMembershipSnapshot(query_succeeded=False)

        try:
            server = ldap3.Server(self.server, connect_timeout=self.timeout_seconds)
            if self.bind_dn:
                conn = ldap3.Connection(
                    server,
                    user=self.bind_dn,
                    password=self.bind_password,
                    auto_bind=True,
                    receive_timeout=self.timeout_seconds,
                )
            else:
                conn = ldap3.Connection(
                    server,
                    auto_bind=True,
                    receive_timeout=self.timeout_seconds,
                )

            snapshot = AsfMembershipSnapshot(query_succeeded=True)

            # Committer groups: posix-style with memberUid attribute.
            conn.search(
                search_base=self.committer_base,
                search_filter=f"(&(objectClass=posixGroup)(memberUid={_escape_filter(uid)}))",
                attributes=["cn"],
            )
            snapshot.committer_groups = {
                str(entry.cn.value) for entry in conn.entries if entry.cn.value
            }

            # PMC groups: groupOfNames-style with member=DN attribute.
            # The user's DN follows the pattern uid=jdoe,ou=people,dc=apache,dc=org.
            user_dn = f"uid={_escape_filter(uid)},ou=people,dc=apache,dc=org"
            conn.search(
                search_base=self.pmc_base,
                search_filter=f"(&(objectClass=groupOfNames)(member={user_dn}))",
                attributes=["cn"],
            )
            snapshot.pmc_groups = {
                str(entry.cn.value) for entry in conn.entries if entry.cn.value
            }

            # Banned group: check membership in a single known group.
            conn.search(
                search_base=self.banned_group,
                search_scope=ldap3.BASE,
                search_filter="(objectClass=*)",
                attributes=["memberUid", "member"],
            )
            if conn.entries:
                banned_entry = conn.entries[0]
                member_uids = set(banned_entry.memberUid.values) if "memberUid" in banned_entry else set()
                dn_members = set(banned_entry.member.values) if "member" in banned_entry else set()
                snapshot.is_banned = (
                    uid in member_uids
                    or user_dn in dn_members
                )

            conn.unbind()
            return snapshot

        except Exception as e:
            # Soft-fail: log and return query_succeeded=False. The
            # calling code inspects this flag and decides whether to
            # revoke or preserve existing memberships.
            print(f"Warning: ASF LDAP query failed for uid={uid}: {e}")
            return AsfMembershipSnapshot(query_succeeded=False)


def _escape_filter(value: str) -> str:
    """Escape LDAP filter special characters per RFC 4515.

    Defensive against a malicious uid like ``*)(objectClass=*``.
    """
    replacements = [
        ("\\", "\\5c"),
        ("*", "\\2a"),
        ("(", "\\28"),
        (")", "\\29"),
        ("\0", "\\00"),
    ]
    for src, dst in replacements:
        value = value.replace(src, dst)
    return value
