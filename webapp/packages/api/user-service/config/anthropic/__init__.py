# Anthropic Claude models configuration
# Updated January 2026
# Note: Claude 4.x models do NOT allow temperature + top_p together - use only one

models = {
    # =========================================================================
    # Claude 4.5 family (Latest - November 2025)
    # Note: Cannot specify both temperature and top_p - pick one
    # =========================================================================
    "claude-opus-4-5-20251101": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 16384,
                "description": "Maximum tokens in response"
            },
        }
    },
    "claude-sonnet-4-5-20250929": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 16384,
                "description": "Maximum tokens in response"
            },
        }
    },
    "claude-haiku-4-5-20251001": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 16384,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Claude 4.1 (August 2025)
    # =========================================================================
    "claude-opus-4-1-20250805": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 16384,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Claude 4 (May 2025)
    # =========================================================================
    "claude-opus-4-20250514": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 16384,
                "description": "Maximum tokens in response"
            },
        }
    },
    "claude-sonnet-4-20250514": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 16384,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Claude 3.7 (February 2025)
    # =========================================================================
    "claude-3-7-sonnet-20250219": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Claude 3.5 family (2024)
    # =========================================================================
    "claude-3-5-sonnet-20241022": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "claude-3-5-sonnet-20240620": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },
    "claude-3-5-haiku-20241022": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
                "default": 8192,
                "min": 1,
                "max": 8192,
                "description": "Maximum tokens in response"
            },
        }
    },

    # =========================================================================
    # Claude 3 family (Legacy)
    # =========================================================================
    "claude-3-haiku-20240307": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 1.0,
                "description": "Randomness (0=focused, 1=creative)"
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
}
