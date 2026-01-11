# LLM Provider Configuration Guide

This guide explains how to set up and add LLM providers in Gofannon. Provider configurations determine which models are available and how they interact with the system.

## Table of Contents

- [Overview](#overview)
- [Why LiteLLM?](#why-litellm)
- [Configuration Structure](#configuration-structure)
- [Provider Configuration Files](#provider-configuration-files)
- [Adding a New Provider](#adding-a-new-provider)
- [Parameter Types and Features](#parameter-types-and-features)
- [Examples](#examples)
- [LiteLLM Mapping Reference](#litellm-mapping-reference)

## Overview

Gofannon uses a centralized provider configuration system that abstracts LLM provider implementations through [LiteLLM](https://github.com/BerriAI/litellm). All provider configurations are defined in:

```
webapp/packages/api/user-service/config/
├── provider_config.py          # Main provider registry
├── openai/__init__.py          # OpenAI models configuration
├── anthropic/__init__.py       # Anthropic/Claude models configuration
├── gemini/__init__.py          # Google Gemini models configuration
└── [provider]/__init__.py      # Additional provider configurations
```

The LLM service that consumes these configurations is located at:
```
webapp/packages/api/user-service/services/llm_service.py
```

## Why LiteLLM?

Gofannon relies on [LiteLLM](https://github.com/BerriAI/litellm) to abstract multiple LLM providers and manage their dependencies. This architectural decision has important implications:

### Advantages

1. **Unified Interface**: Single API interface for all providers (OpenAI, Anthropic, Google, etc.)
2. **Dependency Management**: LiteLLM handles provider-specific SDKs and their dependencies
3. **Consistency**: Standardized request/response formats across providers
4. **Reduced Maintenance**: Updates to provider SDKs are managed by LiteLLM

### Important Tradeoff

**Do not use provider-specific SDKs directly.** While this keeps our codebase simpler, it creates a brief lag between when a provider releases a new feature and when we can use it (we must wait for LiteLLM to add support). However, we've decided this tradeoff is acceptable given the significant maintenance and consistency benefits.

### Best Practice

When implementing provider features, always reference [LiteLLM's documentation](https://docs.litellm.ai/docs/) to understand:
- How provider-specific options map to LiteLLM parameters
- Which features are currently supported
- Provider-specific limitations or quirks

## Configuration Structure

Each provider in `provider_config.py` follows this structure:

```python
PROVIDER_CONFIG = {
    "provider_name": {
        "api_key_env_var": "PROVIDER_API_KEY",  # Optional: environment variable for API key
        "models": {
            "model-name": {
                "api_style": "responses",  # Optional: "responses" for OpenAI's special APIs
                "returns_thoughts": True,   # Whether model returns reasoning/thoughts
                "parameters": {
                    # Model-specific parameters (see below)
                },
                "built_in_tools": [
                    # Provider-specific built-in tools (see below)
                ]
            }
        }
    }
}
```

### Key Fields

- **api_key_env_var**: Environment variable name for the provider's API key
- **models**: Dictionary of model configurations keyed by model name
- **api_style**: Special handling for certain APIs (e.g., OpenAI's "responses" API for o1/reasoning models)
- **returns_thoughts**: Boolean indicating if the model returns reasoning traces or internal thoughts
- **parameters**: Model-specific parameters with validation rules
- **built_in_tools**: Provider-specific tools (web search, code execution, etc.)

## Provider Configuration Files

### OpenAI Configuration

Location: [webapp/packages/api/user-service/config/openai/__init__.py](webapp/packages/api/user-service/config/openai/__init__.py)

Key features:
- **API Style**: OpenAI's newer models (o1, gpt-5 series) use the `"responses"` API style
- **Reasoning Effort**: GPT-5 and o-series models support `reasoning_effort` parameter
- **Built-in Tools**: Many models have built-in web search capabilities

Example configuration:

```python
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
        {
            "id": "web_search",
            "description": "Performs a web search.",
            "tool_config": {"type": "web_search", "search_context_size": "medium"}
        },
    ]
}
```

**LiteLLM Mapping**:
- The `api_style: "responses"` maps to LiteLLM's `litellm.aresponses()` function (see [llm_service.py:87-127](webapp/packages/api/user-service/services/llm_service.py#L87-L127))
- Standard models use `litellm.acompletion()` (see [llm_service.py:220-240](webapp/packages/api/user-service/services/llm_service.py#L220-L240))
- Model string format: `"openai/model-name"` (see [llm_service.py:53](webapp/packages/api/user-service/services/llm_service.py#L53))

### Anthropic Configuration

Location: [webapp/packages/api/user-service/config/anthropic/__init__.py](webapp/packages/api/user-service/config/anthropic/__init__.py)

Key features:
- **Mutually Exclusive Parameters**: Claude 4.x models cannot have both `temperature` and `top_p` set simultaneously
- **Max Tokens**: Different models have different token limits

Example configuration:

```python
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
}
```

**LiteLLM Mapping**:
- Model string format: `"anthropic/model-name"` (see [llm_service.py:53](webapp/packages/api/user-service/services/llm_service.py#L53))
- Anthropic's block-based content format is handled in [llm_service.py:250-261](webapp/packages/api/user-service/services/llm_service.py#L250-L261)
- The `mutually_exclusive_with` is enforced in the frontend; LiteLLM passes through only one parameter

### Gemini Configuration

Location: [webapp/packages/api/user-service/config/gemini/__init__.py](webapp/packages/api/user-service/config/gemini/__init__.py)

Key features:
- **Built-in Tools**: Google Search, URL context, code execution
- **Reasoning Effort**: Similar to OpenAI's reasoning models

Example configuration:

```python
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
            "id": "code_execution",
            "description": "Executes code snippets in a secure environment.",
            "tool_config": {"codeExecution": {}}
        }
    ]
}
```

**LiteLLM Mapping**:
- Model string format: `"gemini/model-name"` (see [llm_service.py:53](webapp/packages/api/user-service/services/llm_service.py#L53))
- Built-in tools are passed through LiteLLM's `tools` parameter

### Ollama Configuration

Location: [webapp/packages/api/user-service/config/provider_config.py:17-77](webapp/packages/api/user-service/config/provider_config.py#L17-L77)

Example for local models:

```python
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
            }
        }
    }
}
```

**LiteLLM Mapping**:
- No API key required (local deployment)
- Model string format: `"ollama/model-name"`

## Adding a New Provider

Follow these steps to add a new LLM provider:

### Step 1: Research LiteLLM Support

Before adding a provider, check [LiteLLM's supported providers documentation](https://docs.litellm.ai/docs/providers):

1. Verify the provider is supported
2. Note the required authentication method
3. Identify any provider-specific parameters
4. Check for special features (built-in tools, reasoning, etc.)

### Step 2: Create Provider Configuration File

Create a new file: `webapp/packages/api/user-service/config/[provider_name]/__init__.py`

```python
# [Provider Name] models configuration
# Updated [Date]

models = {
    "model-name": {
        "returns_thoughts": False,  # or True if model supports reasoning
        "parameters": {
            # Define parameters with validation rules
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness in generation"
            },
            # Add more parameters as needed
        },
        "built_in_tools": []  # Add provider-specific tools if available
    }
}
```

### Step 3: Register Provider in Main Config

Edit [webapp/packages/api/user-service/config/provider_config.py](webapp/packages/api/user-service/config/provider_config.py):

```python
from .provider_name import models as provider_name_models

PROVIDER_CONFIG = {
    # ... existing providers ...
    "provider_name": {
        "api_key_env_var": "PROVIDER_NAME_API_KEY",  # if API key is required
        "models": provider_name_models,
    },
}
```

### Step 4: Set Environment Variables

Add the API key to your environment or `.env` file:

```bash
PROVIDER_NAME_API_KEY=your-api-key-here
```

### Step 5: Test the Integration

Create a test to verify the provider works correctly. The LLM service will automatically:
- Format the model string as `"provider_name/model-name"`
- Pass it to LiteLLM's `acompletion()` or `aresponses()` function
- Handle the response according to the configuration

## Parameter Types and Features

### Basic Parameter Types

#### Float Parameter

```python
"temperature": {
    "type": "float",
    "default": 0.7,
    "min": 0.0,
    "max": 2.0,
    "description": "Controls randomness"
}
```

#### Integer Parameter

```python
"max_tokens": {
    "type": "integer",
    "default": 4096,
    "min": 1,
    "max": 16384,
    "description": "Maximum tokens in response"
}
```

#### Choice Parameter

```python
"reasoning_effort": {
    "type": "choice",
    "default": "medium",
    "choices": ["low", "medium", "high"],
    "description": "Effort level for reasoning"
}
```

### Advanced Features

#### Mutually Exclusive Parameters

Prevents using two parameters simultaneously (like `temperature` and `top_p`):

```python
"temperature": {
    "type": "float",
    "default": 0.7,
    "min": 0.0,
    "max": 2.0,
    "mutually_exclusive_with": ["top_p"]
}
```

**Implementation**: The LLM service filters out `None` values before passing to LiteLLM (see [llm_service.py:58-59](webapp/packages/api/user-service/services/llm_service.py#L58-L59)):

```python
# Filter out None values from parameters (e.g., top_p with default None)
filtered_params = {k: v for k, v in parameters.items() if v is not None}
```

#### Built-in Tools

Provider-specific tools that don't require custom implementation:

```python
"built_in_tools": [
    {
        "id": "web_search",
        "description": "Performs a web search.",
        "tool_config": {"type": "web_search", "search_context_size": "medium"}
    }
]
```

**LiteLLM Mapping**: Built-in tools are passed through the `tools` parameter in [llm_service.py:69-70](webapp/packages/api/user-service/services/llm_service.py#L69-L70):

```python
if tools:
    kwargs["tools"] = tools
```

#### API Styles

For providers with multiple API endpoints (like OpenAI's responses API):

```python
"api_style": "responses"  # Uses litellm.aresponses() instead of acompletion()
```

**Implementation**: The service checks this flag and routes to the appropriate LiteLLM function (see [llm_service.py:82-86](webapp/packages/api/user-service/services/llm_service.py#L82-L86)):

```python
use_responses_api = (
    api_style == "responses" and
    (tools or reasoning_effort != 'disable')
)
```

## Examples

### Example 1: Basic Provider (No Special Features)

```python
# config/cohere/__init__.py
models = {
    "command": {
        "returns_thoughts": False,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.75,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "max_tokens": {
                "type": "integer",
                "default": 4096,
                "min": 1,
                "max": 4096,
                "description": "Maximum tokens in response"
            }
        },
        "built_in_tools": []
    }
}
```

```python
# In provider_config.py
from .cohere import models as cohere_models

PROVIDER_CONFIG = {
    "cohere": {
        "api_key_env_var": "COHERE_API_KEY",
        "models": cohere_models
    }
}
```

### Example 2: Provider with Reasoning Support

```python
# config/mistral/__init__.py
models = {
    "mistral-large": {
        "returns_thoughts": True,
        "parameters": {
            "temperature": {
                "type": "float",
                "default": 0.7,
                "min": 0.0,
                "max": 1.0,
                "description": "Controls randomness"
            },
            "reasoning_effort": {
                "type": "choice",
                "default": "disable",
                "choices": ["disable", "low", "medium", "high"],
                "description": "Reasoning effort level"
            }
        },
        "built_in_tools": []
    }
}
```

### Example 3: Local Provider (No API Key)

```python
# In provider_config.py
PROVIDER_CONFIG = {
    "vllm": {
        # No api_key_env_var needed for local deployment
        "models": {
            "llama-3-70b": {
                "returns_thoughts": False,
                "parameters": {
                    "temperature": {
                        "type": "float",
                        "default": 0.7,
                        "min": 0.0,
                        "max": 1.0,
                        "description": "Controls randomness"
                    }
                },
                "built_in_tools": []
            }
        }
    }
}
```

## LiteLLM Mapping Reference

This section explains how Gofannon's configuration maps to LiteLLM function calls.

### Model String Format

Gofannon constructs model strings in the format `"provider/model"`:

```python
# From llm_service.py:53
model_string = f"{provider}/{model}"
```

Examples:
- `"openai/gpt-4o"`
- `"anthropic/claude-opus-4-5-20251101"`
- `"gemini/gemini-2.5-pro"`

### Standard Completion Flow

For most models (see [llm_service.py:220-240](webapp/packages/api/user-service/services/llm_service.py#L220-L240)):

```python
kwargs = {
    "model": model_string,          # "provider/model"
    "messages": messages,           # Standard messages array
    **filtered_params,              # temperature, max_tokens, etc.
}

if reasoning_effort != 'disable':
    kwargs['reasoning_effort'] = reasoning_effort

response = await litellm.acompletion(**kwargs)
```

### Responses API Flow

For OpenAI's responses API (see [llm_service.py:87-127](webapp/packages/api/user-service/services/llm_service.py#L87-L127)):

```python
# System prompts become 'instructions'
kwargs["instructions"] = "\n\n".join(system_prompts)

# Last user message becomes 'input'
response_obj = await litellm.aresponses(input=input_text, **kwargs)

# Poll for completion
response_status = await litellm.aget_responses(response_id=response_obj.id)
```

### Parameter Filtering

Parameters with `None` values are filtered out (see [llm_service.py:58-59](webapp/packages/api/user-service/services/llm_service.py#L58-L59)):

```python
filtered_params = {k: v for k, v in parameters.items() if v is not None}
```

This implements mutual exclusivity without explicit validation.

### Tool Handling

Tools are passed directly if provided (see [llm_service.py:69-70](webapp/packages/api/user-service/services/llm_service.py#L69-L70)):

```python
if tools:
    kwargs["tools"] = tools
```

### Response Extraction

Different response formats are handled:

**Standard responses** (see [llm_service.py:239-263](webapp/packages/api/user-service/services/llm_service.py#L239-L263)):
```python
message = response.choices[0].message
content = message.content if isinstance(message.content, str) else ""

# Extract thoughts (reasoning, tool calls, etc.)
if message.tool_calls:
    thoughts_payload['tool_calls'] = [tc.model_dump() for tc in message.tool_calls]

if hasattr(message, 'reasoning_content') and message.reasoning_content:
    thoughts_payload['reasoning_content'] = message.reasoning_content
```

**Anthropic block-based responses** (see [llm_service.py:250-261](webapp/packages/api/user-service/services/llm_service.py#L250-L261)):
```python
if isinstance(message.content, list):  # Anthropic's block-based content
    thought_blocks = [block for block in content_blocks if block.get("type") == "thought"]
    tool_use_blocks = [block for block in content_blocks if block.get("type") == "tool_use"]
    text_blocks = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
```

## Additional Resources

- [LiteLLM Documentation](https://docs.litellm.ai/docs/)
- [LiteLLM Supported Providers](https://docs.litellm.ai/docs/providers)
- [LiteLLM API Reference](https://docs.litellm.ai/docs/completion)
- [Gofannon LLM Service Implementation](webapp/packages/api/user-service/services/llm_service.py)

## Troubleshooting

### Provider Not Working

1. **Check LiteLLM Support**: Verify the provider is supported by LiteLLM
2. **Verify API Key**: Ensure the environment variable is set correctly
3. **Check Model Name**: Verify the model name matches LiteLLM's expected format
4. **Review LiteLLM Logs**: Check `services/litellm_logger.py` for error messages

### Parameter Issues

1. **Mutually Exclusive Parameters**: Ensure only one parameter from a mutually exclusive group is set
2. **Range Validation**: Check that numeric values are within min/max bounds
3. **Type Mismatches**: Verify parameter types match the configuration (float vs int)

### Feature Lag

If a provider releases a new feature that isn't working:

1. Check if LiteLLM has added support for the feature
2. Review [LiteLLM's changelog](https://github.com/BerriAI/litellm/releases)
3. Consider updating the LiteLLM dependency
4. Temporarily use the provider's SDK directly (not recommended for production)

## Contributing

When adding new providers or models:

1. Follow the existing configuration patterns
2. Add comprehensive parameter descriptions
3. Document any provider-specific quirks
4. Reference LiteLLM documentation for parameter mappings
5. Add example usage in this documentation
6. Test thoroughly with the provider's actual API

---

**Last Updated**: January 2026
**Maintainer**: AI Alliance Gofannon Team
