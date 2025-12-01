import json
import os
from typing import Any

import litellm
from litellm.integrations.custom_logger import CustomLogger

from services.observability_service import get_observability_service


class ObservabilityLiteLLMLogger(CustomLogger):
    """LiteLLM callback that forwards StandardLoggingPayload to observability."""

    def __init__(self) -> None:
        super().__init__()
        self.observability = get_observability_service()
        self.logging_mode = _get_logging_mode()

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        await self._log_standard_payload(kwargs, level="INFO")

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        await self._log_standard_payload(kwargs, level="ERROR")

    async def _log_standard_payload(self, kwargs: Any, level: str) -> None:
        if self.logging_mode == "NONE":
            return

        payload = kwargs.get("standard_logging_object") if isinstance(kwargs, dict) else None
        if payload is None:
            return

        try:
            serialized_payload = json.loads(json.dumps(payload, default=str))
        except Exception:
            serialized_payload = {"error": "Failed to serialize StandardLoggingPayload"}

        status = serialized_payload.get("status", "unknown") if serialized_payload else "unknown"

        if self.logging_mode == "COST_ONLY":
            serialized_payload = {
                key: serialized_payload.get(key)
                for key in ("response_cost", "cost_breakdown")
                if serialized_payload.get(key) is not None
            }
        message = f"LiteLLM call completed with status: {status}"

        self.observability.log(
            level=level,
            event_type="litellm_call",
            message=message,
            metadata={"standardLoggingPayload": serialized_payload},
        )


_configured_logger = False


def _get_logging_mode() -> str:
    mode = os.getenv("LITELLM_LOGGING_MODE", "NONE").upper()
    return mode if mode in {"NONE", "ALL", "COST_ONLY"} else "NONE"


def ensure_litellm_logging() -> None:
    """Attach the observability logger to LiteLLM callbacks if not already set."""
    global _configured_logger
    if _configured_logger or _get_logging_mode() == "NONE":
        return

    callbacks = getattr(litellm, "callbacks", [])
    if not any(isinstance(cb, ObservabilityLiteLLMLogger) for cb in callbacks):
        callbacks.append(ObservabilityLiteLLMLogger())
        litellm.callbacks = callbacks

    _configured_logger = True


# Ensure the logger is registered when the module is imported.
ensure_litellm_logging()
