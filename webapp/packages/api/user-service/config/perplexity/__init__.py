# Perplexity AI models configuration
# Reference: https://docs.litellm.ai/docs/providers/perplexity

models = {
    # =========================================================================
    # Sonar Deep Research
    # =========================================================================
    "sonar-deep-research": {
        "returns_thoughts": False,
        "context_window": 128000,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness in generation"
            },
        },
        "built_in_tools": []
    },

    # =========================================================================
    # Sonar Reasoning Series
    # =========================================================================
    "sonar-reasoning-pro": {
        "returns_thoughts": True,
        "context_window": 128000,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness in generation"
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            },
        },
        "built_in_tools": []
    },
    "sonar-reasoning": {
        "returns_thoughts": True,
        "context_window": 128000,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness in generation"
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            },
        },
        "built_in_tools": []
    },

    # =========================================================================
    # Sonar Series
    # =========================================================================
    "sonar-pro": {
        "returns_thoughts": False,
        "context_window": 200000,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness in generation"
            },
        },
        "built_in_tools": []
    },
    "sonar": {
        "returns_thoughts": False,
        "context_window": 128000,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness in generation"
            },
        },
        "built_in_tools": []
    },

    # =========================================================================
    # R1 Series
    # =========================================================================
    "r1-1776": {
        "returns_thoughts": False,
        "context_window": 128000,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness in generation"
            },
        },
        "built_in_tools": []
    },
}