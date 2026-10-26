from .anthropic import models as anthropic_models
from .bedrock import models as bedrock_models
from .anthropic_1p import models as anthropic_1p_models
from .selfhosted import models as selfhosted_models
from .gemini import models as gemini_models
from .openai import models as openai_models
from .openrouter import models as openrouter_models
from .perplexity import models as perplexity_models
PROVIDER_CONFIG = {
    "openai": {
        "api_key_env_var": "OPENAI_API_KEY",
        "models": openai_models
    },
    "gemini": {
        "api_key_env_var": "GEMINI_API_KEY",
        "models":  gemini_models,
    },
    "perplexity": {
        "api_key_env_var": "PERPLEXITYAI_API_KEY",
        "models": perplexity_models,
    },
    "bedrock": {
        "api_key_env_var": "AWS_BEARER_TOKEN_BEDROCK",
        "models": bedrock_models
    },
    "anthropic": {
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "models": anthropic_models,
    },
    # Anthropic first-party API via Workload Identity Federation.
    #
    # No static key: an AWS STS web identity JWT is exchanged with
    # Anthropic's /v1/oauth/token endpoint for a short-lived bearer token,
    # minted per request in llm_service.
    #
    # ANTHROPIC_API_KEY MUST NOT be set in a container that uses this
    # provider. litellm prefers a static key over an injected one, so its
    # presence silently bypasses the WIF path entirely -- you would get
    # working calls on the wrong auth and no signal.
    # services/anthropic_wif.py raises if it finds one.
    #
    # The static-key "anthropic" provider above and this one therefore cannot
    # both be active in the same container. Configure one or the other.
    #
    # auth_mechanism is the dispatch key. llm_service branches on config
    # keys rather than provider names -- see the assume_role_arn pattern it
    # replaced -- so this follows the same shape.
    "anthropic-1p": {
        "auth_mechanism": "wif",
        "litellm_provider_prefix": "anthropic",
        "models": anthropic_1p_models,
    },
    # Self-hosted models behind an OpenAI-compatible gateway.
    #
    # Routed as litellm's "openai" provider: the gateway speaks the OpenAI
    # API and routes by model_name to whichever backend is serving that
    # model, so "openai" describes the hop accurately. "hosted_vllm" would
    # describe one hop further down, inside the gateway.
    #
    # Point SELFHOSTED_API_BASE at the gateway's /v1 endpoint and
    # SELFHOSTED_API_KEY at a token it accepts. The models below are
    # examples -- replace them with whatever the gateway serves, keeping
    # the same parameters shape as every other provider here.
    #
    # NOTE: a gateway that reports zero cost per call means litellm budgets
    # do not bind, and a retry loop has nothing stopping it from saturating
    # the fleet. Rate-limit at the gateway.
    "selfhosted": {
        "litellm_provider_prefix": "openai",
        "api_base_env_var": "SELFHOSTED_API_BASE",
        "api_key_env_var": "SELFHOSTED_API_KEY",
        "models": selfhosted_models,
    },
    "openrouter": {
        "api_key_env_var": "OPENROUTER_API_KEY",
        "models": openrouter_models,
    },
    "ollama": {
        "models": {
            "llama2": {
                "parameters": {
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "Controls randomness"
                    },
                    "num_predict": {
                        "type": "integer",
                        "default": 512,
                        "min": 1,
                        "max": 2048,
                        "description": "Maximum tokens to generate"
                    },
                    "top_p": {
                        "type": "float",
                        "default": 0.9,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "Nucleus sampling"
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 40,
                        "min": 1,
                        "max": 100,
                        "description": "Top-k sampling"
                    },
                    "repeat_penalty": {
                        "type": "float",
                        "default": 1.1,
                        "min": 0.0,
                        "max": 2.0,
                        "description": "Penalty for repetition"
                    }
                }
            },
            "mistral": {
                "parameters": {
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "Controls randomness"
                    },
                    "num_predict": {
                        "type": "integer",
                        "default": 512,
                        "min": 1,
                        "max": 2048,
                        "description": "Maximum tokens to generate"
                    }
                }
            }
        }
    }
}