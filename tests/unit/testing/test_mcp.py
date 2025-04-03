import pytest
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def invoke(cmd_or_url: str, method: str, data: dict) -> dict:
    # STDIO transport
    command, args = cmd_or_url.split(" ", 1)
    server_params = StdioServerParameters(
        command=command,
        args=args.split(" "),
    )
    client = stdio_client(server_params)

    params = data if data else {}

    async with client as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            match method:
                case "prompts/list":
                    result = await session.list_prompts()

                case "prompts/get":
                    result = await session.get_prompt(**params)

                case "resources/list":
                    result = await session.list_resources()

                case "resources/read":
                    result = await session.read_resource(**params)

                case "tools/list":
                    result = await session.list_tools()

                case "tools/call":
                    result = await session.call_tool(**params)

                case _:
                    raise ValueError(f"Unknown method: {method}")

            return result

def test_tool_list():
    cmd = "mcp run gofannon_server.py"
    method = "tools/list"
    data = {}
    result = asyncio.run(invoke(cmd, method, data))
    assert any(t.name == "addition" for t in result['tools'])

def test_fn():
    cmd = "mcp run gofannon_server.py"
    method = "tools/call"
    data = {"name": "addition", "arguments": {"num1": 1, "num2": 2}}
    result = asyncio.run(invoke(cmd, method, data))
    assert result['content']['text'] == "3"