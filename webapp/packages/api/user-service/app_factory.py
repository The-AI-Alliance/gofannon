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
    """Application lifespan handler.

    Run persistence: starts two background tasks per worker:

    - The stop poller scans CouchDB every few seconds for runs this
      worker owns where stop_requested has been flipped by another
      worker handling the POST /runs/<id>/stop. It flips the local
      cancel token so the agent terminates.

    - The eviction task deletes completed run records older than the
      retention window (7 days by default).

    Both are best-effort: failures log and the task continues. On
    shutdown they're cancelled cleanly.
    """
    import asyncio
    from services.run_registry import (
        get_run_registry,
        WORKER_ID,
    )

    logger = get_observability_service()
    logger.log(
        level="INFO",
        event_type="lifecycle",
        message=f"Application startup complete (worker_id={WORKER_ID[:8]}).",
    )

    async def _stop_poller():
        # Interval picked for sub-5s perceived stop latency in the UI
        # while keeping load on CouchDB trivial. The query uses the
        # by_worker_status index so each iteration is one quick read.
        interval = 3.0
        while True:
            try:
                await asyncio.sleep(interval)
                flipped = get_run_registry().poll_owned_stops()
                if flipped:
                    logger.log(
                        level="INFO",
                        event_type="cross_worker_stop",
                        message=f"Stop poller flipped {flipped} local tokens for runs owned by this worker.",
                        metadata={"worker_id": WORKER_ID, "count": flipped},
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Don't let a transient CouchDB blip kill the poller.
                logger.log(
                    level="WARNING",
                    event_type="stop_poller_error",
                    message=f"Stop poller iteration failed: {exc}",
                )

    async def _evictor():
        # Run hourly. The eviction query uses the by_status_completed
        # index and is cheap; the bulk of cost is the actual deletes,
        # which happen rarely (only records >7d old).
        interval = 3600.0
        # First sweep after 60s so a freshly-started worker isn't
        # racing CouchDB index creation.
        await asyncio.sleep(60.0)
        while True:
            try:
                deleted = get_run_registry().evict_old_completed()
                if deleted:
                    logger.log(
                        level="INFO",
                        event_type="run_eviction",
                        message=f"Evicted {deleted} run records older than retention window.",
                        metadata={"count": deleted},
                    )
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.log(
                    level="WARNING",
                    event_type="evictor_error",
                    message=f"Eviction iteration failed: {exc}",
                )
                await asyncio.sleep(interval)

    poller_task = asyncio.create_task(_stop_poller())
    evictor_task = asyncio.create_task(_evictor())

    try:
        yield
    finally:
        for t in (poller_task, evictor_task):
            t.cancel()
        for t in (poller_task, evictor_task):
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass


def _configure_cors(app: FastAPI) -> None:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    allowed_origins = [frontend_url]
    print(f"Configured allowed CORS origins: {allowed_origins}")

    cors_options = {
        "allow_origins": allowed_origins,
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
    # install per-agent env_var overlay proxy before anything reads
    # os.environ. Idempotent.
    from services.environ_proxy import install_environ_proxy
    install_environ_proxy()

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
