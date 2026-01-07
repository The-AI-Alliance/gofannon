# Code interpreter will work, but needs special handling of responses or throws error: 
# ResponseCodeInterpreterToolCall has no attribute 'content'

models = {
    # =========================================================================
    # GPT-5.2 Series (Latest)
    # =========================================================================
    "gpt-5.2": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5.2-2025-12-11": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5.2-pro": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "medium", 
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5.2-pro-2025-12-11": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "medium", 
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },

    # =========================================================================
    # GPT-5.1 Series
    # =========================================================================
    "gpt-5.1": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5.1-2025-11-13": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5.1-codex": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.2, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": []
    },
    "gpt-5.1-codex-mini": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.2, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": []
    },
    "gpt-5.1-codex-max": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.2, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": []
    },

    # =========================================================================
    # GPT-5 Series
    # =========================================================================
    "gpt-5": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-2025-08-07": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-pro": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "medium", 
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-pro-2025-10-06": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "medium", 
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-mini": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-mini-2025-08-07": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-nano": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {},
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-nano-2025-08-07": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {},
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-codex": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.2, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": []
    },
    "gpt-5-search-api": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {},
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-5-search-api-2025-10-14": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {},
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },

    # =========================================================================
    # O-Series (Reasoning Models)
    # =========================================================================
    "o1": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": []
    },
    "o1-2024-12-17": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": []
    },
    "o1-pro": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice",
                "default": "high",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": []
    },
    "o1-pro-2025-03-19": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning_effort": {
                "type": "choice",
                "default": "high",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": []
    },
    "o3": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "o3-2025-04-16": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "o3-mini": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            "reasoning_effort": {
                "type": "choice", 
                "default": "medium", 
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "o3-mini-2025-01-31": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            "reasoning_effort": {
                "type": "choice", 
                "default": "medium", 
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "o4-mini": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "o4-mini-2025-04-16": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            "reasoning_effort": {
                "type": "choice",
                "default": "medium",
                "choices": ["low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation"
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },

    # =========================================================================
    # GPT-4.1 Series
    # =========================================================================
    "gpt-4.1": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4.1-2025-04-14": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4.1-mini": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4.1-mini-2025-04-14": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4.1-nano": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4.1-nano-2025-04-14": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },

    # =========================================================================
    # GPT-4o Series
    # =========================================================================
    "gpt-4o": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-2024-11-20": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-2024-08-06": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-2024-05-13": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "chatgpt-4o-latest": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-mini": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-mini-2024-07-18": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },

    # =========================================================================
    # GPT-4o Search Preview
    # =========================================================================
    "gpt-4o-search-preview": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-search-preview-2025-03-11": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-mini-search-preview": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },
    "gpt-4o-mini-search-preview-2025-03-11": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "medium"}},
        ]
    },

    # =========================================================================
    # GPT-4 Turbo Series
    # =========================================================================
    "gpt-4-turbo": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },
    "gpt-4-turbo-2024-04-09": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },
    "gpt-4-turbo-preview": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },
    "gpt-4-0125-preview": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },
    "gpt-4-1106-preview": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },

    # =========================================================================
    # GPT-4 Base
    # =========================================================================
    "gpt-4": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 8192, "min": 1, "max": 8192},
        },
        "built_in_tools": []
    },
    "gpt-4-0613": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 8192, "min": 1, "max": 8192},
        },
        "built_in_tools": []
    },

    # =========================================================================
    # GPT-3.5 Series
    # =========================================================================
    "gpt-3.5-turbo": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },
    "gpt-3.5-turbo-0125": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },
    "gpt-3.5-turbo-1106": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 4096},
        },
        "built_in_tools": []
    },
    "gpt-3.5-turbo-16k": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0, "mutually_exclusive_with": ["top_p"]},
            "top_p": {"type": "float", "default": 1.0, "min": 0.0, "max": 1.0, "mutually_exclusive_with": ["temperature"]},
            "max_tokens": {"type": "int", "default": 4096, "min": 1, "max": 16384},
        },
        "built_in_tools": []
    },
}
