"""Tests for MicrosoftProvider."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from auth.base import LoginAllow, LoginDeny, Membership, UserInfo
from auth.providers.microsoft import MicrosoftProvider


def _make_provider(**overrides):
    config = {
        "tenant_id": "11111111-2222-3333-4444-555555555555",
        "client_id": "cid",
        "client_secret": "csec",
        "mode": "allowlist",
        "allowed_groups": ["group-a-id"],
    }
    config.update(overrides)
    return MicrosoftProvider(config=config)


def _mock_httpx_responses(*responses):
    async_client = AsyncMock()
    iter_resp = iter(responses)

    async def _next_response(*_a, **_kw):
        return next(iter_resp)

    async_client.post = AsyncMock(side_effect=_next_response)
    async_client.get = AsyncMock(side_effect=_next_response)

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

class TestMicrosoftProviderInit:
    def test_missing_tenant_raises(self):
        with pytest.raises(ValueError, match="tenant_id"):
            MicrosoftProvider(config={"client_id": "a", "client_secret": "b"})

    def test_missing_client_raises(self):
        with pytest.raises(ValueError, match="client_id"):
            MicrosoftProvider(config={"tenant_id": "t"})

    def test_allowlist_requires_groups(self):
        with pytest.raises(ValueError, match="allowed_groups"):
            _make_provider(allowed_groups=[])

    def test_bad_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            _make_provider(mode="nonsense")


# --- Authorize URL ---------------------------------------------------------

class TestMicrosoftAuthorizeURL:
    def test_tenant_in_url(self):
        p = _make_provider()
        url = p.get_authorize_url(state="s", redirect_uri="https://app")
        assert "11111111-2222-3333-4444-555555555555" in url
        assert "state=s" in url
        assert "client_id=cid" in url


# --- exchange_code ---------------------------------------------------------

@pytest.mark.asyncio
class TestMicrosoftExchangeCode:
    async def test_happy_path(self):
        p = _make_provider()
        token_resp = _resp(200, {"access_token": "TOKEN"})
        me_resp = _resp(200, {
            "id": "msid-1",
            "displayName": "Alice",
            "mail": "alice@acme.com",
        })
        cm = _mock_httpx_responses(token_resp, me_resp)

        with patch("auth.providers.microsoft.httpx.AsyncClient", return_value=cm):
            info = await p.exchange_code(code="c", redirect_uri="r")

        assert info.provider_type == "microsoft"
        assert info.external_id == "msid-1"
        assert info.email == "alice@acme.com"
        assert info._access_token == "TOKEN"

    async def test_falls_back_to_userPrincipalName(self):
        """Guest accounts have mail=None; upn is the usable email."""
        p = _make_provider()
        token_resp = _resp(200, {"access_token": "T"})
        me_resp = _resp(200, {
            "id": "msid-1",
            "displayName": "Alice",
            "mail": None,
            "userPrincipalName": "alice#EXT@other.com",
        })
        cm = _mock_httpx_responses(token_resp, me_resp)
        with patch("auth.providers.microsoft.httpx.AsyncClient", return_value=cm):
            info = await p.exchange_code(code="c", redirect_uri="r")
        assert info.email == "alice#EXT@other.com"


# --- get_workspace_memberships --------------------------------------------

@pytest.mark.asyncio
class TestMicrosoftMemberships:
    async def _call(self, provider, memberof_response):
        info = UserInfo("microsoft", "msid-1", "A", "a@acme.com")
        info._access_token = "T"
        cm = _mock_httpx_responses(memberof_response)
        with patch("auth.providers.microsoft.httpx.AsyncClient", return_value=cm):
            return await provider.get_workspace_memberships(info)

    async def test_allowlist_filter(self):
        p = _make_provider(allowed_groups=["group-a-id"])
        resp = _resp(200, {"value": [
            {"id": "group-a-id", "displayName": "Group A"},
            {"id": "group-other", "displayName": "Other"},
        ]})
        result = await self._call(p, resp)
        assert [m.workspace_id for m in result] == ["group:group-a-id"]

    async def test_admin_group_promotes_role(self):
        p = _make_provider(
            allowed_groups=["group-a-id", "admin-group-id"],
            admin_groups=["admin-group-id"],
        )
        resp = _resp(200, {"value": [
            {"id": "group-a-id", "displayName": "A"},
            {"id": "admin-group-id", "displayName": "Admins"},
        ]})
        result = await self._call(p, resp)
        roles = {m.workspace_id: m.role for m in result}
        assert roles == {
            "group:group-a-id": "member",
            "group:admin-group-id": "admin",
        }

    async def test_403_returns_empty(self):
        p = _make_provider()
        resp = _resp(403, {}, text="forbidden")
        result = await self._call(p, resp)
        assert result == []


# --- evaluate_login --------------------------------------------------------

@pytest.mark.asyncio
class TestMicrosoftEvaluateLogin:
    async def test_site_admin_allowed(self):
        p = _make_provider()
        info = UserInfo("microsoft", "msid-1", "A", "a@acme.com")
        decision = await p.evaluate_login(info, [], ["microsoft:msid-1"])
        assert isinstance(decision, LoginAllow)
        assert decision.site_admin is True

    async def test_memberships_allowed(self):
        p = _make_provider()
        info = UserInfo("microsoft", "msid-1", "A", "a@acme.com")
        m = [Membership("group:x", "member", "X", "entra_group")]
        decision = await p.evaluate_login(info, m, [])
        assert isinstance(decision, LoginAllow)

    async def test_allowlist_no_memberships_denied(self):
        p = _make_provider()
        info = UserInfo("microsoft", "msid-1", "A", "a@acme.com")
        decision = await p.evaluate_login(info, [], [])
        assert isinstance(decision, LoginDeny)

    async def test_open_tenant_no_memberships_allowed(self):
        p = _make_provider(mode="open_tenant", allowed_groups=[])
        info = UserInfo("microsoft", "msid-1", "A", "a@acme.com")
        decision = await p.evaluate_login(info, [], [])
        assert isinstance(decision, LoginAllow)
