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

how_to_use_litellm = """
You also have access to the `litellm` library for making calls to other language models.
The specific models you can call are listed in the section above.

To make a call, use `await litellm.acompletion()`:

async def acompletion(model: str, messages: list, **kwargs):
    '''
    Makes an asynchronous call to a language model.

    :param model: 
        The name of the model to call, including the provider prefix.
        (e.g., 'openai/gpt-4', 'openai/gpt-3.5-turbo', 'claude-3-opus', 'gemini/gemini-pro').
    :param messages: 
        A list of dictionaries representing the conversation history,
        following the format: `[{"role": "user", "content": "Hello"}, ...]`.
    :param kwargs: 
        Additional parameters to pass to the model provider's API,
        such as `temperature`, `max_tokens`, `top_p`, etc.

    :return: 
        A `ModelResponse` object from litellm. To get the content,
        access `response.choices[0].message.content`.

    :Example:
    >>> import litellm
    >>> response = await litellm.acompletion(
    ...     model="gpt-3.5-turbo",
    ...     messages=[{"role": "user", "content": "Summarize this for me."}],
    ...     temperature=0.7,
    ...     max_tokens=150
    ... )
    >>> summary = response.choices[0].message.content
    >>> print(summary)
    "This is a summary." # (Example Output)
    '''
"""


how_to_use_swagger_tools = """
# How to Call Tools from an OpenAPI/Swagger Spec

You are also provided with a pre-initialized asynchronous HTTP client called `http_client` from the `httpx` library.
You **MUST** use this client to make any HTTP requests to the APIs defined in the OpenAPI/Swagger specifications.

**ALL HTTP calls are asynchronous and MUST use the `await` keyword.**

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

