import asyncio
import json
import os
import random
import re
from config import settings
from config.provider_config import PROVIDER_CONFIG
# services.anthropic_wif (which imports boto3) is imported lazily inside the
# auth_mechanism == "wif" branches below, so a deployment without a WIF
# provider never loads it. boto3 is transitively present anyway via
# storage_service / dynamodb / observability_service.
from services.database_service import get_database_service
from services.user_service import get_user_service
from typing import Any, AsyncGenerator, Dict, List, Tuple, Optional
import litellm

from services.litellm_logger import ensure_litellm_logging
from services.observability_service import get_observability_service
from services.user_service import UserService
from services.cancel_token import check_should_stop

ensure_litellm_logging()

# Configure litellm defaults
litellm.drop_params = True
litellm.set_verbose = False

# ---------------------------------------------------------------------------
# litellm model-map registration, declared in provider config
# ---------------------------------------------------------------------------
# litellm decides several things by looking the model string up in its own
# model map: whether output_config.effort is supported (else it is DROPPED
# under drop_params, with only a log warning), cost tracking, max tokens, and
# the second gate in _supports_prompt_caching(). A model string the map does
# not know misses silently on all of them.
#
# The fix is to register an entry for that string. Which models need one, and
# what the entry says, is a fact about the model -- so it lives on the model's
# config entry, not here:
#
#     "litellm_registration": {
#         "copy_from": "<existing litellm map key>",   # optional
#         "overrides": {...},                          # merged on top
#         "aliases":   ["<other string>", ...],        # optional extra keys
#     }
#
# copy_from inherits whatever capability flags and costs litellm already knows
# rather than hand-writing them. If the source key is missing (a litellm
# upgrade renamed it) the entry is SKIPPED with a warning rather than failing
# startup -- the same guard the hard-coded block it replaced had.
#
# This replaces per-model blocks at the top of this module that patched
# litellm's map directly. Each is now a litellm_registration entry on the
# model it belongs to, in config/.


def _register_litellm_models(provider_config: Dict[str, Any]) -> List[str]:
    """Register every model that declares `litellm_registration`.

    Returns the list of keys registered, for tests and startup logging.
    Never raises: model metadata must not be able to break import.
    """
    registered: List[str] = []
    for provider_name, provider_cfg in provider_config.items():
        for model_name, model_cfg in (provider_cfg.get("models") or {}).items():
            reg = model_cfg.get("litellm_registration")
            if not reg:
                continue
            src = reg.get("copy_from")
            if src:
                if src not in litellm.model_cost:
                    print(
                        f"WARNING: {provider_name}/{model_name}: litellm model "
                        f"map has no {src!r} to copy from; not registered. "
                        f"Effort may be silently dropped for this model.",
                        flush=True,
                    )
                    continue
                info = {**litellm.model_cost[src], **(reg.get("overrides") or {})}
            else:
                info = dict(reg.get("overrides") or {})
            keys = [model_name, *(reg.get("aliases") or [])]
            try:
                litellm.register_model({k: info for k in keys})
                registered.extend(keys)
            except Exception as e:  # pragma: no cover - never fail import over metadata
                print(
                    f"WARNING: could not register {provider_name}/{model_name} "
                    f"with litellm: {e}",
                    flush=True,
                )
    return registered


_register_litellm_models(PROVIDER_CONFIG)

# Silences the "Provider List / Give Feedback" banner litellm prints via
# print() (not logging) whenever a model-registry lookup misses. Redundant for
# models registered above, but covers any other unregistered model string
# and keeps ~40% of noise out of the agent logs.
litellm.suppress_debug_info = True
# ---------------------------------------------------------------------------

# Default timeout (seconds) for LLM calls. Override with LLM_TIMEOUT_SECONDS env var.
DEFAULT_LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "600"))

# Max retries on timeout. Override with LLM_TIMEOUT_RETRIES env var.
#
# Defaulted to 0 until 2026-07-16, which meant a single hung request killed a
# whole pipeline run. Bedrock/Mantle intermittently accepts a request and then
# never responds: the same prompt+params that hangs past a 900s ceiling
# returns in ~180s on the next attempt (measured, back-to-back, same process).
# The retry path below is correct and was simply never enabled, so the first
# bad draw ended a 40-minute, ~$100 run that a 5-second backoff would have
# survived. 2 retries is the smallest number that covers a single hang.
MAX_TIMEOUT_RETRIES = int(os.getenv("LLM_TIMEOUT_RETRIES", "2"))

# Retries specifically for a rejected minted bearer token. One is
# normally enough: the retry mints a fresh token from fresh STS creds. A
# second failure means the problem isn't the token (bad trust policy,
# IMDS down), so don't spin.
MAX_AUTH_REMINT_RETRIES = int(os.getenv("LLM_AUTH_REMINT_RETRIES", "1"))

# Max retries on rate-limit / 429. Override with LLM_RATE_LIMIT_RETRIES.
# Bedrock and OpenAI both throttle on a per-minute token-bucket, so this
# needs real backoff with jitter — an immediate retry just hits the same
# empty bucket. Five attempts with exponential backoff (1, 2, 4, 8, 16s
# + jitter) gives roughly 30 seconds of patience per call, enough to
# ride through most quota refills.
MAX_RATE_LIMIT_RETRIES = int(os.getenv("LLM_RATE_LIMIT_RETRIES", "5"))

# Max retries on provider overload (HTTP 529 overloaded_error). Distinct from
# rate-limit: 529 is the provider saying "too busy right now", not a quota
# bucket. litellm surfaces it as APIConnectionError (or a generic exception
# with "overloaded" in the body), NOT as RateLimitError, so it would otherwise
# fall through to the terminal branch and permanently fail the call. It is the
# MOST retryable error there is; reuse the same exponential-backoff-with-jitter
# as rate-limit. Especially important on newer or capacity-limited endpoints
# under stacked concurrency, where transient overloads are more likely.
MAX_OVERLOADED_RETRIES = int(os.getenv("LLM_OVERLOADED_RETRIES", "5"))

# Cap on individual backoff sleep, regardless of attempt number.
RATE_LIMIT_BACKOFF_CAP_SECONDS = int(os.getenv("LLM_RATE_LIMIT_BACKOFF_CAP", "60"))


# --- Transient-failure classification ------------------------------------
#
# These predicates decide whether a provider exception is retried from the
# MAX_OVERLOADED_RETRIES budget or fails the call on first contact. They are
# module-level rather than inline in the retry loop so they can be unit-tested
# directly: see tests/unit/services/test_llm_service_retries.py.
#
# All three take the exception string ALREADY LOWERCASED, as the call site
# does with str(e).lower().


