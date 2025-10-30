# webapp/packages/api/user-service/agent_factory/__init__.py
from .remote_mcp_client import RemoteMCPClient
from .prompts import how_to_use_tools, \
    how_to_use_litellm, \
    what_to_do_prompt_template, \
    how_to_use_swagger_tools, \
    how_to_use_gofannon_agents
from litellm import acompletion
from models.agent import GenerateCodeRequest, GenerateCodeResponse, Agent
import json
import asyncio

from services.database_service import get_database_service
from services.llm_service import call_llm
from config import settings
from config.provider_config import PROVIDER_CONFIG

async def generate_agent_code(request: GenerateCodeRequest):
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
    if request.tools:
        system_prompt_parts.append(how_to_use_tools)
    if request.swagger_specs:
        system_prompt_parts.append(how_to_use_swagger_tools) 
    if request.gofannon_agents:
        system_prompt_parts.append(how_to_use_gofannon_agents)  
               
    if request.invokable_models:
        system_prompt_parts.append(how_to_use_litellm)
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

    # Build tools list from config
    built_in_tools = []
    model_tool_config = PROVIDER_CONFIG.get(provider, {}).get("models", {}).get(model, {}).get("built_in_tools", [])
    if request.built_in_tools:
        for tool_id in request.built_in_tools:
            tool_conf = next((t for t in model_tool_config if t["id"] == tool_id), None)
            if tool_conf:
                built_in_tools.append(tool_conf["tool_config"])
    
    config = request.composer_model_config.parameters
    
    async def code_gen_with_thoughts():
        return await call_llm(
            provider=provider,
            model=model,
            messages=code_gen_messages,
            parameters=config,
            tools=built_in_tools if built_in_tools else None,
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

    name_doc_gen_task = acompletion(
        model=f"{provider}/{model}",
        messages=name_doc_messages,
        **name_doc_config
    )
    
    # ---- Run tasks concurrently ----
    (code_body, thoughts), name_doc_response = await asyncio.gather(
        code_gen_with_thoughts(),
        name_doc_gen_task
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
import litellm

async def run(input_dict, tools):
   mcpc = { url : RemoteMCPClient(remote_url = url) for url in tools.keys() }"""
    
    indented_body = "\n".join(["   " + line for line in code_body.split('\n')])
    
    full_code = f"{header}\n{indented_body}"

    # ---- Process Name and Docstring Response ----
    name_doc_content = name_doc_response.choices[0].message.content
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
