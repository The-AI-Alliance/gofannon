PROVIDER_CONFIG = {
    "openai": {
        "models": {
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
                    }
                }
            },
            "gpt-3.5-turbo": {
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
    "anthropic": {
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
                }
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