# 529 as a standalone token, not as three digits inside a longer run of
# characters. A bare `"529" in err_str` also matched a token count ("5290
# input tokens"), a truncation offset ("1529 tokens"), a model name
# ("qwen-529b") and an identifier ("req_529_ab"), each of which would open
# the retry budget for an error that then fails identically on every
# attempt. The boundaries exclude digits, letters and underscores on both
# sides, so the status code in "Error code: 529 - {...}" still matches.
_HTTP_529_RE = re.compile(r"(?<![0-9a-z_])529(?![0-9a-z_])")


def _is_overloaded_error(err_str: str) -> bool:
    """Provider overload: HTTP 529 / overloaded_error.

    litellm surfaces this as APIConnectionError or a generic exception, NOT
    RateLimitError, so it is caught in the generic handler and routed through
    the same exponential-backoff-with-jitter as rate-limit before falling
    through to the terminal error classifier. 529 means "provider busy,
    retry" and is highly likely to succeed on a backed-off retry.

    "overloaded" remains the primary matcher: a real 529 carries
    overloaded_error in its body, so narrowing the numeric test cannot lose
    a genuine overload.
    """
    return (
        "overloaded" in err_str
        or bool(_HTTP_529_RE.search(err_str))
        or "\"type\":\"overloaded_error\"" in err_str
    )


def _is_gateway_error(err_str: str) -> bool:
    """A 502 from a reverse proxy in front of the model endpoint.

    When the upstream drops the connection mid-response, the proxy answers
    502 and litellm maps it to BadGatewayError. That is the same transient
    condition as a 503 or a 500 api_error: the request never reached a
    verdict, so a backed-off retry is likely to get one.

    The tests match a class name or a full phrase, never a bare "502", so an
    error string that merely contains those digits -- a token count like
    "50200 input tokens", a model named qwen-502b -- does not open the retry
    budget.

    504 is deliberately excluded. A gateway timeout means the proxy gave up
    waiting, so if its limit is shorter than the caller's, every long call
    would 504 and then retry, each attempt burning the full proxy timeout
    before failing again -- turning one slow failure into several. It belongs
    here only once the proxy's own limit has been measured against the
    request timeouts in use.
    """
    return (
        "badgateway" in err_str
        or "bad gateway" in err_str
        or "502 proxy error" in err_str
    )


def _is_transient_5xx_error(err_str: str) -> bool:
    """Transient server-side failures from the provider.

    HTTP 500 with "api_error", litellm's ServiceUnavailableError, endpoints
    that return "The server had an error while processing your request" under
    load, and gateway-class 502s. These succeed on a backed-off retry just
    like a 529, but are NOT matched by the overloaded checks (different
    type/status), so without this they fail the call on the first hit.
    """
    return (
        "serviceunavailable" in err_str
        or "500 internal server error" in err_str
        or "\"type\":\"api_error\"" in err_str
        or "the server had an error" in err_str
        or _is_gateway_error(err_str)
    )


def _extract_response_cost(response_obj: Any) -> Optional[float]:
    standard_logging = None
    if hasattr(response_obj, "_hidden_params") and isinstance(response_obj._hidden_params, dict):
        standard_logging = response_obj._hidden_params.get("standard_logging_object")
    if isinstance(standard_logging, dict):
        try:
            cost_value = standard_logging.get("response_cost")
            if cost_value is not None:
                return float(cost_value)
        except Exception:
            pass
    usage = getattr(response_obj, "usage", None)
    if usage and getattr(usage, "total_cost", None) is not None:
        try:
            return float(getattr(usage, "total_cost"))
        except Exception:
            return None
    return None

# How a model is told to reason. One value per model, declared in provider
# config as `thinking_style`, resolved once per call by _thinking_style().
#
#   "enable_thinking"   vLLM chat-template switch: extra_body.
#                       chat_template_kwargs.enable_thinking (+ the graded
#                       level, where the model declares thinking_levels).
#                       Self-hosted models behind selfhosted.
#   "adaptive"          thinking={"type":"adaptive"} + output_config.effort,
#                       set directly so litellm does not translate
#                       reasoning_effort into the legacy thinking.type.enabled
#                       shape these models reject. Opus 4.7 and later.
#   "reasoning_effort"  pass reasoning_effort through for litellm to translate.
#                       Every other model.
#   "none"              send no reasoning parameter at all.
#
# This replaces _is_opus_4_7_or_later(), which decided the adaptive shape by
# substring-matching the model string ("claude-opus-4-7", "claude-opus-4-8",
# "claude-opus-5"). A name cannot know what a model accepts, and every new
# model meant editing that tuple. The entries it matched now declare
# "adaptive" in config.
THINKING_STYLES = ("enable_thinking", "adaptive", "reasoning_effort", "none")


def _thinking_style(provider_cfg: Dict[str, Any], model_config: Dict[str, Any]) -> str:
    """Resolve a model's thinking style from config.

    An explicit `thinking_style` wins. Otherwise the default is derived so
    that every model not declaring one behaves exactly as before:

      - a provider served from a custom OpenAI-compatible endpoint (declares
        api_base_env_var -- only selfhosted does) whose model supports_thinking
        -> "enable_thinking". This is the gate that used to sit inline in
        call_llm and stream_llm; see the comment there for why it is
        api_base_env_var and not supports_thinking alone.
      - anything else -> "reasoning_effort". Deliberately NOT keyed on
        supports_effort: reasoning_effort has always been passed through for
        every non-adaptive model, and litellm (drop_params=True) decides per
        model whether it survives. Keying on supports_effort would stop
        sending it to e.g. Sonnet and Haiku, a behavior change.

    Raises ValueError on an unknown explicit value: a typo in config should
    fail the call loudly, not fall back to a default that looks like it works.
    """
    style = model_config.get("thinking_style")
    if style is not None:
        if style not in THINKING_STYLES:
            raise ValueError(
                f"unknown thinking_style {style!r}; expected one of {THINKING_STYLES}"
            )
        return style
    if provider_cfg.get("api_base_env_var") and model_config.get("supports_thinking"):
        return "enable_thinking"
    return "reasoning_effort"


