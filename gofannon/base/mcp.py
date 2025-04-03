from json import dumps

class MCPMixin:
    def export_to_mcp(self, fast_mcp_server=None):
        """Convert Gofannon tool definition to MCP Tool schema"""
        fast_mcp_server.add_tool(fn=self.fn, name=self.name, description=dumps(self.definition))