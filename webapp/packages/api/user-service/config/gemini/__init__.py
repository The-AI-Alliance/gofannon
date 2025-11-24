models = {
    "gemini-3-pro-preview": {
         "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "description": "Temperature - Controls the randomness of the output."
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
            },
            {
                "id": "urlContext", 
                "description": "Provides context from a specified URL.",
                "tool_config": {"urlContext": {}}
            },
            {
                "id": "code_execution",
                "description": "Executes code snippets in a secure environment.",
                "tool_config": {"codeExecution": {}}
            }
        ]
    }
    "gemini-2.5-pro": {
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "description": "Temperature - Controls the randomness of the output."
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
            },
            {
                "id": "urlContext", 
                "description": "Provides context from a specified URL.",
                "tool_config": {"urlContext": {}}
            },
            {
                "id": "code_execution",
                "description": "Executes code snippets in a secure environment.",
                "tool_config": {"codeExecution": {}}
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
                "description": "Temperature - Controls the randomness of the output."
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
            },
            {
                "id": "urlContext", 
                "description": "Provides context from a specified URL.",
                "tool_config": {"urlContext": {}}
            },
            {
                "id": "code_execution",
                "description": "Executes code snippets in a secure environment.",
                "tool_config": {"codeExecution": {}}
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
                "description": "Temperature - Controls the randomness of the output."
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
            },
            {
                "id": "urlContext",
                "description": "Provides context from a specified URL.",
                "tool_config": {"urlContext": {}}
            },
            {
                "id": "code_execution",
                "description": "Executes code snippets in a secure environment.",
                "tool_config": {"codeExecution": {}}
            }
        ],
    }
}