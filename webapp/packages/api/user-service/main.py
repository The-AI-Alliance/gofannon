"""Entry point for running the user-service API.

This module intentionally contains no business logic so that platform-specific
entry points (e.g., Firebase, Amplify) can be swapped with minimal effort.
"""

from app_factory import create_app
from wsgi import create_wsgi_app

app = create_app()
wsgi_app = create_wsgi_app(app)

__all__ = ["app", "wsgi_app"]
