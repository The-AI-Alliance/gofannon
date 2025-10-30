

models = {

    "gemini-2.5-pro": {
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "description": "Temperature - Controls randomness"
            },
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
                    {
                        "id": "google_search",
                        "description": "Performs a Google search.",
                        "tool_config": {"google_search": {}}
                    }
                ],
    },
    "gemini-2.5-flash": {
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "description": "Temperature - Controls randomness"
            },
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
                    {
                        "id": "google_search",
                        "description": "Performs a Google search.",
                        "tool_config": {"google_search": {}}
                    }
                ],
    },
    "gemini-2.5-flash-lite": {
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "description": "Temperature - Controls randomness"
            },
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        },
        "built_in_tools": [
                    {
                        "id": "google_search",
                        "description": "Performs a Google search.",
                        "tool_config": {"google_search": {}}
                    }
                ],
    }
}