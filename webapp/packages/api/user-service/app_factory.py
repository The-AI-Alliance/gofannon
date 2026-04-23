import os
from contextlib import asynccontextmanager
from typing import Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.routes_config import RouterConfig, resolve_router_configs
from services.observability_service import (
    ObservabilityMiddleware,
    get_observability_service,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger = get_observability_service()
    logger.log(
        level="INFO",
        event_type="lifecycle",
        message="Application startup complete."
    )
    yield


def _configure_cors(app: FastAPI) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    allowed_origins = [frontend_url]
    print(f"Configured allowed CORS origins: {allowed_origins}")

    cors_options = {
        "allow_origins": ["*"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    app.add_middleware(
        CORSMiddleware,
        **cors_options,
    )
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware and not hasattr(middleware, "options"):
            setattr(middleware, "options", getattr(middleware, "kwargs", cors_options))


def _include_routers(app: FastAPI, router_configs: Iterable[RouterConfig]) -> None:
    for router_config in resolve_router_configs(router_configs):
        app.include_router(
            router_config.router,
            prefix=router_config.prefix,
            tags=router_config.tags or [],
        )


def create_app() -> FastAPI:
    """Create and configure a FastAPI application instance."""
    app = FastAPI(lifespan=lifespan)
    app.add_middleware(ObservabilityMiddleware)
    _configure_cors(app)

    # Phase B: initialize the auth provider registry from AUTH_CONFIG.
    # When no providers are configured (or Phase B is disabled), this
    # is a no-op — ProviderRegistry with no entries. The auth router
    # is only mounted when at least one provider is enabled.
    try:
        from config import settings as app_settings
        from auth import init_registry
        providers_cfg = (app_settings.AUTH_CONFIG or {}).get("providers") or []
        registry = init_registry(providers_cfg)
    except Exception as e:
        # Don't fail app startup over an auth config error; Phase B
        # just stays disabled and the legacy Firebase path keeps working.
        print(f"Warning: auth registry init failed: {e}")
        registry = None

    from routes import router
    _include_routers(app, [RouterConfig(router=router)])

    if registry is not None and registry.has_any():
        from routes_auth import router as auth_router
        _include_routers(app, [RouterConfig(router=auth_router)])

    return app
