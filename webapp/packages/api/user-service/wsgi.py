import os
from typing import Any

from a2wsgi import ASGIMiddleware
from fastapi import FastAPI

ALLOWED_METHODS = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
ALLOWED_HEADERS_FALLBACK = "authorization,content-type"
MAX_AGE = "3600"


def create_wsgi_app(app: FastAPI):
    """Create a WSGI-compatible wrapper for the FastAPI app."""
    return ASGIMiddleware(app)


def build_cors_headers(req: Any, *, origin_override: str | None = None):
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    origin = origin_override or req.headers.get("origin") or frontend_url or "*"
    req_headers = req.headers.get("access-control-request-headers", "")
    return {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": ALLOWED_METHODS,
        "access-control-allow-headers": req_headers or ALLOWED_HEADERS_FALLBACK,
        "access-control-max-age": MAX_AGE,
        "vary": "Origin, Access-Control-Request-Method, Access-Control-Request-Headers",
    }
