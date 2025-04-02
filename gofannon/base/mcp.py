
try:
    from mcp.types import Tool
    from mcp.server.lowlevel import Server

    _HAS_MCP = True
except ImportError:
    _HAS_MCP = False

class MCPMixin:
    def export_to_mcp(self):
        """Convert Gofannon tool definition to MCP Tool schema"""
        if not _HAS_MCP:
            raise RuntimeError(
                "mcp is not installed. Install with `pip install mcp[cli`"
            )
        definition = self.definition['function']
        return Tool(
            name=definition['name'],
            description=definition['description'],
            inputSchema={
                "type": "object",
                "properties": {
                    param: {
                        "type": prop.get('type', 'string'),
                        "description": prop.get('description', '')
                    }
                    for param, prop in definition['parameters']['properties'].items()
                },
                "required": definition['parameters'].get('required', [])
            }
        )

    @classmethod
    def create_mcp_handler(cls, tool_instance):
        async def handler(arguments: dict):
            return await tool_instance.execute_async(arguments)
        return handler