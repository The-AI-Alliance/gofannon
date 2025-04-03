from mcp.server.fastmcp import FastMCP
from gofannon.basic_math.addition import Addition

# Create an MCP server
mcp = FastMCP("Gofannon Demo")

# Add an addition tool
add = Addition()
add.export_to_mcp(mcp)