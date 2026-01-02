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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


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

    from routes import router

    _include_routers(app, [RouterConfig(router=router)])
    return app
