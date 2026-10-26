"""Self-hosted models served behind an OpenAI-compatible gateway.

Example configuration for a gateway (litellm, vLLM, TGI or similar) that a
deployment runs itself. Replace the entries below with whatever the gateway
serves.

Two things are worth copying even if the models are not:

CONTEXT WINDOWS ARE THE SERVING LIMIT. Set context_window to the backend's
configured limit (vLLM's --max-model-len, for instance), not the
architectural maximum from the model card. The serving limit is what
actually rejects a request, and get_context_window() feeds batch-sizing
math directly, so an aspirational number produces batches the backend
refuses at request time.

KEEP THE SERVING LIMIT AT OR BELOW THE KV CACHE SIZE. On vLLM, a
--max-model-len above the measured KV cache token count means a prompt
sized between the two is accepted and then HANGS -- no error, no timeout,
the request is simply never scheduled. Large batches land in that dead
zone while small probes do not, which makes it look intermittent and
network-like. It is neither.

Thinking behavior is declared per model here, as with every other
provider: see thinking_style and the temperature flags in
services/llm_service.py.
"""

# vLLM serving limits, per model. These are NOT interchangeable, and each is
# the INPUT budget (serving --max-model-len minus that tier's output
# reservation), NOT the raw --max-model-len. See the module docstring.
#
# Gemma serves 131,072. Minus the 32,768 max_tokens ceiling below leaves
# 98,304; 97,000 keeps ~1,300 tokens of margin at that ceiling.
_GEMMA_CONTEXT = 97000

# Qwen3.8-27B serves 131,072 as well, and takes the same 32,768 ceiling, so
# the arithmetic is identical. Kept as a separate constant deliberately: the
# two models are on different hosts with different cards, and a shared
# constant would couple them the next time one is re-served at a different
# window.
_QWEN27_CONTEXT = 97000

# Qwen3-8B serves 40,960 (its max_position_embeddings). Subtracting the 8,192
# max_tokens ceiling below leaves 32,768 of input budget with ~0 slack, so
# this is set at 30,000 to keep a real margin. 40,960 is a hard architectural
# ceiling and will not rise.
_QWEN8_CONTEXT = 30000


def _params(window, default_max_tokens, thinking_levels=()):
    """Parameter spec for one model.

    max_tokens' ceiling is that model's own served window -- a shared ceiling
    would let a caller request more output than the model can produce, which
    vLLM rejects at request time. The default is deliberately well under the
    window so the prompt always has room.
    """
    return {
        "temperature": {
            "type": "float",
            "default": 0.0,
            "min": 0.0,
            "max": 2.0,
            # 0.0 is right with thinking OFF. With thinking ON it causes
            # repetition loops, so llm_service drops an explicit 0.0 then
            # (requires_nonzero_temperature_with_thinking).
            "description": "Randomness. 0 for deterministic classification work (ignored when thinking is on).",
        },
        "top_p": {
            "type": "float",
            "default": 1.0,
            "min": 0.0,
            "max": 1.0,
            "description": "Nucleus sampling",
        },
        # Declared so a tier can CHOOSE. Without this key in the params
        # dict, the gate in llm_service.py pops it with a fallback of
        # 'disable' -- which means every call sends enable_thinking=false and
        # no tier can ever turn reasoning on.
        #
        # Binary, deliberately. vLLM's enable_thinking is a boolean and the
        # gate translates anything non-'disable' into true. Offering
        # low/medium/high would imply gradation this transport cannot
        # Default 'disable' rather than deferring to the model, because there
        # is nothing to defer TO. LiteLLM drops extra keys from
        # litellm_params at /model/new, so selfhosted's catalog cannot set a
        # per-model default; /model/info reads back with only `model` and
        # `api_base`. Deferring would mean each model's own behavior, and
        # two of three are unusable that way. Measured, "what is 17 x 23":
        #
        #     gemma4-26b    thinks only when asked  ->  fine
        #     qwen3.8-27b   thinks by default       ->    5c of content
        #     qwen3-8b      thinks by default       ->    0c of content
        #
        # A model that grades its reasoning offers those levels here too.
        # 'enable' means "on, at the model's own default" -- which on
        # qwen3.8-27b is xhigh, its MAXIMUM, so naming a level is usually
        # what you want. See that model's thinking_levels for the numbers.
        "reasoning_effort": {
            "type": "choice",
            "default": "disable",
            "choices": ["disable", "enable", *thinking_levels],
            "description": (
                "Reasoning. 'disable' sends "
                "chat_template_kwargs.enable_thinking=false; 'enable' sends "
                "true at the model's own default level. A named level is "
                "sent as chat_template_kwargs.reasoning_effort alongside it, "
                "on models that grade it."
            ),
        },
        "max_tokens": {
            "type": "integer",
            "default": default_max_tokens,
            "min": 1,
            # Output shares the served context window with the input, so no
            # single call can ask for the whole window as output.
            "max": window,
            "description": "Maximum tokens in response (shares the window with input)",
        },
    }


