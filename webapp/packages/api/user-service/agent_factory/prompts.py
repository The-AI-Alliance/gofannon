how_to_use_tools = """
# How to Call Tools

You are provided with a pre-initialized dictionary of clients called `mcpc`.
- The keys of `mcpc` are the MCP server URLs (e.g., 'http://example.com/mcp').
- The values are client objects used to call tools on that server.

**ALL tool calls are asynchronous and MUST use the `await` keyword.**

To call a tool, you **MUST** use the `.call()` method on the appropriate client object from the `mcpc` dictionary.

Here is the documentation for the `call` method:
`async def call(self, tool_name: str, **params: Any) -> Any:`
    Calls a specific tool exposed by the remote MCP server.

    This method sends a request to the server to execute a function
    (a "tool") by its registered name, passing the required arguments.

    :param tool_name:
        The **name** of the tool (function) as a string.
        (e.g., 'query_database', 'add_item').
    :param params:
        Keyword arguments (key=value) corresponding to the tool's expected
        input parameters.

    :return:
        The result from the remote tool. The type depends on what the tool returns.

    :Example:
    >>> # To call the 'calculate_tax' tool on the server at 'http://tax.api/mcp'
    >>> tax_result = await mcpc['http://tax.api/mcp'].call(
    ...     tool_name="calculate_tax",
    ...     amount=100.00,
    ...     rate=0.07
    ... )
    >>> print(tax_result)
    7.00
    
"""

how_to_use_llm = """
You have access to the `call_llm` function for making calls to language models.
The specific models you can call are listed in the section above.
For each invokable model, you are given the configured parameters and any selected built-in tool.
When you call a listed model, pass the parameters exactly as shown, and include the `tools` argument
only when a built-in tool is selected for that model.

To make a call, use `await call_llm()`:

async def call_llm(provider: str, model: str, messages: list, parameters: dict, ...) -> tuple[str, Any]:
    '''
    Makes an asynchronous call to a language model through the centralized LLM service.

    :param provider:
        The provider name (e.g., 'openai', 'anthropic', 'gemini').
    :param model:
        The model name without the provider prefix (e.g., 'gpt-4', 'claude-3-opus').
    :param messages:
        A list of dictionaries representing the conversation history,
        following the format: `[{"role": "user", "content": "Hello"}, ...]`.
    :param parameters:
        A dictionary of additional parameters to pass to the model provider's API,
        such as `temperature`, `max_tokens`, `top_p`, etc.
    :param tools:
        Optional list of built-in tool configurations. See "Using Built-in Tools" below.
    :param user_service:
        Optional user service for tracking usage (set to None if not needed).
    :param user_id:
        Optional user ID for tracking usage (set to None if not needed).

    :return:
        A tuple of (content, thoughts) where content is the string response
        and thoughts contains any reasoning/tool call information.

    :Example:
    >>> content, thoughts = await call_llm(
    ...     provider="openai",
    ...     model="gpt-4",
    ...     messages=[{"role": "user", "content": "Summarize this for me."}],
    ...     parameters={"temperature": 0.7, "max_tokens": 150},
    ...     user_service=None,
    ...     user_id=None,
    ... )
    >>> print(content)
    "This is a summary." # (Example Output)
    '''

## Using Built-in Tools

Some models support built-in tools like web search, code execution, or URL context.
To use these tools, pass the `tools` parameter with a list of tool configurations.

**OpenAI Web Search** (for models like gpt-4o, gpt-5, o3, etc.):
```python
content, thoughts = await call_llm(
    provider="openai",
    model="gpt-4o",
    messages=[{"role": "user", "content": "What are the latest news about AI?"}],
    parameters={},
    tools=[{"type": "web_search", "search_context_size": "medium"}],
    user_service=None,
    user_id=None,
)
```

**Gemini Google Search** (for models like gemini-2.5-pro, gemini-2.5-flash):
```python
content, thoughts = await call_llm(
    provider="gemini",
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Search for recent developments in quantum computing."}],
    parameters={},
    tools=[{"google_search": {}}],
    user_service=None,
    user_id=None,
)
```

**Gemini Code Execution**:
```python
content, thoughts = await call_llm(
    provider="gemini",
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Calculate the factorial of 10 using Python."}],
    parameters={},
    tools=[{"codeExecution": {}}],
    user_service=None,
    user_id=None,
)
```

**Note:** Not all models support all tools. Check the model documentation above to see which built-in tools are available for each model.

## Batch Processing Guidance

When processing large datasets or multiple items, follow these best practices to avoid token limits and ensure reliable results:

### Token-Aware Batching
- Estimate ~4 characters per token when calculating batch sizes
- For large inputs, process in batches of 10-50 items depending on item size
- Leave headroom for the response (at least 25% of max_tokens)

### Progressive Consolidation Pattern
For tasks requiring analysis of many items (e.g., summarizing 100 documents):
```python
# Process in batches, then consolidate
batch_size = 20
batch_results = []

for i in range(0, len(items), batch_size):
    batch = items[i:i + batch_size]
    result, _ = await call_llm(
        provider=provider,
        model=model,
        messages=[{"role": "user", "content": f"Analyze these items: {batch}"}],
        parameters=parameters,
    )
    batch_results.append(result)

# Final consolidation pass
final_result, _ = await call_llm(
    provider=provider,
    model=model,
    messages=[{"role": "user", "content": f"Consolidate these analyses: {batch_results}"}],
    parameters=parameters,
)
```

### Skip Lists for Efficiency
When processing items that may fail or be irrelevant:
```python
skip_patterns = ["404", "access denied", "not found", "empty"]
results = []

for item in items:
    if any(pattern in str(item).lower() for pattern in skip_patterns):
        continue
    # Process item...
```

### Output Format Recommendations
- **Prefer Markdown over JSON** for large outputs - it's more token-efficient and readable
- Use structured Markdown (headers, lists, tables) for organized data
- Reserve JSON for programmatic consumption or when exact structure is required

### Error Handling for Batch Operations
```python
async def process_with_retry(item, max_retries=3):
    for attempt in range(max_retries):
        try:
            result, _ = await call_llm(...)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                return {"error": str(e), "item": item}
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Memory Management
- For very large datasets (1000+ items), consider streaming results to storage
- Don't accumulate all results in memory before returning
- Use generators or async iterators when possible
"""


