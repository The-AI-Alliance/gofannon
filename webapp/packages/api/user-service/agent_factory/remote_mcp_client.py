import asyncio
from typing import Any, Dict, List, Optional
from fastmcp import Client
from fastmcp.tools.tool import Tool
from fastmcp.client.auth import BearerAuth

class RemoteMCPClient:
    """
    A Colab/Jupyter-friendly client for a remote Model Context Protocol (MCP) server.

    All public methods are async and should be called using 'await' in a notebook cell.
    """

    def __init__(self, remote_url: str, auth_token: Optional[str] = None):
        """
        Initializes the client.
        """
        self.remote_url = remote_url
        self.auth: Optional[BearerAuth] = BearerAuth(token=auth_token) if auth_token else None
        self.mcp_client = Client(self.remote_url, auth=self.auth)
        self._tools: List[Tool] = []

    async def list_tools(self) -> List[Tool]:
        """
        Connects to the server, lists all exposed tools, and stores them.

        This method is now asynchronous and uses 'await'.
        :return: A list of Tool objects.
        """
        print(f"Connecting to MCP server at: {self.remote_url}...")
        async with self.mcp_client:
            tools_result = await self.mcp_client.list_tools()
            self._tools = tools_result
            print(f"Found {len(self._tools)} tools.")
        return self._tools

    def get_tool_doc(self, tool_name: str) -> Optional[str]:
        """
        Retrieves a Python-like docstring for a specific tool, including
        an example of how to call it with the MCP client.
        """
        for tool in self._tools:
            if tool.name == tool_name:
                params = []
                schema = tool.inputSchema.get('properties', {})
                required = tool.inputSchema.get('required', [])
                example_args_list = []

                for name, props in schema.items():
                    type_str = props.get('type', 'Any').replace('integer', 'int').replace('string', 'str')
                    if name in required:
                        params.append(f"{name}: {type_str}")
                    else:
                        params.append(f"{name}: {type_str} = ...")
                    example_args_list.append(f"{name}=...")
                
                example_args_str = ", ".join(example_args_list)

                signature = f"def {tool_name}({', '.join(params)}) -> Any:"
                example_call = f"await mcpc['{self.remote_url}'].call(tool_name='{tool_name}', {example_args_str})"

                doc = f"""{signature}
    \"\"\"{tool.description}

    To call this tool, use the `mcpc` client dictionary like this:
    `result = {example_call}`
    \"\"\""""
                return doc
        return None

    async def call(self, tool_name: str, **params: Any) -> Any:
        """
        Calls a specific tool on the remote server using 'await'.
        If the tool list has not been fetched yet, it will be fetched on the first call.

        :param tool_name: The name of the tool to call.
        :param params: Keyword arguments.
        :return: The result returned from the remote tool execution.
        :raises ValueError: If the tool is not found.
        """
        if not self._tools:
            await self.list_tools()

        if tool_name not in [tool.name for tool in self._tools]:
            raise ValueError(f"Tool '{tool_name}' not found on the server.")

        print(f"Calling tool '{tool_name}' with args: {params}")

        async with self.mcp_client:
            tool_result = await self.mcp_client.call_tool(
                name=tool_name,
                arguments=params
            )
            print(f"[DEBUG] Tool result: {tool_result}")
            return tool_result.data