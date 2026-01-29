import asyncio
import json
from config import settings
from config.provider_config import PROVIDER_CONFIG
from services.database_service import get_database_service
from services.user_service import get_user_service
from typing import Any, AsyncGenerator, Dict, List, Tuple, Optional
import litellm

from services.litellm_logger import ensure_litellm_logging
from services.observability_service import get_observability_service
from services.user_service import UserService

ensure_litellm_logging()

# Configure litellm defaults
litellm.drop_params = True
litellm.set_verbose = False

def _extract_response_cost(response_obj: Any) -> Optional[float]:
    standard_logging = None
    if hasattr(response_obj, "_hidden_params") and isinstance(response_obj._hidden_params, dict):
        standard_logging = response_obj._hidden_params.get("standard_logging_object")
    if isinstance(standard_logging, dict):
        try:
            cost_value = standard_logging.get("response_cost")
            if cost_value is not None:
                return float(cost_value)
        except Exception:
            pass
    usage = getattr(response_obj, "usage", None)
    if usage and getattr(usage, "total_cost", None) is not None:
        try:
            return float(getattr(usage, "total_cost"))
        except Exception:
            return None
    return None


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
    Calls the specified language model using litellm, handling different API styles.
    Returns a tuple of (content, thoughts).
    """
    model_config = PROVIDER_CONFIG.get(provider, {}).get("models", {}).get(model, {})
    api_style = model_config.get("api_style")

    model_string = f"{provider}/{model}"
    
    thoughts = None
    content = ""

    # Filter out None values from parameters (e.g., top_p with default None)
    filtered_params = {k: v for k, v in parameters.items() if v is not None}

    kwargs = {
        "model": model_string,
        "messages": messages,
        **filtered_params,
    }

    reasoning_effort = kwargs.pop('reasoning_effort', 'disable')

    if tools:
        kwargs["tools"] = tools

    if user_service is None:
        user_service = get_user_service(get_database_service(settings))
    if user_id is None:
        user_id = "anonymous"

    if user_service and user_id:
        user_service.require_allowance(user_id, basic_info=user_basic_info)

    # Get the effective API key (user's key takes precedence over env var)
    api_key = None
    if user_service and user_id:
        api_key = user_service.get_effective_api_key(user_id, provider, basic_info=user_basic_info)
    # If no user-specific key, litellm will use environment variables
    if api_key:
        kwargs["api_key"] = api_key


    # Only use aresponses API when we actually need its features (tools or reasoning)
    # Otherwise use standard acompletion which is more reliable
    use_responses_api = (
        api_style == "responses" and 
        (tools or reasoning_effort != 'disable')
    )

    if use_responses_api:
        # Use aresponses and aget_responses for OpenAI's special tools like built-in web search
        kwargs.pop('messages', None) # aresponses uses 'input' not 'messages'
        if reasoning_effort != 'disable':
            kwargs['reasoning'] = {'effort': reasoning_effort, 'summary': 'auto'}

        try:
            # For 'responses' API style, system prompt is 'instructions' and user prompt is 'input'
            system_prompts = [msg["content"] for msg in messages if msg["role"] == "system"]
            other_messages = [msg for msg in messages if msg["role"] != "system"]

            if system_prompts:
                kwargs["instructions"] = "\n\n".join(system_prompts)

            # Note: The 'input' for aresponses is the last user message. Conversation history is not directly supported.
            input_text = ""
            for msg in reversed(other_messages):
                if msg.get("role") == "user":
                    msg_content = msg.get("content", "")
                    if isinstance(msg_content, str):
                        input_text = msg_content
                    elif isinstance(msg_content, list):
                        # Handle list-format content (e.g., multimodal)
                        input_text = " ".join(
                            item.get("text", "") for item in msg_content 
                            if isinstance(item, dict) and item.get("type") == "text"
                        )
                    break
            
            if not input_text:
                # Fall back to standard completion if no user input found
                kwargs['messages'] = messages
                if reasoning_effort != 'disable':
                    kwargs['reasoning_effort'] = reasoning_effort
                    kwargs.pop('reasoning', None)
                response = await litellm.acompletion(**kwargs)
                message = response.choices[0].message
                content = message.content if isinstance(message.content, str) else ""
                return content, None
            
            response_obj = await litellm.aresponses(input=input_text, **kwargs)
            
            final_response = None
            for _ in range(15): # Poll for up to 30 seconds
                await asyncio.sleep(2)
                # Pass api_key to aget_responses as well (needed when using user-specific keys)
                poll_kwargs = {"response_id": response_obj.id}
                if api_key:
                    poll_kwargs["api_key"] = api_key
                response_status = await litellm.aget_responses(**poll_kwargs)
                if response_status.status == "completed":
                    final_response = response_status
                    break
            
            if final_response:
                # Helper to get attribute from object or dict
                def get_attr(obj, key, default=None):
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    return getattr(obj, key, default)
                
                # Extract thoughts/summary from the first output block
                output_list = get_attr(final_response, 'output', [])
                if len(output_list) > 0 and output_list[0]:
                    first_output = output_list[0]
                    summary = get_attr(first_output, 'summary')
                    if summary:
                        summary_texts = []
                        for s in summary:
                            text = get_attr(s, 'text')
                            if text:
                                summary_texts.append(text)
                        thoughts = {"summary": summary_texts}
                    else:
                        # Fallback for other tool outputs
                        if hasattr(first_output, 'model_dump'):
                            thoughts = first_output.model_dump()
                        elif isinstance(first_output, dict):
                            thoughts = first_output
                
                # Extract content from the second output block (or first if it's the only one with content)
                if len(output_list) > 1 and output_list[1]:
                    second_output = output_list[1]
                    second_content = get_attr(second_output, 'content')
                    if second_content and len(second_content) > 0:
                        content = get_attr(second_content[0], 'text', '')
                
                if not content and len(output_list) > 0 and output_list[0]:
                    # Fallback if there's only one output block
                    first_content = get_attr(output_list[0], 'content')
                    if first_content and len(first_content) > 0:
                        content = get_attr(first_content[0], 'text', '')
                
                # If content is still empty, try to extract from any output block
                if not content:
                    for output_item in output_list:
                        if output_item:
                            item_content = get_attr(output_item, 'content')
                            if item_content:
                                for content_block in item_content:
                                    text = get_attr(content_block, 'text', '')
                                    if text:
                                        content = text
                                        break
                            if content:
                                break
                
                # Final validation - log if we still have no content
                if not content:
                    observability = get_observability_service()
                    observability.log(
                        level="WARNING",
                        event_type="empty_response_content",
                        message="Could not extract content from aresponses API response",
                        user_id=user_id,
                        metadata={
                            "model": model_string,
                            "output_list_length": len(output_list),
                            "output_structure": str(output_list)[:500]  # Truncate for logging
                        }
                    )
            else:
                raise Exception("Polling for OpenAI Responses API timed out.")

        except Exception as e:
            observability = get_observability_service()
            
            # Check for authentication errors and provide user-friendly message
            error_str = str(e).lower()
            if "invalid_api_key" in error_str or "authentication" in error_str or "api key" in error_str:
                key_source = "user-specific" if api_key else "environment variable"
                error_msg = f"Invalid API key for {provider}. Please check your {key_source} API key in your profile settings."
                observability.log(
                    level="ERROR",
                    event_type="invalid_api_key",
                    message=error_msg,
                    user_id=user_id,
                    metadata={
                        "provider": provider,
                        "key_source": key_source,
                        "original_error": str(e)[:200],
                    }
                )
                raise ValueError(error_msg) from e
            
            observability.log_exception(
                e,
                user_id=user_id,
                metadata={
                    "context": "litellm.aresponses",
                    "model": model_string,
                    "provider": provider,
                }
            )
            raise
    else:
        # Standard acompletion call for most models
        if reasoning_effort != 'disable':
            kwargs['reasoning_effort'] = reasoning_effort

        try:
            response = await litellm.acompletion(**kwargs)
        except Exception as e:
            observability = get_observability_service()
            
            # Check for authentication errors and provide user-friendly message
            error_str = str(e).lower()
            if "invalid_api_key" in error_str or "authentication" in error_str or "api key" in error_str:
                key_source = "user-specific" if api_key else "environment variable"
                error_msg = f"Invalid API key for {provider}. Please check your {key_source} API key in your profile settings."
                observability.log(
                    level="ERROR",
                    event_type="invalid_api_key",
                    message=error_msg,
                    user_id=user_id,
                    metadata={
                        "provider": provider,
                        "key_source": key_source,
                        "original_error": str(e)[:200],
                    }
                )
                raise ValueError(error_msg) from e
            
            observability.log_exception(
                e,
                user_id=user_id,
                metadata={
                    "context": "litellm.acompletion",
                    "model": kwargs.get('model'),
                    "provider": provider,
                    "tools": kwargs.get('tools'),
                }
            )
            raise
        message = response.choices[0].message
        content = message.content if isinstance(message.content, str) else ""
        
        # Extract various forms of "thoughts"
        thoughts_payload = {}
        if message.tool_calls:
            thoughts_payload['tool_calls'] = [tc.model_dump() for tc in message.tool_calls]
        
        if hasattr(message, 'reasoning_content') and message.reasoning_content:
            thoughts_payload['reasoning_content'] = message.reasoning_content

        if isinstance(message.content, list): # Handle Anthropic's block-based content
            content_blocks = message.content
            thought_blocks = [block for block in content_blocks if block.get("type") == "thought"]
            tool_use_blocks = [block for block in content_blocks if block.get("type") == "tool_use"]
            text_blocks = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
            
            if thought_blocks:
                thoughts_payload['anthropic_thoughts'] = thought_blocks
            if tool_use_blocks:
                thoughts_payload['anthropic_tool_uses'] = tool_use_blocks
            
            content = "\n".join(text_blocks)

        thoughts = thoughts_payload if thoughts_payload else None

    # Ensure thoughts are JSON serializable
    if thoughts is not None:
        thoughts = json.loads(json.dumps(thoughts, default=str))

    if user_service and user_id:
        response_cost = None
        try:
            response_cost = _extract_response_cost(final_response if use_responses_api else response)
        except Exception:
            response_cost = None
        if response_cost is not None:
            user_service.add_usage(user_id, response_cost, basic_info=user_basic_info)

    return content, thoughts


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
    Stream LLM responses using litellm's async streaming.

    This function provides streaming capability while maintaining the same
    interface and checks as call_llm (user allowance, logging, etc).

    Yields chunks from the LLM response stream.

    Note: Cost tracking is not available for streaming responses.
    """
    model_string = f"{provider}/{model}"

    # Filter out None values from parameters
    filtered_params = {k: v for k, v in parameters.items() if v is not None}

    kwargs = {
        "model": model_string,
        "messages": messages,
        "stream": True,
        **filtered_params,
    }

    # Remove reasoning_effort from kwargs if present (not typically used in streaming)
    kwargs.pop('reasoning_effort', None)

    if user_service is None:
        user_service = get_user_service(get_database_service(settings))
    if user_id is None:
        user_id = "anonymous"

    if user_service and user_id:
        user_service.require_allowance(user_id, basic_info=user_basic_info)

    # Get the effective API key (user's key takes precedence over env var)
    api_key = None
    if user_service and user_id:
        api_key = user_service.get_effective_api_key(user_id, provider, basic_info=user_basic_info)
    
    # If no user-specific key, litellm will use environment variables
    if api_key:
        kwargs["api_key"] = api_key

    try:
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            yield chunk
    except Exception as e:
        observability = get_observability_service()
        observability.log_exception(
            e,
            user_id=user_id,
            metadata={
                "context": "stream_llm",
                "model": model_string,
                "provider": provider,
            }
        )
        raise


