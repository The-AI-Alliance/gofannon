# webapp/packages/api/user-service/agent_factory/swagger_parser.py
import yaml
import json
from typing import Any, Dict, List

def _format_param_schema(param: Dict[str, Any]) -> str:
    """Formats a single parameter schema for the docstring."""
    name = param.get('name', 'N/A')
    location = param.get('in', 'N/A')
    p_schema = param.get('schema', {})
    p_type = p_schema.get('type', 'any')
    required = param.get('required', False)
    req_str = "required" if required else "optional"
    description = param.get('description', '')
    return f"- `{name}` ({p_type}, in {location}, {req_str}): {description}"

def parse_spec_and_generate_docs(spec_name: str, spec_content: str) -> str:
    """
    Parses a Swagger/OpenAPI spec content (JSON or YAML) and generates markdown-formatted
    docstrings for all its operations.
    """
    try:
        spec = yaml.safe_load(spec_content)
    except yaml.YAMLError:
        try:
            spec = json.loads(spec_content)
        except json.JSONDecodeError:
            return f"## Error parsing spec: {spec_name}\n\nCould not parse content as YAML or JSON."

    base_url = ""
    if 'servers' in spec and spec['servers']:
        base_url = spec['servers'][0].get('url', '')

    docs_parts = [f"## Tools from OpenAPI spec: `{spec_name}`\n\n**Base URL**: `{base_url}`\n"]

    paths = spec.get('paths', {})
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                continue
            
            operation_id = operation.get('operationId', f"{method.upper()}_{path.replace('/', '_')}")
            summary = operation.get('summary', '')
            description = operation.get('description', summary) # Fallback to summary
            
            doc = f"### Tool: `{operation_id}`\n"
            doc += f"**Description**: {description}\n"
            doc += f"**Endpoint**: `HTTP {method.upper()}` `{base_url}{path}`\n\n"

            params = operation.get('parameters', [])
            if params:
                params_md = "\n".join([_format_param_schema(p) for p in params])
                doc += f"**Parameters**:\n{params_md}\n\n"

            request_body = operation.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                if 'application/json' in content:
                    schema = content['application/json'].get('schema', {})
                    doc += "**Request Body** (JSON):\n"
                    doc += f"```json\n{json.dumps(schema, indent=2)}\n```\n\n"
            
            doc += "**How to call**:\nUse the `http_client` to make a `{method.upper()}` request to the endpoint URL.\n"
            docs_parts.append(doc)

    return "\n".join(docs_parts)
