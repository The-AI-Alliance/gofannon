"""Tests for GoogleProvider.

Mocks httpx.AsyncClient to avoid real network calls. Covers:
    - Config validation (missing required fields, bad mode)
    - Authorize URL shape
    - exchange_code: happy path, hosted-domain enforcement, errors
    - get_workspace_memberships: allowlist filter, role mapping, 403 soft-fail
    - evaluate_login: site_admin / memberships / open_domain / deny
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth.base import LoginAllow, LoginDeny, UserInfo
from auth.providers.google import GoogleProvider


# --- Helpers ---------------------------------------------------------------

def _make_provider(**overrides) -> GoogleProvider:
    config = {
        "client_id": "cid",
        "client_secret": "csec",
        "hosted_domain": "acme.com",
        "mode": "allowlist",
        "allowed_groups": ["engineering@acme.com"],
    }
    config.update(overrides)
    return GoogleProvider(config=config)


def _mock_httpx_responses(*responses):
    """Return an AsyncMock that, when used as httpx.AsyncClient(),
    yields successive responses for .post/.get calls in order."""
    async_client = AsyncMock()
    iter_resp = iter(responses)

    async def _next_response(*_args, **_kwargs):
        return next(iter_resp)

    async_client.post = AsyncMock(side_effect=_next_response)
    async_client.get = AsyncMock(side_effect=_next_response)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=async_client)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


def _resp(status: int, json_body: dict = None, text: str = ""):
    r = MagicMock()
    r.status_code = status
    r.json = MagicMock(return_value=json_body or {})
    r.text = text
    return r


# --- Config validation -----------------------------------------------------

class TestGoogleProviderInit:
    def test_missing_client_id_raises(self):
        with pytest.raises(ValueError, match="client_id"):
            GoogleProvider(config={"client_secret": "x", "hosted_domain": "acme.com"})

    def test_missing_hosted_domain_raises(self):
        with pytest.raises(ValueError, match="hosted_domain"):
            GoogleProvider(config={"client_id": "a", "client_secret": "b"})

    def test_bad_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            _make_provider(mode="nonsense")

    def test_allowlist_mode_requires_allowed_groups(self):
        with pytest.raises(ValueError, match="allowed_groups"):
            _make_provider(allowed_groups=[])

    def test_open_domain_without_allowed_groups_is_ok(self):
        # In open_domain mode the allowed_groups list is optional.
        p = _make_provider(mode="open_domain", allowed_groups=[])
        assert p.mode == "open_domain"


# --- Authorize URL ---------------------------------------------------------

class TestGoogleAuthorizeURL:
    def test_includes_required_params(self):
        p = _make_provider()
        url = p.get_authorize_url(state="abc", redirect_uri="https://app/x")
        assert "client_id=cid" in url
        assert "state=abc" in url
        assert "hd=acme.com" in url
        assert "scope=" in url
        assert "redirect_uri=" in url


# --- exchange_code ---------------------------------------------------------

@pytest.mark.asyncio
class TestGoogleExchangeCode:
    async def test_happy_path(self):
        p = _make_provider()
        token_resp = _resp(200, {"access_token": "TOKEN"})
        userinfo_resp = _resp(200, {
            "sub": "12345", "email": "a@acme.com", "name": "Alice",
            "hd": "acme.com",
        })
        cm = _mock_httpx_responses(token_resp, userinfo_resp)

        with patch("auth.providers.google.httpx.AsyncClient", return_value=cm):
            info = await p.exchange_code(code="c", redirect_uri="r")

        assert info.provider_type == "google"
        assert info.external_id == "12345"
        assert info.email == "a@acme.com"
        assert info._access_token == "TOKEN"  # stashed for groups call

    async def test_wrong_hosted_domain_rejected(self):
        p = _make_provider()
        token_resp = _resp(200, {"access_token": "TOKEN"})
        # hd=other.com — should be rejected
        userinfo_resp = _resp(200, {
            "sub": "12345", "email": "a@other.com", "hd": "other.com",
        })
        cm = _mock_httpx_responses(token_resp, userinfo_resp)

        with patch("auth.providers.google.httpx.AsyncClient", return_value=cm):
            with pytest.raises(RuntimeError, match="hosted domain"):
                await p.exchange_code(code="c", redirect_uri="r")

    async def test_token_exchange_error_raises(self):
        p = _make_provider()
        token_resp = _resp(400, {}, text="invalid_grant")
        cm = _mock_httpx_responses(token_resp)

        with patch("auth.providers.google.httpx.AsyncClient", return_value=cm):
            with pytest.raises(RuntimeError, match="token exchange"):
                await p.exchange_code(code="c", redirect_uri="r")


# --- get_workspace_memberships --------------------------------------------

@pytest.mark.asyncio
class TestGoogleMemberships:
    async def _call(self, provider, groups_response):
        info = UserInfo(
            provider_type="google", external_id="sub1",
            display_name="A", email="a@acme.com",
        )
        info._access_token = "T"
        cm = _mock_httpx_responses(groups_response)
        with patch("auth.providers.google.httpx.AsyncClient", return_value=cm):
            return await provider.get_workspace_memberships(info)

    async def test_allowlist_filters_non_allowed(self):
        p = _make_provider(allowed_groups=["engineering@acme.com"])
        resp = _resp(200, {"groups": [
            {"email": "engineering@acme.com", "name": "Eng", "role": "MEMBER"},
            {"email": "social@acme.com", "name": "Social", "role": "OWNER"},
        ]})
        result = await self._call(p, resp)
        assert [m.workspace_id for m in result] == ["group:engineering@acme.com"]

    async def test_role_mapping(self):
        p = _make_provider(allowed_groups=["a@acme.com", "b@acme.com", "c@acme.com"])
        resp = _resp(200, {"groups": [
            {"email": "a@acme.com", "role": "OWNER"},
            {"email": "b@acme.com", "role": "MANAGER"},
            {"email": "c@acme.com", "role": "MEMBER"},
        ]})
        result = await self._call(p, resp)
        roles = {m.workspace_id: m.role for m in result}
        assert roles == {
            "group:a@acme.com": "admin",
            "group:b@acme.com": "admin",
            "group:c@acme.com": "member",
        }

    async def test_forbidden_returns_empty(self):
        """403 from Admin SDK is common; soft-fail to empty."""
        p = _make_provider()
        resp = _resp(403, {}, text="Not authorized")
        result = await self._call(p, resp)
        assert result == []

    async def test_no_access_token_returns_empty(self):
        p = _make_provider()
        info = UserInfo(
            provider_type="google", external_id="sub1",
            display_name="A", email="a@acme.com",
        )
        # No _access_token attached — simulates the refresh path.
        result = await p.get_workspace_memberships(info)
        assert result == []


# --- evaluate_login --------------------------------------------------------

@pytest.mark.asyncio
class TestGoogleEvaluateLogin:
    async def test_site_admin_allowed_without_memberships(self):
        p = _make_provider()
        info = UserInfo("google", "sub1", "A", "a@acme.com")
        decision = await p.evaluate_login(info, [], ["google:sub1"])
        assert isinstance(decision, LoginAllow)
        assert decision.site_admin is True

    async def test_member_allowed(self):
        p = _make_provider()
        info = UserInfo("google", "sub1", "A", "a@acme.com")
        from auth.base import Membership
        m = [Membership("group:eng", "member", "Eng", "google_group")]
        decision = await p.evaluate_login(info, m, [])
        assert isinstance(decision, LoginAllow)
        assert decision.site_admin is False

    async def test_allowlist_no_memberships_denied(self):
        p = _make_provider(mode="allowlist")
        info = UserInfo("google", "sub1", "A", "a@acme.com")
        decision = await p.evaluate_login(info, [], [])
        assert isinstance(decision, LoginDeny)

    async def test_open_domain_no_memberships_allowed(self):
        p = _make_provider(mode="open_domain", allowed_groups=[])
        info = UserInfo("google", "sub1", "A", "a@acme.com")
        decision = await p.evaluate_login(info, [], [])
        assert isinstance(decision, LoginAllow)
