# webapp/packages/api/user-service/auth/__init__.py
"""Auth provider registry.

Instantiates enabled providers once at startup from AUTH_CONFIG and
exposes a lookup function used by routes. New provider types are
registered in ``_PROVIDER_CLASSES`` below.
"""
from typing import Dict, List, Optional, Type

from .base import (
    AuthProvider,
    LoginAllow,
    LoginDecision,
    LoginDeny,
    Membership,
    UserInfo,
)
from .providers import AsfProvider, DevStubProvider, GitHubProvider, GoogleProvider, MicrosoftProvider


# Map provider type -> class. Adding GitHub/Google/Microsoft later is a
# one-line registration change here plus a new file under providers/.
_PROVIDER_CLASSES: Dict[str, Type[AuthProvider]] = {
    "asf": AsfProvider,
    "dev_stub": DevStubProvider,
    "github": GitHubProvider,
    "google": GoogleProvider,
    "microsoft": MicrosoftProvider,
}


class ProviderRegistry:
    """Collection of enabled AuthProvider instances.

    Constructed once at service startup from the ``providers`` list in
    ``AUTH_CONFIG``. Misconfigured providers (missing required keys,
    unknown types) are logged and skipped — failing startup would take
    down the legacy Firebase path too, which isn't acceptable.
    """

    def __init__(self, config_list: List[dict]):
        self._providers: Dict[str, AuthProvider] = {}
        for entry in config_list or []:
            if not entry.get("enabled"):
                continue
            ptype = entry.get("type")
            if ptype not in _PROVIDER_CLASSES:
                print(f"Warning: unknown auth provider type '{ptype}', skipping")
                continue
            try:
                cls = _PROVIDER_CLASSES[ptype]
                instance = cls(config=entry.get("config") or {})
                self._providers[ptype] = instance
            except Exception as e:
                print(f"Warning: failed to initialize auth provider '{ptype}': {e}")

    def get(self, provider_type: str) -> Optional[AuthProvider]:
        return self._providers.get(provider_type)

    def all_enabled(self) -> List[AuthProvider]:
        """Enabled providers in a deterministic order (sorted by type)."""
        return [self._providers[k] for k in sorted(self._providers.keys())]

    def has_any(self) -> bool:
        return bool(self._providers)


# Module-level singleton. Populated once by app startup via init_registry.
_registry: Optional[ProviderRegistry] = None


def init_registry(config_list: List[dict]) -> ProviderRegistry:
    """Build the registry from config and store it on the module.

    Called from app_factory at startup. Subsequent calls replace the
    registry — useful in tests.
    """
    global _registry
    _registry = ProviderRegistry(config_list)
    return _registry


def get_registry() -> ProviderRegistry:
    """Return the process-wide registry; empty one if not yet init'd.

    An empty registry means Phase B is disabled; callers check
    ``has_any()`` to decide whether to offer session-based auth.
    """
    global _registry
    if _registry is None:
        _registry = ProviderRegistry([])
    return _registry


__all__ = [
    "AuthProvider",
    "LoginAllow",
    "LoginDecision",
    "LoginDeny",
    "Membership",
    "UserInfo",
    "ProviderRegistry",
    "init_registry",
    "get_registry",
]
