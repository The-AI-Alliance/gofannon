# LLM Service Architecture

This document explains the centralized LLM service in Gofannon and why all LLM calls must go through it.

## Overview

The Gofannon user service uses a centralized LLM service (`services/llm_service.py`) as the single point of interaction with language model providers. This design provides several critical benefits for cost management, observability, and maintainability.

## Why Use `call_llm` Instead of `litellm` Directly?

### 1. Cost Tracking and User Allowances

The `call_llm` function automatically:
- Tracks the cost of each API call
- Associates costs with specific users
- Enforces user spending limits (allowances)
- Prevents unauthorized usage when allowances are exceeded

```python
# Inside call_llm:
user_service.require_allowance(user_id, basic_info=user_basic_info)
# ... make the API call ...
user_service.add_usage(user_id, response_cost, basic_info=user_basic_info)
```

If you bypass `call_llm` and call `litellm` directly:
- User costs won't be tracked
- Users could exceed their spending limits without being blocked
- Usage analytics will be incomplete

### 2. Observability and Logging

All LLM calls through the service are automatically logged for:
- Debugging production issues
- Monitoring API performance
- Auditing API usage
- Analyzing usage patterns

The service integrates with the observability service to log:
- Request details (provider, model, message count)
- Response metadata
- Errors and exceptions with full context

### 3. Provider-Specific Configuration

Different LLM providers have different API styles and response formats. The service handles:
- **Standard completion API** (OpenAI, Anthropic)
- **Responses API** (newer OpenAI models with extended thinking)
- **Reasoning content extraction** (Claude's extended thinking, OpenAI's reasoning tokens)
- **Block-based content handling** (Anthropic's content blocks)

Example of provider-specific handling:
```python
# The service automatically detects and handles different response formats
if hasattr(response.choices[0].message, 'reasoning_content'):
    thoughts = response.choices[0].message.reasoning_content
elif provider == "anthropic":
    # Handle Anthropic's block-based content format
    thoughts = extract_anthropic_thinking(response)
```

### 4. Consistent Error Handling

The service provides standardized error handling:
- Logs exceptions with full context (provider, model, user)
- Ensures errors are properly propagated
- Enables easier debugging across the codebase

### 5. Centralized Configuration

LiteLLM configuration is set once in the service:
```python
litellm.drop_params = True
litellm.set_verbose = False
```

This ensures consistent behavior across all LLM calls.

## API Reference

### `call_llm`

The main function for making LLM completions.

```python
async def call_llm(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    parameters: Dict[str, Any],
    tools: Optional[List[Dict[str, Any]]] = None,
    user_service: Optional[UserService] = None,
    user_id: Optional[str] = None,
    user_basic_info: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Any]:
    """
    Make an LLM completion call through the centralized service.

    Args:
        provider: The LLM provider (e.g., 'openai', 'anthropic', 'gemini')
        model: The model name (e.g., 'gpt-4', 'claude-3-opus')
        messages: List of message dicts with 'role' and 'content' keys
        parameters: Additional parameters (temperature, max_tokens, etc.)
        tools: Optional list of tool configurations for function calling
        user_service: Optional UserService for cost tracking
        user_id: Optional user ID for cost tracking
        user_basic_info: Optional user info for creating new users

    Returns:
        Tuple of (content, thoughts) where:
        - content: The string response from the LLM
        - thoughts: Any reasoning/thinking content (or None)
    """
```

### `stream_llm`

For streaming responses.

```python
async def stream_llm(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    parameters: Dict[str, Any],
    user_service: Optional[UserService] = None,
    user_id: Optional[str] = None,
    user_basic_info: Optional[Dict[str, Any]] = None,
) -> AsyncGenerator[Any, None]:
    """
    Stream LLM responses.

    Note: Cost tracking is not available for streaming responses.

    Yields:
        Chunks from the LLM response stream
    """
```

## Usage Examples

### Basic Usage

```python
from services.llm_service import call_llm

content, thoughts = await call_llm(
    provider="openai",
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    parameters={"temperature": 0.7, "max_tokens": 500},
    user_service=user_service,
    user_id="user-123",
)
```

### Without User Tracking

For internal operations that don't need user cost tracking:

```python
content, thoughts = await call_llm(
    provider="openai",
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Summarize this..."}],
    parameters={},
    user_service=None,
    user_id=None,
)
```

### Streaming

```python
from services.llm_service import stream_llm

async for chunk in stream_llm(
    provider="openai",
    model="gpt-4",
    messages=[{"role": "user", "content": "Tell me a story..."}],
    parameters={"temperature": 0.9},
):
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Files That Can Import `litellm` Directly

Only these files should import `litellm`:

| File | Reason |
|------|--------|
| `services/llm_service.py` | The abstraction layer itself |
| `services/litellm_logger.py` | Logging integration |

All other files must use:
```python
from services.llm_service import call_llm, stream_llm
```

## Testing

When testing code that uses the LLM service, mock `call_llm` or `stream_llm`:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_feature():
    with patch("my_module.call_llm", new_callable=AsyncMock) as mock:
        mock.return_value = ("Test response", None)

        result = await my_function()

        assert result == expected
        mock.assert_called_once()
```

## Migration Guide

If you find code that uses `litellm` directly, migrate it:

### Before (Incorrect)
```python
import litellm

response = await litellm.acompletion(
    model="openai/gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
)
content = response.choices[0].message.content
```

### After (Correct)
```python
from services.llm_service import call_llm

content, thoughts = await call_llm(
    provider="openai",
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    parameters={},
    user_service=user_service,
    user_id=user_id,
)
```

Note the changes:
1. Import `call_llm` instead of `litellm`
2. Split `model` into separate `provider` and `model` arguments
3. Use `parameters` dict instead of kwargs
4. Pass `user_service` and `user_id` for cost tracking
5. Handle the tuple return `(content, thoughts)` instead of response object