how_to_use_swagger_tools = """
# How to Call Tools from an OpenAPI/Swagger Spec

You are also provided with a pre-initialized asynchronous HTTP client called `http_client` from the `httpx` library.
You **MUST** use this client to make any HTTP requests to the APIs defined in the OpenAPI/Swagger specifications.

**Important notes:**
- The `http_client` is configured to automatically follow HTTP redirects.
- Always prefer `https://` URLs over `http://` URLs when available.
- **ALL HTTP calls are asynchronous and MUST use the `await` keyword.**

Here is an example of how to use `http_client` to make a GET request:

:Example:
>>> # To call the 'getUser' operation from the 'user_api' spec
>>> # The base URL is provided in the tool's documentation.
>>> response = await http_client.get(
...     "https://api.example.com/v1/users/123",
...     headers={"Authorization": "Bearer YOUR_API_KEY"} # if needed
... )
>>> # ALWAYS check if the request was successful
>>> response.raise_for_status() 
>>> user_data = response.json()
>>> print(user_data)

To make a POST request with a JSON body:
:Example:
>>> new_user_data = {"name": "John Doe", "email": "john.doe@example.com"}
>>> response = await http_client.post(
...     "https://api.example.com/v1/users",
...     json=new_user_data
... )
>>> response.raise_for_status()
>>> created_user = response.json()

Refer to the specific documentation for each tool to know the correct URL, HTTP method, and what parameters (query, path, body) are expected.
"""