# Temperature, reconciled against what the model accepts. Three config flags,
# checked in this order; at most one of the last two may be set on a model:
#
#   rejects_temperature
#       The model rejects the parameter outright, thinking or not. Some
#       models answer HTTP 400 "`temperature` is deprecated for this model".
#       Always dropped.
#
#   rejects_temperature_with_thinking
#       Rejected while thinking is on, except 1.0. Anthropic on Bedrock and
#       via OpenRouter: HTTP 400 for temperature + thinking, documented as
#       "Locked to 1.0 when thinking enabled", so 1.0 itself is accepted and
#       kept.
#
#   requires_nonzero_temperature_with_thinking
#       0.0 with thinking on drives the model into repetition loops inside the
#       thinking block. Self-hosted selfhosted models. An explicit 0.0 is DROPPED,
#       not raised to some chosen value: vLLM then applies the model's own
#       generation_config, which is the vendor-tuned value (Gemma 4 publishes
#       1.0; the Qwen family 0.6-1.0 depending on version and mode), and
#       failing that vLLM's own default of 1.0 -- never 0. An ABSENT
#       temperature is left alone for the same reason. This matters because
#       selfhosted's config default is 0.0 ("deterministic classification"), so any
#       caller taking defaults and turning thinking on lands exactly here.
#
# This replaces a copy of the same rule in each ASVS agent's _make_tier, keyed
# on provider NAME rather than on what the model accepts, which meant any
# provider added later was missing from the set and silently unprotected.
# The non-zero rule existed there only as a comment; nothing enforced it.
_NONZERO_TEMP_WARNED: set = set()


def _reconcile_temperature(
    kwargs: Dict[str, Any],
    model_config: Dict[str, Any],
    thinking_active: bool,
    model_label: str = "",
) -> None:
    """Adjust kwargs["temperature"] in place per the model's declared flags."""
    if "temperature" not in kwargs:
        return
    if model_config.get("rejects_temperature"):
        kwargs.pop("temperature", None)
        return
    if not thinking_active:
        return
    temperature = kwargs["temperature"]
    if model_config.get("rejects_temperature_with_thinking"):
        if temperature != 1.0:
            kwargs.pop("temperature", None)
        return
    if model_config.get("requires_nonzero_temperature_with_thinking"):
        try:
            is_zero = float(temperature) == 0.0
        except (TypeError, ValueError):
            is_zero = False
        if is_zero:
            kwargs.pop("temperature", None)
            if model_label not in _NONZERO_TEMP_WARNED:
                _NONZERO_TEMP_WARNED.add(model_label)
                print(
                    f"WARNING: {model_label}: temperature=0.0 with thinking on "
                    f"causes repetition loops on this model; dropped so the "
                    f"model's own default applies. Set a non-zero temperature "
                    f"for this tier to silence this. (Logged once per model.)",
                    flush=True,
                )


def _supports_prompt_caching(provider: str, model: str) -> bool:
    """Whether this model honors cache_control ephemeral blocks.

    Declared per model in the provider config, not inferred from the name.
    The previous implementation was `"claude" in model.lower()`, which is how
    every self-hosted model came to have its cache_prefix silently discarded
    -- a name match cannot know what a model supports, and the one place that
    knowledge belongs is the config.

    litellm's own model map is still consulted as a second gate for models
    that declare support, because it knows about cases the config should not
    have to track: a model can be a Claude model and still have litellm
    report supports_prompt_caching=false, and injecting the marker anyway
    converts the first message to block form to carry a cache_control the
    model ignores -- no cache hit, and a large inventory prefix re-sent on
    every batch expecting to be cached across the pass.

    Defaults to False: a model that has not declared the capability does not
    get the marker, and llm_service delivers its cache_prefix as prepended
    text instead. Nothing is lost either way.
    """
    model_config = (
        PROVIDER_CONFIG.get(provider, {}).get("models", {}).get(model, {})
    )
    if not model_config.get("supports_prompt_caching", False):
        return False
    return litellm.model_cost.get(model, {}).get("supports_prompt_caching", True)


def _prepend_prefix_to_message(
    messages: List[Dict[str, Any]], cache_prefix: str
) -> List[Dict[str, Any]]:
    """Prepend `cache_prefix` to the first message so it ALWAYS reaches the
    model, on providers that cannot carry it as a cache_control block.

    Without this, a caller passing cache_prefix= to a non-caching provider
    has the content silently discarded. asvs_audit did exactly that: it built
    the analysis system prompt and code inventory as a cache_prefix and passed
    nothing else, so every self-hosted HEAVY call analysed raw source with no
    auditor role, no ASVS rubric and no severity guidance. It looked like the
    model finding less; it was the model being asked less.

    Returns a NEW list; the caller's is not mutated.
    """
    if not messages:
        return [{"role": "user", "content": cache_prefix}]

    new_messages = [dict(m) for m in messages]
    first = new_messages[0]
    content = first.get("content", "")

    # Guard against double delivery. A caller that both inlines the prefix
    # AND passes it as cache_prefix would otherwise send it twice -- doubling
    # an already-large prompt and handing the model its instructions two
    # times over, with nothing raising.
    if isinstance(content, str):
        if content.startswith(cache_prefix):
            return new_messages
        first["content"] = f"{cache_prefix}\n\n{content}" if content else cache_prefix
    elif isinstance(content, list):
        blocks = list(content)
        if blocks and blocks[0].get("type") == "text" \
                and (blocks[0].get("text") or "").startswith(cache_prefix):
            return new_messages
        first["content"] = [{"type": "text", "text": cache_prefix}] + blocks
    else:
        first["content"] = cache_prefix

    new_messages[0] = first
    return new_messages


def _inject_cache_prefix(
    messages: List[Dict[str, Any]], cache_prefix: str
) -> List[Dict[str, Any]]:
    """Return a NEW message list with `cache_prefix` prepended to the first
    message as its own cacheable content block. The first message's content
    is converted to block form so the prefix block can carry cache_control
    while the original content follows uncached. The caller's list is not
    mutated.

    Marker is exactly {"type": "ephemeral"} — NO ttl (Bedrock rejects ttl;
    litellm translates this OpenAI-format marker to Bedrock cachePoint)."""
    if not messages:
        return [{
            "role": "user",
            "content": [
                {"type": "text", "text": cache_prefix,
                 "cache_control": {"type": "ephemeral"}},
            ],
        }]

    new_messages = [dict(m) for m in messages]
    first = new_messages[0]
    original_content = first.get("content", "")

    prefix_block = {
        "type": "text",
        "text": cache_prefix,
        "cache_control": {"type": "ephemeral"},
    }

    if isinstance(original_content, str):
        tail_blocks = [{"type": "text", "text": original_content}] if original_content else []
    elif isinstance(original_content, list):
        tail_blocks = original_content
    else:
        tail_blocks = []

    first["content"] = [prefix_block] + tail_blocks
    new_messages[0] = first
    return new_messages


