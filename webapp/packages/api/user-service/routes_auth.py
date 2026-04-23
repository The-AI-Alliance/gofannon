# webapp/packages/api/user-service/routes_auth.py
"""Phase B auth routes: /auth/providers, /auth/login/{type}, /auth/callback/{type},
/auth/logout, /auth/refresh-workspaces.

Why a separate module instead of adding to routes.py: keeps the auth
surface self-contained so it's obvious what turns on when Phase B is
enabled, and easy to disable by not including this router in
app_factory.

This router is included by app_factory only when at least one auth
provider is enabled (``ProviderRegistry.has_any()``). Pre-Phase-B
deployments mount only ``routes.router`` with no auth routes.
"""
import secrets
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from auth import get_registry
from auth.base import LoginAllow, LoginDeny
from config import settings
from dependencies import get_db
from models.auth import (
    AuthProviderInfo,
    AuthProvidersResponse,
    RefreshWorkspacesDiff,
)
from models.session import SessionUser
from services.database_service import DatabaseService
from services.session_service import SessionService, get_session_service


router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_session_svc(db: DatabaseService = Depends(get_db)) -> SessionService:
    return get_session_service(db)


def _default_redirect_uri(request: Request, provider_type: str) -> str:
    """Build the ``redirect_uri`` the provider should bounce back to.

    We compute this from the incoming request so local dev, staging,
    and prod each use the correct absolute URL without per-env config.
    """
    base = str(request.base_url).rstrip("/")
    return f"{base}/auth/callback/{provider_type}"


def _is_secure_cookie(request: Request) -> bool:
    """Secure flag is True only when the request is over HTTPS.

    Setting Secure=True on a plain-http dev server makes browsers drop
    the cookie silently. Autodetect rather than hardcode.
    """
    return request.url.scheme == "https"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/auth/providers", response_model=AuthProvidersResponse)
async def list_providers() -> AuthProvidersResponse:
    """List enabled auth providers. Unauthenticated — for LoginPage.

    Returns the legacy-firebase flag so the frontend knows whether to
    offer the old Firebase login button too during rollout.
    """
    registry = get_registry()
    auth_cfg = settings.AUTH_CONFIG or {}
    return AuthProvidersResponse(
        providers=[
            AuthProviderInfo(
                type=p.type,
                display_name=p.display_name,
                icon=p.icon_hint,
            )
            for p in registry.all_enabled()
        ],
        legacy_firebase_enabled=bool(auth_cfg.get("legacy_firebase_enabled", True)),
    )


@router.get("/auth/login/{provider_type}")
async def login_redirect(
    provider_type: str,
    request: Request,
    return_to: Optional[str] = Query(default=None),
):
    """Kick off login: redirect the browser to the provider's authorize URL.

    The ``state`` param double-duties as CSRF token and as a carrier for
    the post-login ``return_to`` URL. We stash the expected state in a
    short-lived cookie so the callback can verify it.
    """
    registry = get_registry()
    provider = registry.get(provider_type)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_type}")

    state = secrets.token_urlsafe(24)
    redirect_uri = _default_redirect_uri(request, provider_type)
    authorize_url = provider.get_authorize_url(state, redirect_uri)

    resp = RedirectResponse(url=authorize_url, status_code=302)
    # Store expected state + return_to in a short-lived cookie. Both
    # will be verified by the callback.
    resp.set_cookie(
        key="gofannon_auth_state",
        value=state,
        max_age=600,  # 10 minutes is enough for any real OAuth flow
        httponly=True,
        samesite="lax",
        secure=_is_secure_cookie(request),
    )
    if return_to:
        resp.set_cookie(
            key="gofannon_return_to",
            value=return_to,
            max_age=600,
            httponly=True,
            samesite="lax",
            secure=_is_secure_cookie(request),
        )
    return resp


