# Updated test with proper MCP response handling
import pytest
import anyio
from anyio import fail_after
from mcp.client.session import ClientSession
from mcp.types import Tool, TextContent
from gofannon.base import BaseTool
from gofannon.config import FunctionRegistry
from mcp.server.lowlevel import Server

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
    client_send, server_receive = anyio.create_memory_object_stream()
    server_send, client_receive = anyio.create_memory_object_stream()

    server = Server("test-server")
    test_tool = TestTool()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [test_tool.export_to_mcp()]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name != "test_tool":
                raise ValueError(f"Unknown tool: {name}")
            result = await test_tool.execute_async(arguments)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def run_server():
        async with server_receive, server_send:
            await server.run(server_receive, server_send)

    async with anyio.create_task_group() as tg:
        tg.start_soon(run_server)
        yield (client_receive, client_send)
        tg.cancel_scope.cancel()

@pytest.mark.anyio
async def test_mcp_tool_execution(mcp_server):
    print('cp1')
    client_receive, client_send = mcp_server
    print('cp2')
    async with ClientSession(client_receive, client_send) as session:
        print('cp3')
        with fail_after(1):
            await session.initialize()
        print('cp4')
            # Test tool listing
        with fail_after(1):
            tools = await session.list_tools()
            tool_names = [t.name for t in tools]
            assert "test_tool" in tool_names
        print('cp5')
            # Test valid execution
        with fail_after(1):
            results = await session.call_tool("test_tool", {"number": 5})
            assert len(results) == 1
            assert isinstance(results[0], TextContent)
            assert float(results[0].text) == 10.0
        print('cp6')
            # Test invalid tool
        with fail_after(1), pytest.raises(ValueError) as exc_info:
            await session.call_tool("invalid_tool", {})

        assert "Unknown tool: invalid_tool" in str(exc_info.value)