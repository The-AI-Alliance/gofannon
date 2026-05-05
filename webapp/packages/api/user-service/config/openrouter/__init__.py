# OpenRouter model catalog
# OpenRouter proxies to many upstream providers through an OpenAI-compatible API.
# litellm reads the `openrouter/<slug>` model string and the OPENROUTER_API_KEY
# env var (or the api_key we pass) to route requests.
#
# Model slugs here must match OpenRouter's canonical IDs (see https://openrouter.ai/models).
# For a model on OpenRouter listed as `x-ai/grok-code-fast-1`, the slug here is
# `x-ai/grok-code-fast-1` and the final litellm model string is
# `openrouter/x-ai/grok-code-fast-1` (produced by llm_service.py's f"{provider}/{model}").
#
# Parameter conventions:
#   - Start conservative. Only advertise `reasoning_effort` / `supports_thinking`
#     for models where OpenRouter documents native reasoning support — otherwise
#     litellm's drop_params will silently discard the user's setting.
#   - temperature and top_p are marked mutually_exclusive_with each other so the
#     UI's existing "clear one to set the other" logic works without special-casing.
#   - max_tokens upper bounds are set to match OpenRouter's documented max
#     completion length, not the context window, which is what litellm checks.
#
# Pricing as of April 2026 (see openrouter.ai/models for live rates):
#   x-ai/grok-code-fast-1             $0.20 / $1.50    per 1M tokens in/out
#   x-ai/grok-4.1-fast                $0.20 / $0.50
#   anthropic/claude-sonnet-4.5       (mirrors direct Anthropic pricing)
#   openai/gpt-5                      (mirrors direct OpenAI pricing)
#   deepseek/deepseek-v3.2            $0.27 / $0.40
#   deepseek/deepseek-chat-v3.1       $0.15 / $0.75
#   qwen/qwen3-coder                  $0.22 / $1.00
#   qwen/qwen3-coder-next             $0.15 / $0.80
#   meta-llama/llama-3.3-70b-instruct $0.13 / $0.40

# Common parameter blocks to keep each entry compact.
_STANDARD_SAMPLING = {
    "temperature": {
        "type": "float",
        "default": 0.7,
        "min": 0.0,
        "max": 2.0,
        "description": "Randomness (0=focused, 2=creative)",
        "mutually_exclusive_with": ["top_p"],
    },
    "top_p": {
        "type": "float",
        "default": 0.9,
        "min": 0.0,
        "max": 1.0,
        "description": "Nucleus sampling",
        "mutually_exclusive_with": ["temperature"],
    },
}


def _make_entry(
    context_window: int,
    max_output: int,
    default_output: int = 4096,
    supports_effort: bool = False,
    supports_thinking: bool = False,
    returns_thoughts: bool = False,
):
    """Build a PROVIDER_CONFIG model entry with sensible defaults."""
    params = {
        **_STANDARD_SAMPLING,
        "max_tokens": {
            "type": "integer",
            "default": min(default_output, max_output),
            "min": 1,
            "max": max_output,
            "description": "Maximum tokens in response",
        },
    }
    if supports_effort:
        params["reasoning_effort"] = {
            "type": "choice",
            "default": "disable",
            "choices": ["disable", "low", "medium", "high"],
            "description": "Enables extended thinking and controls effort level",
        }
    return {
        "returns_thoughts": returns_thoughts,
        "supports_effort": supports_effort,
        "supports_thinking": supports_thinking,
        "context_window": context_window,
        "parameters": params,
    }


models = {
    # =========================================================================
    # xAI — coding + fast agentic
    # =========================================================================
    # Grok Code Fast 1: economical reasoning model optimized for agentic coding.
    # Reasoning traces are visible in responses.
    "x-ai/grok-code-fast-1": _make_entry(
        context_window=256_000,
        max_output=10_000,
        default_output=8_192,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),
    # Grok 4.1 Fast: xAI's best agentic tool-calling model. 2M context.
    # Reasoning is toggleable; we advertise reasoning_effort so it can be used
    # for both quick turns (disable) and heavier tool-calling (medium/high).
    "x-ai/grok-4.1-fast": _make_entry(
        context_window=2_000_000,
        max_output=32_000,
        default_output=8_192,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),

    # =========================================================================
    # Anthropic via OpenRouter — for users who want one OpenRouter bill
    # =========================================================================
    # Pinned to the stable dated slug so upstream rollouts don't change behavior.
    # max_output is conservative (64k); bump to 128k if Anthropic raises the cap
    # on this slug and OpenRouter mirrors it.
    "anthropic/claude-sonnet-4.5": _make_entry(
        context_window=200_000,
        max_output=64_000,
        default_output=16_384,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),
    "anthropic/claude-opus-4.1": _make_entry(
        context_window=200_000,
        max_output=32_000,
        default_output=16_384,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),

    # =========================================================================
    # OpenAI via OpenRouter
    # =========================================================================
    "openai/gpt-5": _make_entry(
        context_window=400_000,
        max_output=128_000,
        default_output=16_384,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),
    "openai/gpt-5-mini": _make_entry(
        context_window=400_000,
        max_output=128_000,
        default_output=8_192,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),

    # =========================================================================
    # DeepSeek — open-weight, strong coding, cheap
    # =========================================================================
    # V3.2: reasoning-capable hybrid model; enable `reasoning_effort` to switch it on.
    "deepseek/deepseek-v3.2": _make_entry(
        context_window=131_072,
        max_output=32_768,
        default_output=8_192,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),
    # V3.1: smaller context, hybrid reasoning, cheapest option for coding drafts.
    "deepseek/deepseek-chat-v3.1": _make_entry(
        context_window=32_768,
        max_output=7_168,
        default_output=4_096,
        supports_effort=True,
        supports_thinking=True,
        returns_thoughts=True,
    ),

    # =========================================================================
    # Qwen — open-weight, coding-focused
    # =========================================================================
    # Qwen3-Coder 480B: repo-scale coding, function calling, agentic tool use.
    # Non-thinking only, so no reasoning_effort advertised.
    "qwen/qwen3-coder": _make_entry(
        context_window=262_144,
        max_output=65_536,
        default_output=8_192,
    ),
    # Qwen3-Coder-Next: lightweight 80B MoE (3B active), great for always-on
    # agent deployment. Non-thinking only.
    "qwen/qwen3-coder-next": _make_entry(
        context_window=262_144,
        max_output=32_768,
        default_output=8_192,
    ),

    # =========================================================================
    # Meta Llama — solid general-purpose open-weight
    # =========================================================================
    "meta-llama/llama-3.3-70b-instruct": _make_entry(
        context_window=131_072,
        max_output=4_096,
        default_output=2_048,
    ),
}
