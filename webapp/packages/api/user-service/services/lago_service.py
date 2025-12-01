import os
import litellm
from typing import Optional

from litellm.integrations.lago import LagoLogger

from services.observability_service import get_observability_service

_lago_initialized = False


def _has_required_env() -> bool:
    return all(os.getenv(key) for key in ["LAGO_API_KEY", "LAGO_API_BASE", "LAGO_API_EVENT_CODE"])


def configure_lago_logging() -> bool:
    """Attach Lago logger callbacks to LiteLLM if configuration is present.

    Returns True if Lago logging is enabled, otherwise False.
    """
    global _lago_initialized

    if _lago_initialized:
        return True

    logger = get_observability_service()

    if not _has_required_env():
        logger.log(
            level="DEBUG",
            event_type="lago_logging_disabled",
            message="Lago environment variables not set; skipping billing callback registration.",
        )
        return False

    try:
        lago_logger = LagoLogger()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.log(
            level="ERROR",
            event_type="lago_logging_error",
            message=f"Could not initialize Lago logger: {exc}",
        )
        return False

    # Append callbacks without clobbering any previously configured hooks
    litellm.success_callback = list(litellm.success_callback or [])
    litellm.failure_callback = list(litellm.failure_callback or [])

    litellm.success_callback.append(lago_logger)
    litellm.failure_callback.append(lago_logger)

    _lago_initialized = True
    logger.log(
        level="INFO",
        event_type="lago_logging_enabled",
        message="Lago billing callbacks registered for LiteLLM.",
    )
    return True


def build_litellm_metadata(user_id: Optional[str]) -> dict:
    """Return metadata used by Lago to associate spend to a user.

    Falls back to an "anonymous" identifier so LagoLogger always
    receives an external customer id.
    """
    return {"user_api_key_user_id": user_id or "anonymous"}
