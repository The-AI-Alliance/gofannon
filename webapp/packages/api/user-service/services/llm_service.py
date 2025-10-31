import litellm
import asyncio
import json
from config.provider_config import PROVIDER_CONFIG
from typing import Any, Dict, List, Tuple, Optional

async def call_llm(
    provider: str,
    model: str,
    messages: List[Dict[str, Any]],
    parameters: Dict[str, Any],
    tools: Optional[List[Dict[str, Any]]] = None,
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

    kwargs = {
        "model": model_string,
        "messages": messages,
        **parameters,
    }

    reasoning_effort = kwargs.pop('reasoning_effort', 'disable')

    if tools:
        kwargs["tools"] = tools

    if api_style == "responses":
        # Use aresponses and aget_responses for OpenAI's special tools like built-in web search
        kwargs.pop('messages', None) # aresponses uses 'input' not 'messages'
        if reasoning_effort != 'disable':
            kwargs['reasoning'] = {'effort': reasoning_effort, 'summary': 'auto'}

        try:
            # Note: The 'input' for aresponses is different from 'messages'
            input_text = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), "")
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
            print(f"Error using litellm.aresponses: {e}")
            raise
    else:
        # Standard acompletion call for most models
        if reasoning_effort != 'disable':
            kwargs['reasoning_effort'] = reasoning_effort

        response = await litellm.acompletion(**kwargs)
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

    return content, thoughts