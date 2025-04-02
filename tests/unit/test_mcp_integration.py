# tests/test_mcp_integration.py
import pytest
import anyio
from mcp.client.session import ClientSession
from mcp.types import Tool
from gofannon.base import BaseTool
from gofannon.config import FunctionRegistry
from mcp.server.lowlevel import Server

# Simple test tool implementation
@FunctionRegistry.register
class TestTool(BaseTool):
    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": "test_tool",
                "description": "Test tool that doubles numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "number", "description": "Number to double"}
                    },
                    "required": ["number"]
                }
            }
        }

    def fn(self, number: float) -> float:
        return number * 2

@pytest.fixture
async def mcp_server():
    # Create in-memory communication channels
    client_send, server_receive = anyio.create_memory_object_stream()
    server_send, client_receive = anyio.create_memory_object_stream()

    # Configure MCP server
    server = Server("test-server")
    test_tool = TestTool()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [test_tool.export_to_mcp()]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> float:
        if name != "test_tool":
            raise ValueError("Unknown tool")
        return await test_tool.execute_async(arguments)

        # Start server in background
    async def run_server():
        async with server_receive, server_send:
            await server.run(server_receive, server_send)

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        yield (client_receive, client_send)
        tg.cancel_scope.cancel()

@pytest.mark.anyio
async def test_mcp_tool_execution(mcp_server):
    client_receive, client_send = mcp_server

    async with ClientSession(client_receive, client_send) as session:
        # Initialize connection
        await session.initialize()

        # Test tool listing
        tools = await session.list_tools()
        tool_names = [t.name for t in tools]
        assert "test_tool" in tool_names

        # Test tool execution
        result = await session.call_tool("test_tool", {"number": 5})
        assert result == 10

        # Test error handling
        with pytest.raises(ValueError):
            await session.call_tool("invalid_tool", {})  