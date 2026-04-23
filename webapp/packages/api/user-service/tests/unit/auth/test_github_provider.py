"""Tests for GitHubProvider."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth.base import LoginAllow, LoginDeny, Membership, UserInfo
from auth.providers.github import GitHubProvider


def _make_provider(**overrides):
    config = {
        "client_id": "cid",
        "client_secret": "csec",
        "mode": "allowlist",
        "allowed_orgs": ["acme-corp"],
    }
    config.update(overrides)
    return GitHubProvider(config=config)


def _mock_responses(responses_by_call):
    """Create an AsyncClient mock that returns specific responses based
    on the order of .get / .post calls.

    ``responses_by_call`` is a list of responses applied in order
    regardless of which verb is used (get vs post).
    """
    async_client = AsyncMock()
    iter_resp = iter(responses_by_call)

    async def _next(*_a, **_kw):
        return next(iter_resp)

    async_client.get = AsyncMock(side_effect=_next)
    async_client.post = AsyncMock(side_effect=_next)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=async_client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _resp(status, json_body=None, text=""):
    r = MagicMock()
    r.status_code = status
    r.json = MagicMock(return_value=json_body or {})
    r.text = text
    return r


# --- Config validation -----------------------------------------------------

class TestGitHubProviderInit:
    def test_missing_client_raises(self):
        with pytest.raises(ValueError, match="client_id"):
            GitHubProvider(config={})

    def test_allowlist_requires_orgs(self):
        with pytest.raises(ValueError, match="allowed_orgs"):
            _make_provider(allowed_orgs=[])

    def test_bad_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            _make_provider(mode="nonsense")

    def test_org_logins_normalized_to_lowercase(self):
        p = _make_provider(allowed_orgs=["ACME-Corp", "Other-ORG"])
        assert p.allowed_orgs == {"acme-corp", "other-org"}


# --- Authorize URL ---------------------------------------------------------

class TestGitHubAuthorizeURL:
    def test_shape(self):
        p = _make_provider()
        url = p.get_authorize_url(state="s", redirect_uri="r")
        assert "client_id=cid" in url
        assert "state=s" in url
        assert "read%3Aorg" in url or "read:org" in url
        assert "allow_signup=false" in url


# --- exchange_code ---------------------------------------------------------

@pytest.mark.asyncio
class TestGitHubExchangeCode:
    async def test_happy_path(self):
        p = _make_provider()
        token_resp = _resp(200, {"access_token": "TOKEN"})
        user_resp = _resp(200, {
            "login": "alice",
            "id": 12345,
            "name": "Alice A",
            "email": "alice@acme.com",
        })
        cm = _mock_responses([token_resp, user_resp])

        with patch("auth.providers.github.httpx.AsyncClient", return_value=cm):
            info = await p.exchange_code(code="c", redirect_uri="r")

        assert info.provider_type == "github"
        # external_id prefers numeric id (stable across login renames).
        assert info.external_id == "12345"
        assert info.display_name == "Alice A"
        assert info.email == "alice@acme.com"
        assert info._access_token == "TOKEN"
        assert info._login == "alice"

    async def test_200_with_error_payload_raises(self):
        """GitHub sometimes returns 200 + error instead of non-200."""
        p = _make_provider()
        token_resp = _resp(200, {
            "error": "bad_verification_code",
            "error_description": "Code expired",
        })
        cm = _mock_responses([token_resp])

        with patch("auth.providers.github.httpx.AsyncClient", return_value=cm):
            with pytest.raises(RuntimeError, match="Code expired|access_token"):
                await p.exchange_code(code="c", redirect_uri="r")


# --- get_workspace_memberships --------------------------------------------

@pytest.mark.asyncio
class TestGitHubMemberships:
    async def test_allowlist_mode_checks_configured_orgs_only(self):
        p = _make_provider(allowed_orgs=["acme-corp", "acme-internal"])
        info = UserInfo("github", "12345", "Alice", "a@acme.com")
        info._access_token = "T"
        info._login = "alice"

        # Membership responses for each allowlisted org, in order.
        # acme-corp: active admin. acme-internal: 404 (not a member).
        resp_acme_corp = _resp(200, {"state": "active", "role": "admin"})
        resp_acme_internal = _resp(404)
        cm = _mock_responses([resp_acme_corp, resp_acme_internal])

        with patch("auth.providers.github.httpx.AsyncClient", return_value=cm):
            result = await p.get_workspace_memberships(info)

        assert [m.workspace_id for m in result] == ["github:acme-corp"]
        assert result[0].role == "admin"

    async def test_pending_membership_skipped(self):
        p = _make_provider(allowed_orgs=["acme-corp"])
        info = UserInfo("github", "12345", "A", None)
        info._access_token = "T"
        info._login = "alice"

        resp_pending = _resp(200, {"state": "pending", "role": "member"})
        cm = _mock_responses([resp_pending])
        with patch("auth.providers.github.httpx.AsyncClient", return_value=cm):
            result = await p.get_workspace_memberships(info)
        assert result == []

    async def test_open_github_mode_discovers_orgs(self):
        p = _make_provider(mode="open_github", allowed_orgs=[])
        info = UserInfo("github", "12345", "A", None)
        info._access_token = "T"
        info._login = "alice"

        orgs_list = _resp(200, [
            {"login": "Acme-Corp"}, {"login": "other-org"},
        ])
        m_acme = _resp(200, {"state": "active", "role": "member"})
        m_other = _resp(200, {"state": "active", "role": "admin"})
        cm = _mock_responses([orgs_list, m_acme, m_other])
        with patch("auth.providers.github.httpx.AsyncClient", return_value=cm):
            result = await p.get_workspace_memberships(info)

        # Both orgs returned; role mapping preserved.
        by_ws = {m.workspace_id: m.role for m in result}
        assert by_ws == {
            "github:acme-corp": "member",
            "github:other-org": "admin",
        }

    async def test_403_on_membership_skips_that_org(self):
        p = _make_provider(allowed_orgs=["a-org", "b-org"])
        info = UserInfo("github", "12345", "A", None)
        info._access_token = "T"
        info._login = "alice"

        r1 = _resp(403)
        r2 = _resp(200, {"state": "active", "role": "member"})
        cm = _mock_responses([r1, r2])
        with patch("auth.providers.github.httpx.AsyncClient", return_value=cm):
            result = await p.get_workspace_memberships(info)
        assert [m.workspace_id for m in result] == ["github:b-org"]


# --- evaluate_login --------------------------------------------------------

@pytest.mark.asyncio
class TestGitHubEvaluateLogin:
    async def test_site_admin_allowed(self):
        p = _make_provider()
        info = UserInfo("github", "12345", "A", None)
        decision = await p.evaluate_login(info, [], ["github:12345"])
        assert isinstance(decision, LoginAllow)
        assert decision.site_admin is True

    async def test_memberships_allowed(self):
        p = _make_provider()
        info = UserInfo("github", "12345", "A", None)
        m = [Membership("github:acme-corp", "admin", "ACME", "github_org")]
        decision = await p.evaluate_login(info, m, [])
        assert isinstance(decision, LoginAllow)

    async def test_allowlist_no_memberships_denied(self):
        p = _make_provider()
        info = UserInfo("github", "12345", "A", None)
        decision = await p.evaluate_login(info, [], [])
        assert isinstance(decision, LoginDeny)

    async def test_open_github_no_memberships_allowed(self):
        p = _make_provider(mode="open_github", allowed_orgs=[])
        info = UserInfo("github", "12345", "A", None)
        decision = await p.evaluate_login(info, [], [])
        assert isinstance(decision, LoginAllow)
