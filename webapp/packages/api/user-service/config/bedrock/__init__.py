# AWS Bedrock models configuration
# Updated February 2026
# Uses AWS_BEARER_TOKEN_BEDROCK for simplified API key authentication
# For cross-region inference models, use the "us." prefix (e.g., us.anthropic.claude-opus-4-5-20251101-v1:0)
#
# Note: LiteLLM translates reasoning_effort to Bedrock's thinking parameter
# Note: Claude 4.5 models cannot use both temperature and top_p together

models = {
    # =========================================================================
    # Anthropic Claude 4.5 family (Latest - November 2025)
    # - All support extended thinking via reasoning_effort
    # - Opus 4.5 supports effort parameter for token budget control
    # - Cannot specify both temperature and top_p
    # =========================================================================
    "us.anthropic.claude-opus-4-5-20251101-v1:0": {
        "returns_thoughts": True,
        "supports_effort": True,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative). Locked to 1.0 when thinking enabled.",
                "mutually_exclusive_with": ["top_p"]
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
                "mutually_exclusive_with": ["temperature"]
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Enables extended thinking and controls effort level"
            },
            "max_tokens": {
                "type": "integer",
                "default": 16384,
                "min": 1,
                "max": 64000,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative). Locked to 1.0 when thinking enabled.",
                "mutually_exclusive_with": ["top_p"]
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
                "mutually_exclusive_with": ["temperature"]
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Enables extended thinking and controls effort level"
            },
            "max_tokens": {
                "type": "integer",
                "default": 16384,
                "min": 1,
                "max": 64000,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative). Locked to 1.0 when thinking enabled.",
                "mutually_exclusive_with": ["top_p"]
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
                "mutually_exclusive_with": ["temperature"]
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Enables extended thinking and controls effort level"
            },
            "max_tokens": {
                "type": "integer",
                "default": 16384,
                "min": 1,
                "max": 64000,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Anthropic Claude 4.x family
    # - All support extended thinking
    # - Cannot specify both temperature and top_p
    # =========================================================================
    "us.anthropic.claude-opus-4-1-20250805-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative). Locked to 1.0 when thinking enabled.",
                "mutually_exclusive_with": ["top_p"]
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
                "mutually_exclusive_with": ["temperature"]
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Enables extended thinking and controls effort level"
            },
            "max_tokens": {
                "type": "integer",
                "default": 16384,
                "min": 1,
                "max": 64000,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.anthropic.claude-sonnet-4-20250514-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative). Locked to 1.0 when thinking enabled.",
                "mutually_exclusive_with": ["top_p"]
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
                "mutually_exclusive_with": ["temperature"]
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Enables extended thinking and controls effort level"
            },
            "max_tokens": {
                "type": "integer",
                "default": 16384,
                "min": 1,
                "max": 64000,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Anthropic Claude 3.5 family (Legacy) - No extended thinking support
    # =========================================================================
    "us.anthropic.claude-3-5-haiku-20241022-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)",
                "mutually_exclusive_with": ["top_p"]
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
                "mutually_exclusive_with": ["temperature"]
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)",
                "mutually_exclusive_with": ["top_p"]
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (0.1=conservative, 0.95=diverse)",
                "mutually_exclusive_with": ["temperature"]
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 4096,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Amazon Nova family
    # =========================================================================
    "us.amazon.nova-premier-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 10000,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.amazon.nova-pro-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 5000,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.amazon.nova-lite-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 5000,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.amazon.nova-micro-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 5000,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.amazon.nova-2-lite-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness (incompatible with reasoning_effort)"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling (incompatible with reasoning_effort)"
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Enable extended thinking. Note: temperature/top_p must not be set when using reasoning."
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 5000,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Meta Llama 4 family
    # =========================================================================
    "us.meta.llama4-maverick-17b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.meta.llama4-scout-17b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Meta Llama 3.3 family
    # =========================================================================
    "us.meta.llama3-3-70b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Meta Llama 3.2 family
    # =========================================================================
    "us.meta.llama3-2-90b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.meta.llama3-2-11b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.meta.llama3-2-3b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.meta.llama3-2-1b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Meta Llama 3.1 family
    # =========================================================================
    "us.meta.llama3-1-405b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.meta.llama3-1-70b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.meta.llama3-1-8b-instruct-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 2048,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # DeepSeek models
    # =========================================================================
    "us.deepseek.r1-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "deepseek.v3-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Enable thinking mode for chain-of-thought reasoning"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Mistral AI models
    # =========================================================================
    "mistral.mistral-large-3-675b-instruct": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.mistral.pixtral-large-2502-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "mistral.magistral-small-2509": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "mistral.ministral-3-14b-instruct": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "mistral.ministral-3-8b-instruct": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "mistral.mistral-large-2407-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Qwen models (support hybrid thinking - on by default, use show_thinking to control output)
    # =========================================================================
    "qwen.qwen3-235b-a22b-2507-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "show_thinking": {
                "type": "boolean",
                "default": True,
                "description": "Show thinking content in output (Qwen3 thinking is on by default)"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "qwen.qwen3-32b-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "show_thinking": {
                "type": "boolean",
                "default": True,
                "description": "Show thinking content in output (Qwen3 thinking is on by default)"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "qwen.qwen3-coder-480b-a35b-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "show_thinking": {
                "type": "boolean",
                "default": True,
                "description": "Show thinking content in output (Qwen3 thinking is on by default)"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "qwen.qwen3-coder-30b-a3b-v1:0": {
        "returns_thoughts": True,
        "supports_effort": False,
        "supports_thinking": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "show_thinking": {
                "type": "boolean",
                "default": True,
                "description": "Show thinking content in output (Qwen3 thinking is on by default)"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Writer models
    # =========================================================================
    "us.writer.palmyra-x5-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "us.writer.palmyra-x4-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # AI21 Labs models
    # =========================================================================
    "ai21.jamba-1-5-large-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 4096,
                "description": "Maximum tokens in response"
            },
        }
    },
    "ai21.jamba-1-5-mini-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 4096,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Cohere models
    # =========================================================================
    "cohere.command-r-plus-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 4096,
                "description": "Maximum tokens in response"
            },
        }
    },
    "cohere.command-r-v1:0": {
        "returns_thoughts": False,
        "supports_effort": False,
        "supports_thinking": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "top_p": {
                "type": "float",
                "default": 0.9,
                "min": 0.0,
                "max": 1.0,
                "description": "Nucleus sampling"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 4096,
                "description": "Maximum tokens in response"
            },
        }
    },
}