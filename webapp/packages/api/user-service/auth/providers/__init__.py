# webapp/packages/api/user-service/auth/providers/__init__.py
"""Built-in auth providers. Each file defines one AuthProvider subclass."""
from .asf import AsfProvider
from .dev_stub import DevStubProvider
from .github import GitHubProvider
from .google import GoogleProvider
from .microsoft import MicrosoftProvider

__all__ = [
    "AsfProvider",
    "DevStubProvider",
    "GitHubProvider",
    "GoogleProvider",
    "MicrosoftProvider",
]