@router.get("/auth/callback/{provider_type}")
async def login_callback(
    provider_type: str,
    request: Request,
    code: str = Query(...),
    state: Optional[str] = Query(default=None),
    session_svc: SessionService = Depends(_get_session_svc),
    expected_state: Optional[str] = Cookie(default=None, alias="gofannon_auth_state"),
    return_to: Optional[str] = Cookie(default=None, alias="gofannon_return_to"),
):
    """Completion of an OAuth flow.

    Validates the state cookie, exchanges the code for a UserInfo,
    queries memberships, applies the provider's login policy, and
    creates a session (or returns an error page on deny).
    """
    registry = get_registry()
    provider = registry.get(provider_type)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider_type}")

    # CSRF check: the state returned by the provider must match the
    # state we stashed in the cookie at login-init time.
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="Invalid state; possible CSRF")

    # Exchange code -> UserInfo. Any provider error becomes a 502 here;
    # the client retries from the login page.
    try:
        redirect_uri = _default_redirect_uri(request, provider_type)
        user_info = await provider.exchange_code(code, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Provider exchange failed: {e}")

    memberships = await provider.get_workspace_memberships(user_info)
    site_admins = list((settings.AUTH_CONFIG or {}).get("site_admins") or [])
    decision = await provider.evaluate_login(user_info, memberships, site_admins)

    if isinstance(decision, LoginDeny):
        # Render a minimal HTML error page. (A fancier login-denied
        # page comes with the B-2 frontend work.)
        html = _render_deny_page(decision.reason)
        return HTMLResponse(content=html, status_code=403)

    assert isinstance(decision, LoginAllow)
    session = await session_svc.create_from_login(
        user_info=user_info,
        provider_memberships=memberships,
        is_site_admin=decision.site_admin,
    )

    redirect_url = return_to or "/"
    resp = RedirectResponse(url=redirect_url, status_code=302)
    resp.set_cookie(
        key=SessionService.cookie_name(),
        value=session.id,
        max_age=int((session.expires_at - session.created_at).total_seconds()),
        httponly=True,
        samesite="lax",
        secure=_is_secure_cookie(request),
        path="/",
    )
    # Clean up the short-lived state cookies.
    resp.delete_cookie("gofannon_auth_state", path="/")
    resp.delete_cookie("gofannon_return_to", path="/")
    return resp


@router.post("/auth/logout")
async def logout(
    request: Request,
    sid: Optional[str] = Cookie(default=None, alias="gofannon_sid"),
    session_svc: SessionService = Depends(_get_session_svc),
):
    """Delete the server-side session and clear the cookie."""
    await session_svc.delete(sid)
    resp = Response(status_code=204)
    resp.delete_cookie(SessionService.cookie_name(), path="/")
    return resp


@router.post("/auth/refresh-workspaces", response_model=RefreshWorkspacesDiff)
async def refresh_workspaces(
    sid: Optional[str] = Cookie(default=None, alias="gofannon_sid"),
    session_svc: SessionService = Depends(_get_session_svc),
) -> RefreshWorkspacesDiff:
    """Re-query the provider and return the diff.

    The session cookie carries enough info to find the session and its
    provider. On success, returns the difference between old and new
    memberships so the UI can flash a toast.
    """
    session = await session_svc.get_by_id(sid)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    _, diff = await session_svc.refresh_workspaces(session)
    return RefreshWorkspacesDiff(
        added=diff.added,
        removed=diff.removed,
        role_changes=diff.role_changes,
        site_admin_changed=diff.site_admin_changed,
    )


# ---------------------------------------------------------------------------
# Dev-stub picker
# ---------------------------------------------------------------------------


@router.get("/auth/dev-stub-picker", response_class=HTMLResponse)
async def dev_stub_picker(
    request: Request,
    state: str = Query(...),
    redirect_uri: str = Query(...),
    users: str = Query(...),
) -> HTMLResponse:
    """Tiny HTML page listing configured dev_stub users.

    Clicking one does a GET to /auth/callback/dev_stub?code=<uid>&state=<state>,
    which completes the login. No OAuth involved.
    """
    user_list = [u for u in users.split(",") if u]
    if not user_list:
        return HTMLResponse(
            content="<h1>No dev_stub users configured</h1>", status_code=500
        )

    # Build the picker page. Plain HTML; no frontend code involved.
    links = "".join(
        f'<li><a href="/auth/callback/dev_stub?code={u}&state={state}">{u}</a></li>'
        for u in user_list
    )
    html = f"""<!doctype html>
<html>
  <head><title>Dev stub login</title></head>
  <body style="font-family: sans-serif; max-width: 600px; margin: 60px auto;">
    <h1>Dev stub login</h1>
    <p>Not for production. Pick a configured user to sign in as:</p>
    <ul>{links}</ul>
  </body>
</html>"""
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Self-fetch
# ---------------------------------------------------------------------------


@router.get("/auth/me", response_model=SessionUser)
async def get_me(
    sid: Optional[str] = Cookie(default=None, alias="gofannon_sid"),
    session_svc: SessionService = Depends(_get_session_svc),
) -> SessionUser:
    """Return the current session's user info. 401 if not logged in."""
    session = await session_svc.get_by_id(sid)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return SessionUser(
        uid=session.user_uid,
        display_name=session.display_name,
        email=session.email,
        provider_type=session.provider_type,
        workspaces=session.workspaces,
        is_site_admin=session.is_site_admin,
    )


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------


def _render_deny_page(reason: str) -> str:
    # Minimal self-contained HTML; no styling dependency.
    # Explicitly html-escapes the reason in case a provider's deny
    # message ever includes user-controlled text.
    import html as _html
    safe_reason = _html.escape(reason)
    return f"""<!doctype html>
<html>
  <head><title>Login denied</title></head>
  <body style="font-family: sans-serif; max-width: 600px; margin: 80px auto; text-align: center;">
    <h1>Login denied</h1>
    <p>{safe_reason}</p>
    <p><a href="/login">Back to sign-in</a></p>
  </body>
</html>"""
