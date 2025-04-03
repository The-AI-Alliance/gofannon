# MCP Server with Gofannon Tools

If you're reading/interested in this, you're probably running Anthropic's 
Desktop client, which unfortunately will not work with Colab notebooks. However,
we leave this guide here to help you get setup and running on your laptop.

MCP (in the author's opinion) does not have any real world use case beyond 
Anthropic Desktop at this time, but he was compelled by his `$DAYJOB` to 
integrate it anyway, as it is the flavor-of-the-week in the AI hype cycle. If 
you're using Anthropic Desktop, odds on you will need lots of help for local 
usage, if you reach out to us on Discord, we can try to help you.

[Anthropic's Documentation](https://github.com/modelcontextprotocol/python-sdk#quickstart)
may also help. 

The following is an example server.py. You can update it to use any gofannon 
tool, only the Addition tool is included below- but any tool can be added with 
the .export_to_mcp method.

```python
from mcp.server.fastmcp import FastMCP
from gofannon.basic_math.addition import Addition

# Create an MCP server
mcp = FastMCP("Gofannon Demo")

# Add an addition tool
add = Addition()
add.export_to_mcp(mcp)
```

To install for Anthropic Desktop run:

```bash
mcp install server.py
```

For additional information [see Anthropic's Documentation](https://github.com/modelcontextprotocol/python-sdk#quickstart)