async def call_llm(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    parameters: Dict[str, Any],
    tools: Optional[List[Dict[str, Any]]] = None,
    user_service: Optional[UserService] = None,
    user_id: Optional[str] = None,
    user_basic_info: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
    cache_prefix: Optional[str] = None,
) -> Tuple[str, Any]:
    """
    Calls the specified language model using litellm, handling different API styles.
    Returns a tuple of (content, thoughts).

    Args:
        timeout: Per-call timeout in seconds. Defaults to LLM_TIMEOUT_SECONDS env var (600).
        cache_prefix: Optional large, stable text (system prompt, ASVS
            requirement text, shared inventory) to cache across calls that
            share it. When provided for a Claude model, it is sent as a
            separate content block marked cache_control={"type":"ephemeral"}
            ahead of the existing message content. litellm translates that
            marker to Bedrock's native cachePoint; cached input bills at
            ~10% on a hit. Ignored for non-Claude models and for the OpenAI
            'responses' API style (that path builds its own input from the
            original messages). Prompts under the provider minimum (2,048
            tokens for Sonnet 4.x) are silently processed without caching —
            no error — so pass only a genuinely large prefix.

            The marker carries NO ttl field: Bedrock rejects ttl (litellm
            issues #17250 / #15880); the native Anthropic API accepts it but
            we target Bedrock.
    """
    check_should_stop()  # cancel at structural boundary
    model_config = PROVIDER_CONFIG.get(provider, {}).get("models", {}).get(model, {})
    api_style = model_config.get("api_style")

    # If the provider config supplies an explicit litellm prefix (e.g.
    # anthropic-1p -> "anthropic"), use it so litellm routes
    # through its native handler for that backend. Defaults to the
    # gofannon provider key for backwards compatibility.
    provider_cfg = PROVIDER_CONFIG.get(provider, {})
    litellm_prefix = provider_cfg.get("litellm_provider_prefix", provider)
    model_string = f"{litellm_prefix}/{model}"
    
    thoughts = None
    content = ""

    # Filter out None values from parameters (e.g., top_p with default None)
    filtered_params = {k: v for k, v in parameters.items() if v is not None}

    # cache_prefix is a GUARANTEED-DELIVERED input whose transport varies by
    # capability: a cache_control block where the provider supports one,
    # prepended text where it does not. It is never dropped.
    #
    # Callers pass it ONCE and must not also inline it into the message --
    # the prepend path would then send it twice.
    #
    # The OpenAI 'responses' path below builds its own input from the
    # original `messages`, so leaving effective_messages in block-form does
    # not affect it.
    effective_messages = messages
    if cache_prefix:
        if _supports_prompt_caching(provider, model):
            effective_messages = _inject_cache_prefix(messages, cache_prefix)
        else:
            effective_messages = _prepend_prefix_to_message(messages, cache_prefix)

    kwargs = {
        "model": model_string,
        "messages": effective_messages,
        **filtered_params,
    }

    reasoning_effort = kwargs.pop('reasoning_effort', 'disable')
    # How this model is told to reason; see THINKING_STYLES. Resolved once
    # here and used by every branch below, so the selfhosted gate and the
    # adaptive/legacy split read the same decision.
    thinking_style = _thinking_style(provider_cfg, model_config)
    
    # Self-hosted reasoning models (Qwen3, Gemma 4 via selfhosted's vLLM proxy)
    # think by default. They do NOT understand OpenAI's reasoning_effort; the
    # switch is the chat-template kwarg enable_thinking, passed to vLLM via
    # extra_body. Translate our reasoning_effort intent into it.
    # reasoning_effort == 'disable' -> thinking off.
    #
    # GATE: thinking_style == "enable_thinking". By default that resolves ONLY
    # for providers served from a custom OpenAI-compatible endpoint (selfhosted ->
    # vLLM), identified by the provider declaring api_base_env_var. chat_template_kwargs is a vLLM concept, and
    # Bedrock's Converse API rejects any unknown top-level field with
    # 400 "extra_body: Extra inputs are not permitted".
    #
    # Do NOT gate on supports_thinking alone. That flag is True on the Bedrock
    # Anthropic models as well -- it means "this model can do extended
    # thinking", NOT "this model accepts enable_thinking". Gating on it alone
    # attached extra_body to Sonnet and failed every architecture
    # classification batch on 2026-07-23. api_base_env_var is the real
    # discriminator (selfhosted is the only provider that sets it), so Bedrock is
    # excluded by construction rather than by an explicit denylist.
    # (_thinking_style() now holds that derivation; test_provider_config
    # checks that no model declares "enable_thinking" explicitly on a provider
    # without api_base_env_var.)
    #
    # reasoning_effort is popped above and re-applied per style further down
    # ("reasoning_effort" passes it through, "adaptive" translates it into
    # thinking + output_config), so popping it here does not strip thinking
    # from the Bedrock tiers.
    #
    # NOTE: both selfhosted's proxy and gofannon run litellm with drop_params=True,
    # so if this param is malformed or the vLLM server lacks the matching
    # --reasoning-parser, it is silently dropped and thinking stays ON. Verify
    # with a probe call: a disabled response must have empty/no reasoning_content
    # and no <think> block. (selfhosted serves these with --reasoning-parser gemma4 /
    # qwen3; this per-call value is explicit in both directions, so it does not
    # depend on a server-side default.)
    if thinking_style == "enable_thinking":
        _enable_thinking = (reasoning_effort != 'disable')
        _extra = dict(kwargs.get("extra_body", {}))
        _ctk = dict(_extra.get("chat_template_kwargs", {}))
        _ctk["enable_thinking"] = _enable_thinking

        # Some models grade their reasoning as well as switching it on, and
        # take the level in the same chat_template_kwargs. Send it when the
        # model declares the value as one it accepts; otherwise the level is
        # our internal intent and stops here, translated into the boolean
        # above.
        #
        # This matters more than it looks. Qwen3.8-27B's levels are
        # low/medium/xhigh and ITS DEFAULT IS XHIGH -- the maximum -- so a
        # call that turns thinking on without naming a level asks for maximum
        # deliberation. Measured on a 38k audit prompt, 8,000 budget, three
        # repeats, medians:
        #
        #     low      58s    3,726c thinking    6,438c content
        #     medium   78s    4,192c thinking    9,397c content
        #     xhigh   147s   23,110c thinking    4,976c content
        #
        # xhigh costs 1.9x the wall time to produce HALF the answer: it
        # spends the budget reasoning rather than answering. Without this
        # branch every self-hosted call runs there, and the tier's setting is
        # discarded.
        if reasoning_effort in (model_config.get("thinking_levels") or ()):
            _ctk["reasoning_effort"] = reasoning_effort
        _extra["chat_template_kwargs"] = _ctk
        kwargs["extra_body"] = _extra
        # These models do not accept OpenAI's reasoning_effort: qwen3.8-27b
        # takes only xhigh/medium/low, the others reject it outright, and
        # 'enable' is not a value any of them take. The standard-completion
        # branch below therefore sends nothing further for this style.

    # Thinking is on when the caller asked for it and the model's style
    # actually sends it. Applies to every branch below, responses API included.
    _reconcile_temperature(
        kwargs, model_config,
        thinking_active=(reasoning_effort != 'disable' and thinking_style != "none"),
        model_label=f"{provider}/{model}",
    )

    if tools:
        kwargs["tools"] = tools

    # Set timeout for the LLM call
    effective_timeout = timeout or DEFAULT_LLM_TIMEOUT
    kwargs["timeout"] = effective_timeout

    if user_service is None:
        user_service = get_user_service(get_database_service(settings))
    if user_id is None:
        user_id = "anonymous"

    if user_service and user_id:
        user_service.require_allowance(user_id, basic_info=user_basic_info)

    # Get the effective API key (user's key takes precedence over env var)
    api_key = None
    if user_service and user_id:
        api_key = user_service.get_effective_api_key(user_id, provider, basic_info=user_basic_info)
    # If no user-specific key, litellm will use environment variables
    if api_key:
        kwargs["api_key"] = api_key

    # Anthropic 1P: mint a bearer token by exchanging an AWS STS web identity
    # JWT. Dispatched on a config key rather than a provider name, matching
    # the pattern the AWS bearer-token branch above uses.
    if provider_cfg.get("auth_mechanism") == "wif":
        from services.anthropic_wif import get_anthropic_1p_bearer_token
        kwargs["api_key"] = await get_anthropic_1p_bearer_token(
            # Require the token to outlive this call, not merely to be valid
            # at dispatch. 1P tokens last ~600s and HEAVY-tier calls run to
            # 1800s, so a token valid at dispatch can die mid-flight -- and
            # the retry would then replay it and fail identically, which
            # looks like a timeout cascade rather than an auth failure.
            min_validity_seconds=int(effective_timeout or 0),
        )

    # Providers served from a custom OpenAI-compatible endpoint (the selfhosted
    # provider -> selfhosted's litellm proxy). Without api_base, litellm's "openai"
    # handler would call api.openai.com. Fail loudly on a missing base rather
    # than silently sending internal prompts to a public endpoint.
    _api_base_var = provider_cfg.get("api_base_env_var")
    if _api_base_var:
        _api_base = os.environ.get(_api_base_var)
        if not _api_base:
            raise ValueError(
                f"provider '{provider}' requires {_api_base_var} to be set "
                f"(the base URL of its OpenAI-compatible endpoint); refusing "
                f"to fall back to the default OpenAI endpoint."
            )
        kwargs["api_base"] = _api_base
        # Set the key explicitly too. These providers borrow litellm's
        # "openai" handler, which would otherwise pick up OPENAI_API_KEY from
        # the environment and send it to our own proxy.
        _key_var = provider_cfg.get("api_key_env_var")
        if _key_var:
            _key = os.environ.get(_key_var)
            if not _key:
                raise ValueError(
                    f"provider '{provider}' requires {_key_var} to be set "
                    f"(a litellm virtual key for this caller)."
                )
            kwargs["api_key"] = _key


    # Only use aresponses API when we actually need its features (tools or reasoning)
    # Otherwise use standard acompletion which is more reliable
    use_responses_api = (
        api_style == "responses" and 
        (tools or reasoning_effort != 'disable')
    )

    if use_responses_api:
        # Use aresponses and aget_responses for OpenAI's special tools like built-in web search
        kwargs.pop('messages', None) # aresponses uses 'input' not 'messages'
        if reasoning_effort != 'disable':
            kwargs['reasoning'] = {'effort': reasoning_effort, 'summary': 'auto'}

        try:
            # For 'responses' API style, system prompt is 'instructions' and user prompt is 'input'
            system_prompts = [msg["content"] for msg in messages if msg["role"] == "system"]
            other_messages = [msg for msg in messages if msg["role"] != "system"]

            if system_prompts:
                kwargs["instructions"] = "\n\n".join(system_prompts)

            # Note: The 'input' for aresponses is the last user message. Conversation history is not directly supported.
            input_text = ""
            for msg in reversed(other_messages):
                if msg.get("role") == "user":
                    msg_content = msg.get("content", "")
                    if isinstance(msg_content, str):
                        input_text = msg_content
                    elif isinstance(msg_content, list):
                        # Handle list-format content (e.g., multimodal)
                        input_text = " ".join(
                            item.get("text", "") for item in msg_content 
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                    break
            
            if not input_text:
                # Fall back to standard completion if no user input found
                kwargs['messages'] = messages
                if reasoning_effort != 'disable':
                    kwargs['reasoning_effort'] = reasoning_effort
                    kwargs.pop('reasoning', None)
                response = await litellm.acompletion(**kwargs)
                message = response.choices[0].message
                content = message.content if isinstance(message.content, str) else ""
                return content, None
            
            response_obj = await litellm.aresponses(input=input_text, **kwargs)
            
            final_response = None
            for _ in range(15): # Poll for up to 30 seconds
                await asyncio.sleep(2)
                # Pass api_key to aget_responses as well (needed when using user-specific keys)
                poll_kwargs = {"response_id": response_obj.id}
                if api_key:
                    poll_kwargs["api_key"] = api_key
                response_status = await litellm.aget_responses(**poll_kwargs)
                if response_status.status == "completed":
                    final_response = response_status
                    break
            
            if final_response:
                # Helper to get attribute from object or dict
                def get_attr(obj, key, default=None):
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    return getattr(obj, key, default)
                
                # Extract thoughts/summary from the first output block
                output_list = get_attr(final_response, 'output', [])
                if len(output_list) > 0 and output_list[0]:
                    first_output = output_list[0]
                    summary = get_attr(first_output, 'summary')
                    if summary:
                        summary_texts = []
                        for s in summary:
                            text = get_attr(s, 'text')
                            if text:
                                summary_texts.append(text)
                        thoughts = {"summary": summary_texts}
                    else:
                        # Fallback for other tool outputs
                        if hasattr(first_output, 'model_dump'):
                            thoughts = first_output.model_dump()
                        elif isinstance(first_output, dict):
                            thoughts = first_output
                
                # Extract content from the second output block (or first if it's the only one with content)
                if len(output_list) > 1 and output_list[1]:
                    second_output = output_list[1]
                    second_content = get_attr(second_output, 'content')
                    if second_content and len(second_content) > 0:
                        content = get_attr(second_content[0], 'text', '')
                
                if not content and len(output_list) > 0 and output_list[0]:
                    # Fallback if there's only one output block
                    first_content = get_attr(output_list[0], 'content')
                    if first_content and len(first_content) > 0:
                        content = get_attr(first_content[0], 'text', '')
                
                # If content is still empty, try to extract from any output block
                if not content:
                    for output_item in output_list:
                        if output_item:
                            item_content = get_attr(output_item, 'content')
                            if item_content:
                                for content_block in item_content:
                                    text = get_attr(content_block, 'text', '')
                                    if text:
                                        content = text
                                        break
                            if content:
                                break
                
                # Final validation - log if we still have no content
                if not content:
                    observability = get_observability_service()
                    observability.log(
                        level="WARNING",
                        event_type="empty_response_content",
                        message="Could not extract content from aresponses API response",
                        user_id=user_id,
                        metadata={
                            "model": model_string,
                            "output_list_length": len(output_list),
                            "output_structure": str(output_list)[:500]  # Truncate for logging
                        }
                    )
            else:
                raise Exception("Polling for OpenAI Responses API timed out.")

        except Exception as e:
            observability = get_observability_service()
            
            # Check for authentication errors and provide user-friendly message
            error_str = str(e).lower()
            if "invalid_api_key" in error_str or "authentication" in error_str or "api key" in error_str:
                key_source = "user-specific" if api_key else "environment variable"
                error_msg = f"Invalid API key for {provider}. Please check your {key_source} API key in your profile settings."
                observability.log(
                    level="ERROR",
                    event_type="invalid_api_key",
                    message=error_msg,
                    user_id=user_id,
                    metadata={
                        "provider": provider,
                        "key_source": key_source,
                        "original_error": str(e)[:200],
                    }
                )
                raise ValueError(error_msg) from e
            
            # Check for context window overflow errors
            # TODO make this generalized for any provider
            if "prompt is too long" in error_str or "context_length_exceeded" in error_str or "maximum context length" in error_str:
                context_window = model_config.get("context_window", "unknown")
                error_msg = (
                    f"Prompt exceeded {model}'s context window of {context_window} tokens. "
                    f"Use hierarchical consolidation to process data in smaller groups."
                )
                observability.log(
                    level="ERROR",
                    event_type="context_window_exceeded",
                    message=error_msg,
                    user_id=user_id,
                    metadata={
                        "provider": provider,
                        "model": model,
                        "context_window": context_window,
                        "original_error": str(e)[:500],
                    }
                )
                raise ValueError(error_msg) from e

            observability.log_exception(
                e,
                user_id=user_id,
                metadata={
                    "context": "litellm.aresponses",
                    "model": model_string,
                    "provider": provider,
                }
            )
            raise
    else:
        # Standard acompletion call for most models
        if reasoning_effort != 'disable':
            if thinking_style == "adaptive":
                # Opus 4.7 and later reject the old thinking.type.enabled
                # format that litellm's reasoning_effort translation
                # produces. Set the adaptive-thinking params directly and
                # skip litellm's translation.
                kwargs['thinking'] = {'type': 'adaptive'}
                kwargs['output_config'] = {'effort': reasoning_effort}
            elif thinking_style == "reasoning_effort":
                kwargs['reasoning_effort'] = reasoning_effort
            # "enable_thinking": already sent in extra_body above.
            # "none": the model takes no reasoning parameter.

        # Retry loop. Two exception classes are retryable here:
        #   - litellm.Timeout       — slow network or model; modest linear backoff.
        #   - litellm.RateLimitError — provider throttling (Bedrock 429,
        #     OpenAI 429); needs slow exponential backoff with jitter so
        #     parallel callers don't synchronise their retries into a
        #     thundering herd.
        # Other exceptions fall through to the error-classifier branch
        # below (auth, context window, generic). Those are not retryable.
        last_exception = None
        # +MAX_AUTH_REMINT_RETRIES: an expired bearer costs an attempt, and
        # without its own budget an auth failure would eat into the timeout
        # or rate-limit allowance.
        max_attempts = (
            1
            + MAX_TIMEOUT_RETRIES
            + MAX_RATE_LIMIT_RETRIES
            + MAX_OVERLOADED_RETRIES
            + MAX_AUTH_REMINT_RETRIES
        )
        timeout_attempts_used = 0
        rate_limit_attempts_used = 0
        overloaded_attempts_used = 0
        auth_remint_attempts_used = 0

        async def _refresh_bearer_token_if_needed() -> None:
            """Re-mint the bearer before a retry.

            The token was minted before the loop. A long call (up to 1800s)
            can outlive the STS credentials that signed it, in which case
            every retry would replay the SAME dead token and fail
            identically -- which is exactly what a 3x900s "timeout" cascade
            looks like from the outside. Invalidate and re-mint so each
            attempt gets a token good for its own duration.
            """
            if provider_cfg.get("auth_mechanism") != "wif":
                return
            from services.anthropic_wif import (
                invalidate_anthropic_1p_token,
                get_anthropic_1p_bearer_token,
            )
            invalidate_anthropic_1p_token()
            kwargs["api_key"] = await get_anthropic_1p_bearer_token(
                min_validity_seconds=int(effective_timeout or 0),
            )

        for attempt in range(max_attempts):
            try:
                response = await litellm.acompletion(**kwargs)
                break  # Success
            except litellm.AuthenticationError as e:
                # Bedrock rejects an expired presigned token as an auth
                # error. The cached bearer is poisoned for this whole
                # worker, so drop it and retry with a fresh one --
                # otherwise every later call on this process inherits it.
                # Only retry for minted tokens: for a static API key a
                # re-mint changes nothing and the key is genuinely bad.
                last_exception = e
                if (
                    provider_cfg.get("auth_mechanism") == "wif"
                    and auth_remint_attempts_used < MAX_AUTH_REMINT_RETRIES
                ):
                    auth_remint_attempts_used += 1
                    print(
                        f"  Auth error on attempt {attempt + 1} for "
                        f"{model_string}; re-minting bearer token and "
                        f"retrying "
                        f"({auth_remint_attempts_used}/"
                        f"{MAX_AUTH_REMINT_RETRIES})...",
                        flush=True,
                    )
                    await _refresh_bearer_token_if_needed()
                    continue
                raise
            except litellm.Timeout as e:
                last_exception = e
                if timeout_attempts_used < MAX_TIMEOUT_RETRIES:
                    timeout_attempts_used += 1
                    wait_secs = 5 * timeout_attempts_used
                    print(
                        f"  Timeout on attempt {attempt + 1} "
                        f"for {model_string} (timeout={effective_timeout}s). "
                        f"Retrying in {wait_secs}s...",
                        flush=True,
                    )
                    await asyncio.sleep(wait_secs)
                    # A timeout is indistinguishable from an expired-token
                    # stall at this layer, so refresh before retrying.
                    await _refresh_bearer_token_if_needed()
                    continue
                raise
            except litellm.RateLimitError as e:
                last_exception = e
                if rate_limit_attempts_used < MAX_RATE_LIMIT_RETRIES:
                    # Exponential backoff with jitter. The 2**n curve
                    # plus uniform(0, n+1) jitter spreads parallel
                    # callers' retries across time so the next attempt
                    # batch doesn't arrive at the provider as
                    # synchronously as the failed batch did.
                    backoff = min(
                        RATE_LIMIT_BACKOFF_CAP_SECONDS,
                        (2 ** rate_limit_attempts_used)
                        + random.uniform(0, rate_limit_attempts_used + 1),
                    )
                    rate_limit_attempts_used += 1
                    print(
                        f"  RateLimit on attempt {attempt + 1} "
                        f"for {model_string}; sleeping {backoff:.1f}s "
                        f"(retry {rate_limit_attempts_used}/{MAX_RATE_LIMIT_RETRIES})",
                        flush=True,
                    )
                    await asyncio.sleep(backoff)
                    continue
                # Exhausted rate-limit retries. Log and re-raise so the
                # caller can decide whether to apply a domain-specific
                # fallback (e.g., the bundle's score=5 default for failed
                # relevance batches).
                observability = get_observability_service()
                observability.log_exception(
                    e,
                    user_id=user_id,
                    metadata={
                        "context": "litellm.acompletion",
                        "model": kwargs.get('model'),
                        "provider": provider,
                        "tools": kwargs.get('tools'),
                        "rate_limit_retries_exhausted": MAX_RATE_LIMIT_RETRIES,
                    }
                )
                raise
            except Exception as e:
                # Retryable provider failures -- overload (529) and transient
                # 5xx, including gateway-class 502 -- share one backoff budget
                # and are classified by the module-level predicates above, so
                # a flapping endpoint cannot exceed MAX_OVERLOADED_RETRIES in
                # total however its errors are spelled.
                _err_str = str(e).lower()
                _is_overloaded = _is_overloaded_error(_err_str)
                _is_transient_5xx = _is_transient_5xx_error(_err_str)
                if (_is_overloaded or _is_transient_5xx) and overloaded_attempts_used < MAX_OVERLOADED_RETRIES:
                    last_exception = e
                    backoff = min(
                        RATE_LIMIT_BACKOFF_CAP_SECONDS,
                        (2 ** overloaded_attempts_used)
                        + random.uniform(0, overloaded_attempts_used + 1),
                    )
                    overloaded_attempts_used += 1
                    if _is_overloaded:
                        _kind = "overloaded (529)"
                    elif _is_gateway_error(_err_str):
                        _kind = "bad gateway (502)"
                    else:
                        _kind = "server error (5xx)"
                    print(
                        f"  {_kind} on attempt {attempt + 1} "
                        f"for {model_string}; sleeping {backoff:.1f}s "
                        f"(retry {overloaded_attempts_used}/{MAX_OVERLOADED_RETRIES})",
                        flush=True,
                    )
                    await asyncio.sleep(backoff)
                    continue
                observability = get_observability_service()
                
                # Check for authentication errors and provide user-friendly message
                error_str = str(e).lower()
                if "invalid_api_key" in error_str or "authentication" in error_str or "api key" in error_str:
                    key_source = "user-specific" if api_key else "environment variable"
                    error_msg = f"Invalid API key for {provider}. Please check your {key_source} API key in your profile settings."
                    observability.log(
                        level="ERROR",
                        event_type="invalid_api_key",
                        message=error_msg,
                        user_id=user_id,
                        metadata={
                            "provider": provider,
                            "key_source": key_source,
                            "original_error": str(e)[:200],
                        }
                    )
                    raise ValueError(error_msg) from e
                
                # Check for context window overflow errors
                if "prompt is too long" in error_str or "context_length_exceeded" in error_str or "maximum context length" in error_str:
                    context_window = model_config.get("context_window", "unknown")
                    error_msg = (
                        f"Prompt exceeded {model}'s context window of {context_window} tokens. "
                        f"Use hierarchical consolidation to process data in smaller groups."
                    )
                    observability.log(
                        level="ERROR",
                        event_type="context_window_exceeded",
                        message=error_msg,
                        user_id=user_id,
                        metadata={
                            "provider": provider,
                            "model": model,
                            "context_window": context_window,
                            "original_error": str(e)[:500],
                        }
                    )
                    raise ValueError(error_msg) from e

                observability.log_exception(
                    e,
                    user_id=user_id,
                    metadata={
                        "context": "litellm.acompletion",
                        "model": kwargs.get('model'),
                        "provider": provider,
                        "tools": kwargs.get('tools'),
                    }
                )
                raise
        message = response.choices[0].message
        content = message.content if isinstance(message.content, str) else ""
        
        # Extract various forms of "thoughts"
        thoughts_payload = {}
        if message.tool_calls:
            thoughts_payload['tool_calls'] = [tc.model_dump() for tc in message.tool_calls]
        
        if hasattr(message, 'reasoning_content') and message.reasoning_content:
            thoughts_payload['reasoning_content'] = message.reasoning_content

        if isinstance(message.content, list): # Handle Anthropic's block-based content
            content_blocks = message.content
            thought_blocks = [block for block in content_blocks if block.get("type") == "thought"]
            tool_use_blocks = [block for block in content_blocks if block.get("type") == "tool_use"]
            text_blocks = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
            
            if thought_blocks:
                thoughts_payload['anthropic_thoughts'] = thought_blocks
            if tool_use_blocks:
                thoughts_payload['anthropic_tool_uses'] = tool_use_blocks
            
            content = "\n".join(text_blocks)

        thoughts = thoughts_payload if thoughts_payload else None

    # Ensure thoughts are JSON serializable
    if thoughts is not None:
        thoughts = json.loads(json.dumps(thoughts, default=str))

    if user_service and user_id:
        response_cost = None
        try:
            response_cost = _extract_response_cost(final_response if use_responses_api else response)
        except Exception:
            response_cost = None
        if response_cost is not None:
            user_service.add_usage(user_id, response_cost, basic_info=user_basic_info)

    return content, thoughts


async def stream_llm(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    parameters: Dict[str, Any],
    user_service: Optional[UserService] = None,
    user_id: Optional[str] = None,
    user_basic_info: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[Any, None]:
    """
    Stream LLM responses using litellm's async streaming.

    This function provides streaming capability while maintaining the same
    interface and checks as call_llm (user allowance, logging, etc).

    Yields chunks from the LLM response stream.

    Note: Cost tracking is not available for streaming responses.
    """
    # If the provider config supplies an explicit litellm prefix (e.g.
    # anthropic-1p -> "anthropic"), use it so litellm routes
    # through its native handler for that backend. Defaults to the
    # gofannon provider key for backwards compatibility.
    provider_cfg = PROVIDER_CONFIG.get(provider, {})
    model_config = PROVIDER_CONFIG.get(provider, {}).get("models", {}).get(model, {})
    litellm_prefix = provider_cfg.get("litellm_provider_prefix", provider)
    model_string = f"{litellm_prefix}/{model}"

    # Filter out None values from parameters
    filtered_params = {k: v for k, v in parameters.items() if v is not None}

    kwargs = {
        "model": model_string,
        "messages": messages,
        "stream": True,
        **filtered_params,
    }

    # Reasoning, mirroring the gate in call_llm.
    #
    # This previously read `kwargs.pop('reasoning_effort', None)` with the
    # note "not typically used in streaming", which discarded the caller's
    # intent without acting on it. For Bedrock that was harmless -- the
    # parameter simply went unused. For the selfhosted provider it was not: those
    # models are reached through a vLLM endpoint where reasoning is
    # controlled by chat_template_kwargs.enable_thinking, and sending nothing
    # leaves each model at ITS OWN default. Two of the three think by
    # default, and on qwen3-8b that means the whole token budget is spent
    # reasoning and the stream carries no content at all -- measured, 400
    # chunks and zero output.
    #
    # So the pop is kept (reasoning_effort must never reach vLLM: it accepts
    # that parameter on one of the three models and rejects it on the
    # others), but the value is now translated first.
    #
    # GATE: thinking_style == "enable_thinking", resolved by the same
    # _thinking_style() call_llm uses. By default that means api_base_env_var,
    # not supports_thinking alone. That flag is also True on the Bedrock
    # Anthropic models, where it means "can do extended thinking", NOT
    # "accepts enable_thinking" -- Converse rejects unknown top-level fields
    # with 400 "extra_body: Extra inputs are not permitted". Only the selfhosted
    # provider sets api_base_env_var, so Bedrock is excluded by construction
    # rather than by a denylist.
    #
    # Other styles send nothing here, as before: streaming has never passed
    # reasoning to non-selfhosted providers. Unchanged by this refactor.
    _reasoning_effort = kwargs.pop('reasoning_effort', 'disable')

    if _thinking_style(provider_cfg, model_config) == "enable_thinking":
        _extra = dict(kwargs.get("extra_body", {}))
        _ctk = dict(_extra.get("chat_template_kwargs", {}))
        _ctk["enable_thinking"] = (_reasoning_effort != 'disable')
        # Models that grade their reasoning take the level in the same place.
        # See the equivalent branch in call_llm for the measurements: on
        # qwen3.8-27b the default is xhigh, its maximum, and it costs 1.9x the
        # wall time of medium to produce half the content.
        if _reasoning_effort in (model_config.get("thinking_levels") or ()):
            _ctk["reasoning_effort"] = _reasoning_effort
        _extra["chat_template_kwargs"] = _ctk
        kwargs["extra_body"] = _extra

    # Streaming only ever sends reasoning for enable_thinking models (see the
    # gate above), so that is the only case where thinking is on here.
    # rejects_temperature still applies to every model.
    _reconcile_temperature(
        kwargs, model_config,
        thinking_active=(
            _reasoning_effort != 'disable'
            and _thinking_style(provider_cfg, model_config) == "enable_thinking"
        ),
        model_label=f"{provider}/{model}",
    )

    if user_service is None:
        user_service = get_user_service(get_database_service(settings))
    if user_id is None:
        user_id = "anonymous"

    if user_service and user_id:
        user_service.require_allowance(user_id, basic_info=user_basic_info)

    # Get the effective API key (user's key takes precedence over env var)
    api_key = None
    if user_service and user_id:
        api_key = user_service.get_effective_api_key(user_id, provider, basic_info=user_basic_info)

    # If no user-specific key, litellm will use environment variables
    if api_key:
        kwargs["api_key"] = api_key

    # Anthropic 1P: mint a short-lived bearer token at request time. The
    # token overrides any user-specific key above, since WIF auth is
    # account-scoped rather than per-user.
    if provider_cfg.get("auth_mechanism") == "wif":
        from services.anthropic_wif import get_anthropic_1p_bearer_token
        kwargs["api_key"] = await get_anthropic_1p_bearer_token(
            # Streaming has no retry loop, so a token that dies mid-stream
            # can't be recovered -- require it to cover the whole call.
            min_validity_seconds=int(kwargs.get("timeout") or 0),
        )

    # Custom OpenAI-compatible endpoint (selfhosted proxy). Same
    # reasoning as the non-streaming path: fail loudly rather than defaulting
    # to api.openai.com with OPENAI_API_KEY.
    _api_base_var = provider_cfg.get("api_base_env_var")
    if _api_base_var:
        _api_base = os.environ.get(_api_base_var)
        if not _api_base:
            raise ValueError(
                f"provider '{provider}' requires {_api_base_var} to be set."
            )
        kwargs["api_base"] = _api_base
        _key_var = provider_cfg.get("api_key_env_var")
        if _key_var:
            _key = os.environ.get(_key_var)
            if not _key:
                raise ValueError(
                    f"provider '{provider}' requires {_key_var} to be set."
                )
            kwargs["api_key"] = _key

    try:
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            yield chunk
    except Exception as e:
        observability = get_observability_service()
        observability.log_exception(
            e,
            user_id=user_id,
            metadata={
                "context": "stream_llm",
                "model": model_string,
                "provider": provider,
            }
        )
        raise