how_to_use_gofannon_agents = """
# How to Call Other Gofannon Agents

You are provided with a pre-initialized client called `gofannon_client` to call other Gofannon agents that have been imported into your context.

**ALL agent calls are asynchronous and MUST use the `await` keyword.**

To call another agent, you **MUST** use the `.call()` method on the `gofannon_client`.

Here is the documentation for the `call` method:
`async def call(self, agent_name: str, input_dict: dict) -> Any:`
    Calls a specific Gofannon agent by its name.

    :param agent_name:
        The **name** of the agent as a string.
    :param input_dict:
        A dictionary conforming to the target agent's input schema.

    :return:
        The result from the remote agent. The type depends on what the agent returns.

    :Example:
    >>> # To call the 'stock_analyzer' agent
    >>> analysis = await gofannon_client.call(
    ...     agent_name="stock_analyzer",
    ...     input_dict={"stock_symbol": "GOOGL"}
    ... )
    >>> print(analysis)
    {"recommendation": "buy", "confidence": 0.85}
"""

how_to_use_data_store = """
# How to Use the Data Store

You are provided with a pre-initialized `data_store` object for persisting data across agent executions.
Data stored here is available to ALL agents owned by the same user, enabling workflows where one agent
creates data that another agent consumes.

**Data store operations are synchronous (no `await` needed).**

## Discovering Available Data

Before querying, you can discover what namespaces contain data:

```python
# List all namespaces that have data
namespaces = data_store.list_namespaces()
# Returns: ["default", "files:apache/repo", "summary:apache/repo", ...]

# Then work with discovered namespaces
for ns in namespaces:
    if ns.startswith("files:"):
        files_ns = data_store.use_namespace(ns)
        keys = files_ns.list_keys()
        print(f"Found {len(keys)} files in {ns}")
```

## Basic Operations

```python
# Store a value (any JSON-serializable data)
data_store.set("my-key", {"analysis": "results", "score": 95})

# Retrieve a value (returns None if not found)
value = data_store.get("my-key")

# Retrieve with a default value
value = data_store.get("missing-key", default={"empty": True})

# Delete a value
data_store.delete("my-key")

# List all keys in the current namespace
keys = data_store.list_keys()

# List keys matching a prefix
keys = data_store.list_keys(prefix="analysis:")
```

## Using Namespaces

Namespaces help organize data by purpose. The default namespace is "default".

```python
# Switch to a specific namespace
summaries = data_store.use_namespace("repo-summaries")
summaries.set("src/main.py", {"functions": ["main", "init"], "lines": 150})

# Read from the namespace
file_info = summaries.get("src/main.py")

# Use different namespaces for different purposes
cache = data_store.use_namespace("analysis-cache")
cache.set("last-run", {"timestamp": "2026-02-03", "status": "complete"})
```

## Batch Operations

```python
# Set multiple values at once
data_store.set_many({
    "file:a.py": {"lines": 100},
    "file:b.py": {"lines": 200},
    "file:c.py": {"lines": 50},
})

# Get multiple values at once
results = data_store.get_many(["file:a.py", "file:b.py"])
# Returns: {"file:a.py": {"lines": 100}, "file:b.py": {"lines": 200}}
```

## Common Patterns

### Discovering and searching across all data
```python
# Find all namespaces with data
namespaces = data_store.list_namespaces()

# Search for data across namespaces
for ns in namespaces:
    ns_store = data_store.use_namespace(ns)
    keys = ns_store.list_keys()
    # Process keys...
```

### Caching expensive operations
```python
cache_key = f"analysis:{file_path}"
cached = data_store.get(cache_key)
if cached:
    return cached

# Do expensive analysis...
result = await call_llm(...)

# Cache for future runs
data_store.set(cache_key, result)
return result
```

### Building up results across multiple runs
```python
summaries = data_store.use_namespace("code-summaries")

# Store this run's result
summaries.set(input_dict["file_path"], analysis_result)

# Get all accumulated results
all_keys = summaries.list_keys()
all_summaries = summaries.get_many(all_keys)
```

### Passing data between agents
```python
# Agent A: Store results for Agent B
data_store.use_namespace("shared-analysis").set("quarterly-report", report_data)

# Agent B: Read Agent A's results
report = data_store.use_namespace("shared-analysis").get("quarterly-report")
```

### Working with dynamic namespace names
```python
# Namespaces often include context like repo names
# e.g., "files:apache/tooling-trusted-releases", "summary:apache/tooling-trusted-releases"

repo_name = input_dict.get("repo", "")
files_ns = data_store.use_namespace(f"files:{repo_name}")
summary_ns = data_store.use_namespace(f"summary:{repo_name}")

# Store file content
files_ns.set(file_path, file_content)

# Store file summary
summary_ns.set(file_path, {"summary": "...", "key_points": [...]})
```
"""

