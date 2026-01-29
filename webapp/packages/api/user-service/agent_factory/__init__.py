# webapp/packages/api/user-service/agent_factory/__init__.py
from .remote_mcp_client import RemoteMCPClient
from .prompts import how_to_use_tools, \
    how_to_use_llm, \
    what_to_do_prompt_template, \
    how_to_use_swagger_tools, \
    how_to_use_gofannon_agents
from models.agent import GenerateCodeRequest, GenerateCodeResponse, Agent
import json
import asyncio

from services.database_service import get_database_service
from services.llm_service import call_llm
from services.litellm_logger import ensure_litellm_logging
from config import settings
from config.provider_config import PROVIDER_CONFIG

ensure_litellm_logging()

async def generate_agent_code(request: GenerateCodeRequest, user_id: str = None, user_basic_info: dict = None):
    """
    Generates agent code based on the provided configuration.
    """
    ## Generate MCPs and get doc strings of tools
    mcp_tool_docs = ""
    if request.tools:
        tool_docs_parts = []
        for url, selected_tools in request.tools.items():
            mcp_client = RemoteMCPClient(remote_url=url)
            tools = await mcp_client.list_tools()
            docs_for_url = [
                doc for tool in tools if tool.name in selected_tools 
                and (doc := mcp_client.get_tool_doc(tool.name)) is not None
            ]
            if docs_for_url:
                tool_docs_parts.append(f"## Tools from {url}\n\n" + "\n\n".join(docs_for_url))
        mcp_tool_docs = "\n\n".join(tool_docs_parts)

    swagger_docs = ""
    if request.swagger_specs:
        from .swagger_parser import parse_spec_and_generate_docs
        swagger_docs_parts = []
        for spec in request.swagger_specs:
            docs_for_spec = parse_spec_and_generate_docs(spec.name, spec.content)
            if docs_for_spec:
                swagger_docs_parts.append(docs_for_spec)
        swagger_docs = "\n\n".join(swagger_docs_parts)
    tool_docs = "\n\n".join(filter(None, [swagger_docs, mcp_tool_docs]))

    gofannon_agent_docs = ""
    if request.gofannon_agents:
        db = get_database_service(settings)
        agent_docs_parts = ["## Gofannon Agents\n\nThe agent can call the following other Gofannon agents using the `gofannon_client`:\n"]
        for agent_id in request.gofannon_agents:
            try:
                agent_data = db.get("agents", agent_id)
                agent = Agent(**agent_data)
                doc = f"""### Agent: `{agent.name}`
**Description**: {agent.description}

**Docstring**:
```
{agent.docstring or 'No docstring available.'}
```

**How to call**:
You **MUST** use `await` to call this agent using the `gofannon_client`.

result = await gofannon_client.call(agent_name='{agent.name}', input_dict={{...}})
"""
                agent_docs_parts.append(doc)
            except Exception as e:
                print(f"Could not load agent {agent_id} for doc generation: {e}")
        gofannon_agent_docs = "\n\n".join(agent_docs_parts)

    built_in_tools_docs = ""

    ## Generate docs for invokable models with their configured parameters and built-in tools
    model_docs = ""
    if request.invokable_models:
        model_docs += "## Invokable Models\n\nThe agent can invoke the following models using `call_llm`.\nUse the configured parameters and built-in tool selections shown for each model:\n\n"
        for model_config in request.invokable_models:
            provider = model_config.provider
            model_name = model_config.model
            model_docs += f"### `{provider}/{model_name}`\n"

            # Look up built-in tools from provider config
            provider_models = PROVIDER_CONFIG.get(provider, {}).get("models", {})
            model_info = provider_models.get(model_name, {})
            built_in_tools = model_info.get("built_in_tools", [])
            configured_params = model_config.parameters or {}
            selected_tool_id = model_config.built_in_tool

            model_docs += f"**Configured Parameters:** `{json.dumps(configured_params)}`\n"

            selected_tool = None
            if selected_tool_id:
                selected_tool = next(
                    (tool for tool in built_in_tools if tool.get("id") == selected_tool_id),
                    None
                )
                if selected_tool:
                    tool_desc = selected_tool.get("description", "")
                    tool_config = selected_tool.get("tool_config", {})
                    model_docs += f"**Selected Built-in Tool:** `{selected_tool_id}`"
                    if tool_desc:
                        model_docs += f" - {tool_desc}"
                    model_docs += "\n"
                    model_docs += f"Tool config to pass: `{json.dumps(tool_config)}`\n"
                else:
                    model_docs += f"**Selected Built-in Tool:** `{selected_tool_id}` (no tool config found)\n"
            else:
                model_docs += "No built-in tool selected for this model.\n"

            model_docs += "\n**Example call_llm usage for this model:**\n```python\n"
            tools_line = "None"
            if selected_tool and selected_tool.get("tool_config") is not None:
                tools_line = f"[{json.dumps(selected_tool.get('tool_config', {}))}]"
            model_docs += f"""content, thoughts = await call_llm(
    provider="{provider}",
    model="{model_name}",
    messages=[{{"role": "user", "content": "Your query here"}}],
    parameters={json.dumps(configured_params)},
    tools={tools_line},
    user_service=None,
    user_id=None,
)
```\n\n"""
   
    input_schema_str = json.dumps(request.input_schema, indent=4)
    output_schema_str = json.dumps(request.output_schema, indent=4)

    what_to_do = what_to_do_prompt_template.format(
        input_schema=input_schema_str,
        output_schema=output_schema_str
    )
    
    system_prompt_parts = []
    if tool_docs:
        system_prompt_parts.append(tool_docs)
    if gofannon_agent_docs:
        system_prompt_parts.append(gofannon_agent_docs)        
    if model_docs:
        system_prompt_parts.append(model_docs)
    if built_in_tools_docs:
        system_prompt_parts.append(built_in_tools_docs)
    if request.tools:
        system_prompt_parts.append(how_to_use_tools)
    if request.swagger_specs:
        system_prompt_parts.append(how_to_use_swagger_tools) 
    if request.gofannon_agents:
        system_prompt_parts.append(how_to_use_gofannon_agents)  
               
    if request.invokable_models:
        system_prompt_parts.append(how_to_use_llm)
    system_prompt_parts.append(what_to_do)
    system_prompt = "\n\n".join(system_prompt_parts)  
    
    model = request.composer_model_config.model
    provider = request.composer_model_config.provider
    
    config = request.composer_model_config.parameters.copy() # Make a copy to avoid modifying the original request object
    
    # --- Special handling for Gemini tools ---
    if provider == "gemini" and "tools" in config:
        selected_gemini_tools = config["tools"]
        if isinstance(selected_gemini_tools, list) and all(isinstance(t, str) for t in selected_gemini_tools):
            # Transform ["toolName"] to [{"toolName": {}}]
            config["tools"] = [{tool_name: {}} for tool_name in selected_gemini_tools]
        else:
            # If it's not the expected list of strings, log a warning
            print(f"Warning: Gemini tools parameter has unexpected format: {selected_gemini_tools}. Skipping transformation.")
            # Optionally, remove it if it's malformed to prevent errors in litellm
            # del config["tools"]

    # ---- Code Generation Task ----
    code_gen_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.description},
    ]

    # Note: built_in_tools are NOT passed to the code generation LLM.
    # They are documented in the prompt so the LLM generates code that uses
    # the web_search() function available in the sandbox, rather than having
    # the LLM execute web searches during code generation.
    
    config = request.composer_model_config.parameters
    
    async def code_gen_with_thoughts():
        return await call_llm(
            provider=provider,
            model=model,
            messages=code_gen_messages,
            parameters=config,
            tools=None,  # Don't pass tools - we want code generation, not tool execution
            user_id=user_id,
            user_basic_info=user_basic_info,
        )

    # ---- Friendly Name and Docstring Generation Task ----
    name_doc_prompt = f"""
Based on the following description and schemas for a Python function, generate a suitable `friendly_name` for the function (in snake_case) and a Python docstring for it.
The function signature in the docstring should use the `friendly_name` you generate, and reflect the input and output schemas.

Description:
{request.description}

Input Schema:
```json
{input_schema_str}
```

Output Schema:
```json
{output_schema_str}
```

Return your response as a JSON object with two keys: "friendly_name" and "docstring".
Do not include any other text or markdown formatting around the JSON object.
"""
    name_doc_messages = [
        {"role": "system", "content": "You are a helpful assistant that generates Python function names and docstrings in JSON format."},
        {"role": "user", "content": name_doc_prompt}
    ]
    
    name_doc_config = request.composer_model_config.parameters.copy()
    if provider == "openai":
        name_doc_config['response_format'] = { "type": "json_object" }

    async def name_doc_generation():
        content, _ = await call_llm(
            provider=provider,
            model=model,
            messages=name_doc_messages,
            parameters=name_doc_config,
            user_id=user_id,
            user_basic_info=user_basic_info,
        )
        return content

    # ---- Run tasks concurrently ----
    (code_body, thoughts), name_doc_content = await asyncio.gather(
        code_gen_with_thoughts(),
        name_doc_generation()
    )

    # ---- Process Code Generation Response ----
    # Clean up potential markdown formatting from the response
    if code_body.strip().startswith("```python"):
        code_body = code_body.strip()[len("```python"):].strip()
    if code_body.strip().startswith("```"):
        code_body = code_body.strip()[len("```"):].strip()
    if code_body.strip().endswith("```"):
        code_body = code_body.strip()[:-len("```")].strip()

    header = """from agent_factory.remote_mcp_client import RemoteMCPClient
from services.llm_service import call_llm
import httpx

async def run(input_dict, tools):
    mcpc = { url : RemoteMCPClient(remote_url = url) for url in tools.keys() }
    http_client = httpx.AsyncClient()
    try:"""
    
    # Use dedent to remove any common leading whitespace, then re-indent with 8 spaces (inside try block)
    import textwrap
    dedented_body = textwrap.dedent(code_body)
    indented_body = "\n".join(["        " + line if line.strip() else "" for line in dedented_body.split('\n')])
    
    footer = """
    finally:
        await http_client.aclose()"""
    
    full_code = f"{header}\n{indented_body}\n{footer}"

    # ---- Process Name and Docstring Response ----
    try:
        # Clean up potential markdown
        if name_doc_content.strip().startswith("```json"):
            name_doc_content = name_doc_content.strip()[len("```json"):].strip()
        if name_doc_content.strip().endswith("```"):
            name_doc_content = name_doc_content.strip()[:-len("```")].strip()
            
        name_doc_json = json.loads(name_doc_content)
        friendly_name = name_doc_json.get("friendly_name", "unnamed_agent_function")
        docstring = name_doc_json.get("docstring", "No docstring generated.")
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error parsing name/docstring JSON: {e}")
        print(f"LLM response for name/docstring was: {name_doc_content}")
        friendly_name = "parsing_error_function"
        docstring = f"Could not parse docstring from LLM response:\n{name_doc_content}"

    return GenerateCodeResponse(code=full_code, friendly_name=friendly_name, docstring=docstring, thoughts=thoughts)
