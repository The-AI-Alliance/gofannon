

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
            # "top_p": {
            #     "type": "float",
            #     "default": None,
            #     "min": 0.0,
            #     "max": 1.0,
            #     "description": "TopP - Nucleus sampling"
            # },
            # "max_tokens": { #TODO: Verify max tokens for Gemini
            #     "type": "integer",
            #     "default": None, 
            #     "min": 1,
            #     "max": 1048576,
            #     "description": "Maximum tokens in response"
            # },
            # "max_ completion_tokens": {
            #     "type": "integer",
            #     "default": 65536,
            #     "min": 1,
            #     "max": 65536,
            #     "description": "Maximum completion tokens"
            # },
            # "tools": {
            #     "type": "list_choice",
            #     "default": [],
            #     "choices": ["googleSearch", "googleMaps", "urlContext", "codeExecution"],
            #     "description": "Gemini Tools to enable during generation"
            # },
            # "tool_choice": { # if you don't want it calling tools, don't give it any tools...
            #     "type": "choice",
            #     "default": "auto",
            #     "choices": ["auto", "none"],
            #     "description": "Tool selection mode"
            # },
            
            # "response_format": { # Need to set response_format: {"type": ...} in request body
            #     "type": "choice",
            #     "default": "text",
            #     "choices": ["text", "json_object"],
            #     "description": "Format of the response"
            # },
            # "n" : {
            #     "type": "integer",
            #     "default": 1,
            #     "min": 1,
            #     "max": 5,
            #     "description": "Number of completions to generate"
            # },
            # "stop": {
            #     "type": "list_string",
            #     "default": [],
            #     "description": "Sequences where the API will stop generating."
            # },
            # "logprobs": {
            #     "type": "integer",
            #     "default": 0,
            #     "min": 0,
            #     "max": 5,
            #     "description": "Include logprobs on the logprobs most likely tokens"
            # },
            # "frequency_penalty": {
            #     "type": "float",
            #     "default": 0.0,
            #     "min": -2.0,
            #     "max": 2.0,
            #     "description": "Penalty for token repetition"
            # },
            # "modalities": {
            #     "type": "list_choice",
            #     "default": ["text"],
            #     "choices": ["text", "image", "video", "audio"],
            #     "description": "Modalities to include in generation"
            # },  
            # "parallel_tool_calls": {
            #     "type": "boolean",
            #     "default": False,
            #     "description": "Enable parallel tool calls"
            # },
            # "web_search_options": {
            #     "type": "object",
            #     "default": {
            #         "num_results": 3,
            #         "region": "us",
            #         "language": "en"
            #     },
            #     "description": "Options for web search tool"
            # },
            "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        }
    },
    "gemini-2.5-flash": {
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "description": "Temperature - Controls randomness",
            },
            # "top_p": {
            #     "type": "float",
            #     "default": None,
            #     "min": 0.0,
            #     "max": 1.0,
            #     "description": "TopP - Nucleus sampling"
            # },
            # "max_tokens": { #TODO: Verify max tokens for Gemini
            #     "type": "integer",
            #     "default": None, 
            #     "min": 1,
            #     "max": 1048576,
            #     "description": "Maximum tokens in response"
            # },
            # "max_ completion_tokens": {
            #     "type": "integer",
            #     "default": 65536,
            #     "min": 1,
            #     "max": 65536,
            #     "description": "Maximum completion tokens"
            # },
            # "tools": { 
            #     "type": "list_choice",
            #     "default": [],
            #     "choices": ["googleSearch", "googleMaps", "urlContext", "codeExecution"],
            #     "description": "Gemini Tools to enable during generation"
            # },
            # "tool_choice": { # if you don't want it calling tools, don't give it any tools...
            #     "type": "choice",
            #     "default": "auto",
            #     "choices": ["auto", "none"],
            #     "description": "Tool selection mode"
            # },
            
            # "response_format": { # Need to set response_format: {"type": ...} in request body
            #     "type": "choice",
            #     "default": "text",
            #     "choices": ["text", "json_object"],
            #     "description": "Format of the response"
            # },
            # "n" : {
            #     "type": "integer",
            #     "default": 1,
            #     "min": 1,
            #     "max": 5,
            #     "description": "Number of completions to generate"
            # },
            # "stop": {
            #     "type": "list_string",
            #     "default": [],
            #     "description": "Sequences where the API will stop generating."
            # },
            # "logprobs": {
            #     "type": "integer",
            #     "default": 0,
            #     "min": 0,
            #     "max": 5,
            #     "description": "Include logprobs on the logprobs most likely tokens"
            # },
            # "frequency_penalty": {
            #     "type": "float",
            #     "default": 0.0,
            #     "min": -2.0,
            #     "max": 2.0,
            #     "description": "Penalty for token repetition"
            # },
            # "modalities": {
            #     "type": "list_choice",
            #     "default": ["text"],
            #     "choices": ["text", "image", "video", "audio"],
            #     "description": "Modalities to include in generation"
            # },  
            # "parallel_tool_calls": {
            #     "type": "boolean",
            #     "default": False,
            #     "description": "Enable parallel tool calls"
            # },
            # "web_search_options": {
            #     "type": "object",
            #     "default": {
            #         "num_results": 3,
            #         "region": "us",
            #         "language": "en"
            #     },
            #     "description": "Options for web search tool"
            # },
                "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        }
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
            # "top_p": {
            #     "type": "float",
            #     "default": None,
            #     "min": 0.0,
            #     "max": 1.0,
            #     "description": "TopP - Nucleus sampling"
            # },
            # "max_tokens": { #TODO: Verify max tokens for Gemini
            #     "type": "integer",
            #     "default": None, 
            #     "min": 1,
            #     "max": 1048576,
            #     "description": "Maximum tokens in response"
            # },
            # "max_ completion_tokens": {
            #     "type": "integer",
            #     "default": 65536,
            #     "min": 1,
            #     "max": 65536,
            #     "description": "Maximum completion tokens"
            # },
            # "tools": { 
            #     "type": "list_choice",
            #     "default": [],
            #     "choices": ["googleSearch", "googleMaps", "urlContext", "codeExecution"],
            #     "description": "Gemini Tools to enable during generation"
            # },
            # "tool_choice": { # if you don't want it calling tools, don't give it any tools...
            #     "type": "choice",
            #     "default": "auto",
            #     "choices": ["auto", "none"],
            #     "description": "Tool selection mode"
            # },
            
            # "response_format": { # Need to set response_format: {"type": ...} in request body
            #     "type": "choice",
            #     "default": "text",
            #     "choices": ["text", "json_object"],
            #     "description": "Format of the response"
            # },
            # "n" : {
            #     "type": "integer",
            #     "default": 1,
            #     "min": 1,
            #     "max": 5,
            #     "description": "Number of completions to generate"
            # },
            # "stop": {
            #     "type": "list_string",
            #     "default": [],
            #     "description": "Sequences where the API will stop generating."
            # },
            # "logprobs": {
            #     "type": "integer",
            #     "default": 0,
            #     "min": 0,
            #     "max": 5,
            #     "description": "Include logprobs on the logprobs most likely tokens"
            # },
            # "frequency_penalty": {
            #     "type": "float",
            #     "default": 0.0,
            #     "min": -2.0,
            #     "max": 2.0,
            #     "description": "Penalty for token repetition"
            # },
            # "modalities": {
            #     "type": "list_choice",
            #     "default": ["text"],
            #     "choices": ["text", "image", "video", "audio"],
            #     "description": "Modalities to include in generation"
            # },  
            # "parallel_tool_calls": {
            #     "type": "boolean",
            #     "default": False,
            #     "description": "Enable parallel tool calls"
            # },
            # "web_search_options": {
            #     "type": "object",
            #     "default": {
            #         "num_results": 3,
            #         "region": "us",
            #         "language": "en"
            #     },
            #     "description": "Options for web search tool"
            # },
                "reasoning_effort": {
                "type": "choice", 
                "default": "disable", 
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning Effort: Effort level for reasoning during generation" 
            },
        }
    }
}