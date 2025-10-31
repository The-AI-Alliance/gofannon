
from .gemini import models as gemini_models
from .openai import models as openai_models
PROVIDER_CONFIG = {
    "openai": {
        "api_key_env_var": "OPENAI_API_KEY",
        "models": openai_models
    },
    "gemini": {
        "api_key_env_var": "GEMINI_API_KEY",
        "models":  gemini_models,
    },
    "anthropic": {
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "models": {
            "claude-3-opus": {
                "returns_thoughts": True,
                "parameters": {
                    "reasoning_effort": {
                        "type": "choice",
                        "default": "disable",
                        "choices": ["disable", "low", "medium", "high"],
                        "description": "Controls the reasoning effort of the model."
                    },
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "Controls randomness"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "default": 2048,
                        "min": 1,
                        "max": 4096,
                        "description": "Maximum tokens in response"
                    },
                    "top_p": {
                        "type": "float",
                        "default": 1.0,
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
                    }
                },
                "built_in_tools": [
                    {
                        "id": "web_search",
                        "description": "Performs a web search.",
                        "tool_config": {"name": "web_search"}
                    }
                ]
            },
            "claude-3-sonnet": {
                "returns_thoughts": True,
                "parameters": {
                    "reasoning_effort": {
                        "type": "choice",
                        "default": "disable",
                        "choices": ["disable", "low", "medium", "high"],
                        "description": "Controls the reasoning effort of the model."
                    },
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "Controls randomness"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "default": 1024,
                        "min": 1,
                        "max": 4096,
                        "description": "Maximum tokens in response"
                    }
                }
            }
        }
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