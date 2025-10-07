
how_to_use_tools = """
    Consider the tool docs above. Presume there is a dictionary of object called `mcpc` where each key is the MCP URL and the value is an object with methods corresponding to the tools.
    Each item in the dictionary is an instance of a class that has a method `call`- here is the docstring for `async def call(self, tool_name: str, **params: Any) -> Any:`:
        Calls a specific tool exposed by the remote MCP server.

        This method sends a request to the server to execute a function 
        (a "tool") by its registered name, passing the required arguments.

        :param tool_name: 
            The **name** of the tool (function) as listed by `list_tools()`. 
            (e.g., 'query_database', 'add_item', 'calculate_tax').
        :param params: 
            Keyword arguments (key=value) corresponding to the tool's expected 
            input parameters as defined in its schema/docstring.
            
            - **Required arguments** must be provided.
            - **Optional arguments** can be omitted.
            
            The type and name of the parameters must match the tool's definition 
            (e.g., if a tool expects `count: int`, you must pass `count=5`).

        :raises ValueError: 
            If the `tool_name` is not found on the server, or if arguments 
            are missing/invalid (though the server handles deep validation).
        
        :return: 
            The result returned from the remote tool execution. This is typically
            a Python dictionary, list, string, or number, depending on what the 
            server-side tool function returns.
            
        :Example:
        >>> # Assuming the server has a tool named 'calculate_tax' defined as:
        >>> # def calculate_tax(amount: float, rate: float) -> float: ...
        >>> tax_result = await client.call(
        ...     tool_name="calculate_tax", 
        ...     amount=100.00, 
        ...     rate=0.07 
        ... )
        >>> print(tax_result) 
        8.25 # (Example Output)
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
        (e.g., 'gpt-4', 'openai/gpt-3.5-turbo', 'claude-3-opus', 'gemini/gemini-pro').
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