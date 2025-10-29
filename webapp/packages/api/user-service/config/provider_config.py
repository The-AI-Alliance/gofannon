
PROVIDER_CONFIG = {
    "openai": {
        "api_key_env_var": "OPENAI_API_KEY",
        "models": {
            "gpt-5-mini-2025-08-07": {
                "parameters": {
                }
            }, 
            "gpt-4": {
                "parameters": {
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 2.0,
                        "description": "Controls randomness in responses"
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
                        "description": "Nucleus sampling parameter"
                    },
                    "presence_penalty": {
                        "type": "float",
                        "default": 0.0,
                        "min": -2.0,
                        "max": 2.0,
                        "description": "Penalty for new topics"
                    },
                    "frequency_penalty": {
                        "type": "float",
                        "default": 0.0,
                        "min": -2.0,
                        "max": 2.0,
                        "description": "Penalty for token repetition"
                    },
                    "stop": {
                        "type": "choice",
                        "default": 0,
                        "choices": ["\n", " Human:", " AI:"],
                        "description": "Sequence where the API will stop generating."
                    }
                }
            },
            "gpt-4.1-mini": {
                "api_style": "responses",
                "parameters": {
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 2.0,
                        "description": "Controls randomness"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "default": 2048,
                        "min": 1,
                        "max": 4096,
                        "description": "Maximum tokens in response"
                    }
                },
                "built_in_tools": [
                    {
                        "id": "web_search",
                        "description": "Performs a web search.",
                        "tool_config": {"type": "web_search_preview", "search_context_size": "low"}
                    }
                ]
            },
            "gpt-4.1-nano": {
                "parameters": {
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 2.0,
                        "description": "Controls randomness in responses"
                    },
                    "max_tokens": {
                        "type": "integer",
                        "default": 1024,
                        "min": 1,
                        "max": 4096,
                        "description": "Maximum tokens in response"
                    },
                    "top_p": {
                        "type": "float",
                        "default": 1.0,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "Nucleus sampling parameter"
                    }
                }
            }
        }
    },
    "gemini": {
        "api_key_env_var": "GEMINI_API_KEY",
        "models": {
            "gemini-2.5-pro": {
                "parameters": {
                    "reasoning_effort": {
                        "type": "choice", 
                        "default": 0,
                        "choices": ["disable", "low", "medium", "high"],
                    }
                },
                "built_in_tools": [
                    {
                        "id": "google_search",
                        "description": "Performs a Google search.",
                        "tool_config": {"google_search": {}}
                    }
                ]
            }
        }
    },
    "anthropic": {
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "models": {
            "claude-3-opus": {
                "parameters": {
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
                "parameters": {
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