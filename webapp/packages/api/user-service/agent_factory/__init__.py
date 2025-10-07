from .remote_mcp_client import RemoteMCPClient
from .prompts import how_to_use_tools, how_to_use_litellm
from litellm import acompletion
from models.agent import GenerateCodeRequest, GenerateCodeResponse
import json

async def generate_agent_code(request: GenerateCodeRequest):
    """
    Generates agent code based on the provided configuration.
    """
    ## Generate MCPs and get doc strings of tools
    mcp_clients = []
    tool_docs = ""
    if request.tools:
        for url, selected_tools in request.tools.items():
            mcp_client = RemoteMCPClient(remote_url=url)
            tools = await mcp_client.list_tools()
            tool_docs += f"\nmcpc[{url}]".join([mcp_client.get_tool_doc(tool.name) for tool in tools if tool.name in selected_tools])
            mcp_clients.append(mcp_client)
    
    ## Generate docs for invokable models
    model_docs = ""
    if request.invokable_models:
        model_docs += "The agent can invoke the following models using `litellm.acompletion`:\n"
        for model_config in request.invokable_models:
            model_name = f"{model_config.provider}/{model_config.model}"
            model_docs += f"- `{model_name}`\n"
        model_docs += "\n"
   
    input_schema_str = json.dumps(request.input_schema, indent=4)
    output_schema_str = json.dumps(request.output_schema, indent=4)

    what_to_do =  f"You will be given instructions for a python function to create.\nThe input schema is:\n{input_schema_str}\nThe output schema is:\n{output_schema_str}\nONLY return the code as a sting (ready to be executed),not as a markdown codeblock, no explanations.\n"
    
    
    system_prompt_parts = []
    if tool_docs:
        system_prompt_parts.append(tool_docs)
    if model_docs:
        system_prompt_parts.append(model_docs)
    if request.tools:
        system_prompt_parts.append(how_to_use_tools)
    if request.invokable_models:
        system_prompt_parts.append(how_to_use_litellm)
    system_prompt_parts.append(what_to_do)
    system_prompt = "\n\n".join(system_prompt_parts)  

    print("[DEBUG] System Prompt:\n", system_prompt)
    model = request.composer_model_config.model
    provider = request.composer_model_config.provider
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.description},
    ]
    print("[DEBUG] Messages:\n", messages)
    print("[DEBUG] Model:", model)
    print("[DEBUG] Model Config:", request.composer_model_config.parameters)
    config = request.composer_model_config.parameters
    response = await acompletion(
                model=f"{provider}/{model}",
                messages=messages,
                **config
            )

    code = response.choices[0].message.content
    return GenerateCodeResponse(code=code.strip())