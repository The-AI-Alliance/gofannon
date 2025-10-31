# Code interpreter will work, but needs special handling of responses or throws error: 
# ResponseCodeInterpreterToolCall has no attribute 'content'

models = {
    # === GPT-5 family ===
    "gpt-5": {
        "api_style": "responses",
        "returns_thoughts": True,  # reasoning traces supported by GPT-5/o-series
        "parameters": {
            "reasoning": {
                "type": "object",
                "properties": {
                    "effort": {
                        "type": "choice",
                        "default": "medium",
                        "choices": ["low", "medium", "high"],
                        "description": "Controls model’s internal reasoning effort"
                    }
                }
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "auto"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
            # {"id": "image_generation", "description": "Generates images via the GPT Image tool.", "tool_config": {"type": "gpt_image"}} # No way to recover images yet
        ]
    },
    "gpt-5-mini": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "reasoning": {
                "type": "object",
                "properties": {
                    "effort": {
                        "type": "choice",
                        "default": "low",
                        "choices": ["disable", "low", "medium", "high"],
                        "description": "Reasoning effort (can be disabled)"
                    }
                }
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "auto"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
            # {"id": "image_generation", "description": "Generates images via the GPT Image tool.", "tool_config": {"type": "gpt_image"}} # No way to recover images yet
        ]
    },
    "gpt-5-nano": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "auto"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
        ]
    },

    # === O-series (reasoning) ===
    "o4-mini": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            
            "reasoning": {
                "type": "object",
                "properties": {
                    "effort": {"type": "choice", "default": "medium", "choices": ["low", "medium", "high"]}
                }
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "auto"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
        ]
    },
    "o3-mini": {
        "api_style": "responses",
        "returns_thoughts": True,
        "parameters": {
            "temperature": {"type": "float", "default": 0.6, "min": 0.0, "max": 2.0},
            "reasoning": {
                "type": "object",
                "properties": {
                    "effort": {"type": "choice", "default": "low", "choices": ["low", "medium", "high"]}
                }
            }
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "auto"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
        ]
    },

    # === GPT-4.x family still available via API ===
    "gpt-4.1": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search_preview", "search_context_size": "low"}},
            {"id": "image_generation", "description": "Generates images via the GPT Image tool.", "tool_config": {"type": "gpt_image"}}
        ]
    },
    "gpt-4.1-mini": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
       "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "auto"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
        ]
    },
    "gpt-4o": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search", "search_context_size": "auto"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
        ]
    },
    "gpt-4o-mini": {
        "api_style": "responses",
        "returns_thoughts": False,
        "parameters": {
            "temperature": {"type": "float", "default": 0.7, "min": 0.0, "max": 2.0},
        },
        "built_in_tools": [
            {"id": "web_search", "description": "Performs a web search.", "tool_config": {"type": "web_search_preview", "search_context_size": "low"}},
            # {"id": "image_generation", "description": "Generates images via the GPT Image tool.", "tool_config": {"type": "gpt_image"}},
            # {"id": "code_interpreter", "description": "Executes code snippets in a secure environment.", "tool_config": {"type": "code_interpreter","container": {"type": "auto"}}}
        ]
    },

}