# The key below is the model name that ends up in the JSON body sent to
# SELFHOSTED_API_BASE. llm_service.py builds f"{litellm_provider_prefix}/{model}"
# -> "openai/gemma4-26b", and the litellm SDK strips the "openai/" provider
# prefix client-side before the request goes out, so the endpoint receives the
# bare key.
#
# These bare names are what selfhosted's gateway advertises. Confirm against the
# endpoint rather than assuming, since the SDK's prefix handling is version
# dependent:
#
#   curl -sS "$SELFHOSTED_API_BASE/models" -H "Authorization: Bearer $SELFHOSTED_API_KEY"
#
# (selfhosted routes internally with a hosted_vllm/ prefix rather than openai/,
# because litellm's openai provider translates /v1/messages to vLLM's
# /v1/responses and breaks Anthropic-shaped tool calls. That is internal to
# selfhosted and does not change what we send here.)
models = {
    # Gemma 4 26B-A4B (MoE, ~4B active) -- general/MEDIUM tier and the default
    # for interactive work. Reasoning off by default means tokens start
    # immediately, which is why this is the model that works with agents: a
    # reasoning model emits nothing for a minute while it thinks, and
    # impatient clients abandon the stream and retry.
    "gemma4-26b": {
        # No thinking_levels: measured at low/medium/xhigh on a 38k audit
        # prompt and it ignores them -- 28-32s and ~2,500-3,000c of content at
        # every setting. enable_thinking on/off is the only control that does
        # anything here.
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": True,
        # temperature 0.0 + thinking -> repetition loops in the thinking
        # block. llm_service drops an explicit 0.0 so the model default applies.
        "requires_nonzero_temperature_with_thinking": True,
        "context_window": _GEMMA_CONTEXT,
        # max_tokens ceiling is deliberately NOT the full serving window.
        #
        # (1) Output is reserved out of the SAME window as the input, so a
        #     ceiling equal to the window makes it easy for batch-sizing math
        #     to request more output than the prompt leaves room for -- the
        #     input+output>window 400 this pipeline already hit once.
        # (2) A runaway generation holds KV cache that other in-flight
        #     requests are competing for.
        #
        # 32k rather than something tighter because the failure modes are not
        # symmetric: a too-HIGH ceiling risks a hypothetical runaway request,
        # while a too-LOW one silently TRUNCATES long structured output -- a
        # consolidation emitting 20-30k of merged JSON would come back
        # unparseable, and that reads as a model-quality problem rather than a
        # config limit.
        #
        # THIS VALUE IS THE BINDING TERM FOR _GEMMA_CONTEXT. Raising it here
        # SHRINKS the usable input window. The two move together.
        "parameters": _params(32768, 16384),
    },
    # Qwen3.8 27B FP8 -- capable/HEAVY tier. Dense 27B, hybrid GatedDeltaNet
    # plus periodic full attention. Multimodal.
    #
    # Best of the three under concurrent load and the slowest per request.
    # Markedly more verbose than Gemma: 15,561 tokens on a code-generation
    # task Gemma finished in 5,277, so a ceiling that is generous for Gemma
    # can still truncate this model.
    "qwen3.8-27b": {
        # vLLM's qwen3 reasoning parser splits thinking out of content, so a
        # caller that leaves reasoning unset gets an answer with the thinking
        # already removed -- but the tokens were still SPENT producing it.
        "returns_thoughts": True,
        # False so the gate translates to enable_thinking rather than sending
        # OpenAI's scale. This model rejects "high" outright; see the
        # docstring.
        "supports_effort": False,
        # True so the gate fires and enable_thinking is SENT. Matters in the
        # false direction: this model reasons by default.
        "supports_thinking": True,
        # temperature 0.0 + thinking -> repetition loops in the thinking
        # block. llm_service drops an explicit 0.0 so the model default applies.
        "requires_nonzero_temperature_with_thinking": True,
        # Graded reasoning, sent inside chat_template_kwargs alongside
        # enable_thinking. THE DEFAULT IS XHIGH -- this model's maximum -- so
        # a call that turns thinking on without naming a level asks for
        # maximum deliberation, and that is what the pipeline has been doing.
        #
        # Measured, 38k audit prompt, 8,000 budget, three repeats, medians:
        #
        #     low      58s    3,726c thinking    6,438c content
        #     medium   78s    4,192c thinking    9,397c content
        #     xhigh   147s   23,110c thinking    4,976c content
        #
        # xhigh costs 1.9x the wall time to produce HALF the answer -- it
        # spends the budget reasoning rather than answering. medium is the
        # setting for analysis; low for latency-sensitive work.
        #
        # Requires llm_service to send the level: the gate collapses any
        # non-'disable' value into enable_thinking=true and drops the level
        # unless it checks thinking_levels. Without that change this
        # declaration is inert.
        "thinking_levels": ["low", "medium", "xhigh"],
        "context_window": _QWEN27_CONTEXT,
        "parameters": _params(32768, 16384, ["low", "medium", "xhigh"]),
    },
    # Qwen3 8B FP8 -- fast/LIGHT tier.
    "qwen3-8b": {
        "returns_thoughts": True,
        # Binary on/off only. vLLM's enable_thinking is a boolean; there is no
        # graded scale underneath it, and offering low/medium/high would imply
        # gradation this transport cannot express.
        "supports_effort": False,
        # True so llm_service's gate fires and enable_thinking is SENT.
        #
        # This is the model where it matters most. At default settings it
        # spends the entire budget reasoning and returns NO CONTENT -- 3,481
        # characters of thinking for "what is 17 x 23". A LIGHT tier MUST send
        # enable_thinking=false, which only happens when this is True and the
        # tier's reasoning_effort is 'disable' or omitted.
        "supports_thinking": True,
        # temperature 0.0 + thinking -> repetition loops in the thinking
        # block. llm_service drops an explicit 0.0 so the model default applies.
        "requires_nonzero_temperature_with_thinking": True,
        "context_window": _QWEN8_CONTEXT,
        # Ceiling 8,192 rather than the 32k the bigger models get. Two
        # reasons, and the first is binding: 40,960 serving minus this ceiling
        # leaves 32,768 for input, and _QWEN8_CONTEXT is 30,000 -- a bigger
        # ceiling eats the input budget on a model with a quarter of Gemma's
        # window.
        #
        # Second, the default of 2,048 is deliberately well above a one-line
        # answer. Thinking consumes the SAME budget as the response, so a
        # LIGHT-tier default sized for the answer alone returns content=None
        # whenever reasoning is on.
        "parameters": _params(8192, 2048),
    },
}
