# =========================================================================
# Anthropic first-party API (via Workload Identity Federation).
#
# Access is via short-lived OAuth tokens minted by exchanging an OIDC
# identity token with Anthropic's /v1/oauth/token endpoint (RFC 7523
# jwt-bearer grant). No static ANTHROPIC_API_KEY is used, and one being
# present in the container environment is treated as an error -- see
# services/anthropic_wif.py::_assert_no_static_api_key.
#
# Model IDs are the 1P model strings: no "us." region prefix, no ARN.
# litellm routes them under its "anthropic" provider prefix.
#
# SCHEMA NOTE: entries follow the same shape as every other provider in
# config/ -- a "parameters" dict of {type, default, min/max/choices,
# description}. That structure is not decorative:
#   - models/chat.py:19 builds the request schema from it
#   - dependencies.py:312 clamps caller max_tokens to parameters.max_tokens.max
#   - the agent editor UI renders its controls from it
# A config carrying flat keys like max_output_tokens or
# input_cost_per_million instead would load without error and then silently
# fail to clamp, validate, or render.
# =========================================================================


def _params(max_tokens_max, max_tokens_default=16384, effort_choices=None,
            temperature=True):
    """Build a parameters block.

    Keeps the entries below readable and makes the per-model differences
    (effort scale, output ceiling, temperature support) obvious.
    """
    p = {}
    if temperature:
        p["temperature"] = {
            "type": "float",
            "default": 1.0,
            "min": 0.0,
            "max": 1.0,
            "description": (
                "Randomness. Locked to 1.0 when thinking is enabled -- the "
                "Anthropic API rejects any other value alongside extended "
                "thinking with HTTP 400."
            ),
            "mutually_exclusive_with": ["top_p"],
        }
    p["top_p"] = {
        "type": "float",
        "default": 0.9,
        "min": 0.0,
        "max": 1.0,
        "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
        "mutually_exclusive_with": ["temperature"],
    }
    p["reasoning_effort"] = {
        "type": "choice",
        "default": "disable",
        "choices": effort_choices or ["disable", "low", "medium", "high"],
        "description": (
            "Reasoning Effort: enables extended thinking. xhigh/max are "
            "Opus 4.7 and later only."
        ),
    }
    p["max_tokens"] = {
        "type": "integer",
        "default": max_tokens_default,
        "min": 1,
        "max": max_tokens_max,
        "description": "Maximum tokens in response",
    }
    return p


_FULL_EFFORT = ["disable", "low", "medium", "high", "xhigh", "max"]
_BASE_EFFORT = ["disable", "low", "medium", "high"]

models = {
    # =====================================================================
    # Claude Opus 4.8 -- highest capability tier.
    #
    # thinking_style "adaptive": reasoning_effort becomes
    # thinking={"type": "adaptive"} + output_config={"effort": ...} rather
    # than the legacy thinking.type.enabled shape. Opus 4.7 introduced it.
    # =====================================================================
    "claude-opus-4-8": {
        "returns_thoughts": True,
        "supports_effort": True,
        "supports_thinking": True,
        "supports_prompt_caching": True,
        "thinking_style": "adaptive",
        # Anthropic rejects any temperature other than 1.0 alongside
        # extended thinking with HTTP 400.
        "rejects_temperature_with_thinking": True,
        "context_window": 200000,
        "parameters": _params(64000, 16384, _FULL_EFFORT),
    },
    # =====================================================================
    # Claude Sonnet 4.6 -- default working tier.
    # =====================================================================
    "claude-sonnet-4-6": {
        "returns_thoughts": True,
        "supports_effort": True,
        "supports_thinking": True,
        "supports_prompt_caching": True,
        # reasoning_effort, not adaptive: this is how the same model is
        # treated on bedrock, where it declares no thinking_style and so
        # takes the default. Keeping the two providers consistent means a
        # model behaves the same however it is reached.
        "thinking_style": "reasoning_effort",
        "rejects_temperature_with_thinking": True,
        "context_window": 200000,
        "parameters": _params(64000, 16384, _BASE_EFFORT),
    },
    # =====================================================================
    # Claude Haiku 4.5 -- cheap and fast tier.
    # =====================================================================
    "claude-haiku-4-5": {
        "returns_thoughts": True,
        "supports_effort": True,
        "supports_thinking": True,
        "supports_prompt_caching": True,
        "thinking_style": "reasoning_effort",
        "rejects_temperature_with_thinking": True,
        "context_window": 200000,
        "parameters": _params(32000, 8192, _BASE_EFFORT),
    },
}
