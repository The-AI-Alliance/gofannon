import asyncio
import json
from config import settings
from config.provider_config import PROVIDER_CONFIG
from services.database_service import get_database_service
from services.user_service import get_user_service
from typing import Any, Dict, List, Tuple, Optional
import litellm

from services.litellm_logger import ensure_litellm_logging
from services.observability_service import get_observability_service
from services.user_service import UserService

ensure_litellm_logging()

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
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        input_text = content
                    elif isinstance(content, list):
                        # Handle list-format content (e.g., multimodal)
                        input_text = " ".join(
                            item.get("text", "") for item in content 
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
                response_status = await litellm.aget_responses(response_id=response_obj.id)
                if response_status.status == "completed":
                    final_response = response_status
                    break
            
            if final_response:
                # Extract thoughts/summary from the first output block
                if len(final_response.output) > 0 and final_response.output[0] and hasattr(final_response.output[0], 'summary') and final_response.output[0].summary:
                    summary_texts = [s.text for s in final_response.output[0].summary if hasattr(s, 'text')]
                    thoughts = {"summary": summary_texts}
                elif len(final_response.output) > 0 and final_response.output[0]: # Fallback for other tool outputs
                     thoughts = final_response.output[0].model_dump()
                
                # Extract content from the second output block (or first if it's the only one with content)
                if len(final_response.output) > 1 and final_response.output[1] and final_response.output[1].content:
                    content = final_response.output[1].content[0].text
                elif len(final_response.output) > 0 and final_response.output[0] and final_response.output[0].content:
                     # Fallback if there's only one output block
                    content = final_response.output[0].content[0].text
            else:
                raise Exception("Polling for OpenAI Responses API timed out.")

        except Exception as e:
            observability = get_observability_service()
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