what_to_do_prompt_template = """
You are tasked with writing the body of an asynchronous Python function with the signature `async def run(input_dict: dict, tools: dict) -> dict:`.

This function will receive:
- `input_dict`: A dictionary conforming to the following input schema.
- `tools`: A dictionary of tool configurations.

An asynchronous HTTP client `http_client` is available for making API calls to Swagger/OpenAPI specs.
A client for calling other Gofannon agents named `gofannon_client` is also available if you have imported any.
A dictionary of MCP clients named `mcpc` is already initialized for you like this:
`mcpc = {{ url : RemoteMCPClient(remote_url = url) for url in tools.keys() }}`
You can use it to call tools as described in the documentation.

**Available in the Sandbox:**
- `mcpc` - Dictionary of MCP clients for calling external tools
- `http_client` - Async HTTP client (httpx) for REST API calls
- `call_llm` - For calling language models via `await call_llm(provider, model, messages, parameters, ...)`
- `gofannon_client` - For calling other Gofannon agents
- `data_store` - For persisting and sharing data across agent executions (see data store documentation)
- `asyncio`, `json`, `re` - Standard Python libraries

**Input Schema:**
```json
{input_schema}
```

**Output Schema:**
The function **MUST** return a dictionary that conforms to the following output schema.
```json
{output_schema}
```

**Instructions:**
Your task is to implement the logic for this function based on the user's request.
ONLY return the Python code for the function body.
- Do NOT include the `async def run(...)` function signature.
- Do NOT include any imports.
- Do NOT wrap the code in Markdown backticks (```).
- Do NOT add any explanations or surrounding text.
- Your code will be executed inside an `async` function, so you can and should use `await` for async calls.
"""


how_to_build_demo_app_template = """
You are an expert web developer. Your task is to create a single-page web application using only vanilla HTML, CSS, and JavaScript.

**Restrictions:**
- **DO NOT** use any frameworks or libraries like React, Vue, Angular, jQuery, etc. Stick to modern, standard browser APIs.
- Your entire output **MUST** be a single JSON object.

**Instructions:**
1. You will be given a user's description of what the app should look like and do.
2. You will also be given a list of available REST APIs that you can call to fetch data.
3. The base URL for all API calls is available in a pre-defined JavaScript constant called `API_BASE_URL`. You **MUST** use this constant when making `fetch` requests.
   For example, to call an endpoint `/rest/my_api`, your JavaScript code should look like this: `fetch(`${{API_BASE_URL}}/rest/my_api`, ...)`
4. Make the user interface clean, modern, and user-friendly. Use CSS for styling.
5. Your JavaScript should be well-structured and handle API calls asynchronously using `async/await` and `fetch`. It should also include error handling for API calls.

**Output Format:**
Return your response as a single, valid JSON object with three keys: "html", "css", and "js".
- `html`: A string containing the HTML body content. Do not include `<html>`, `<head>`, or `<body>` tags.
- `css`: A string containing all the CSS styles for the application. Do not include `<style>` tags.
- `js`: A string containing all the JavaScript logic for the application. Do not include `<script>` tags.

**Available APIs:**
{api_docs}

**User's Request for the application:**
{user_prompt}
"""