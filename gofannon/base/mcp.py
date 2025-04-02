from mcp.types import Tool
from mcp.server.lowlevel import Server

class MCPMixin:
    def export_to_mcp(self) -> Tool:
        """Convert Gofannon tool definition to MCP Tool schema"""
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