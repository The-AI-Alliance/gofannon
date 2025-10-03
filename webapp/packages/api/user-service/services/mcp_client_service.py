# webapp/packages/api/user-service/services/mcp_client_service.py
import asyncio
from typing import Any, Dict, List, Optional
from fastmcp import Client
from fastmcp.tools.tool import Tool
from fastmcp.client.auth import BearerAuth
from httpx import Auth, HTTPStatusError
from fastapi import HTTPException

class McpClientService:
    """
    A service for interacting with remote Model Context Protocol (MCP) servers.
    """

    def __init__(self):
        pass

    async def list_tools_for_server(self, remote_url: str, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Connects to a remote MCP server, lists all exposed tools, and returns their details.

        :param remote_url: The URL of the remote MCP server.
        :param auth_token: Optional bearer token for authentication with the MCP server.
        :return: A list of dictionaries, each representing a tool with its name and description.
        :raises: HTTPException if the MCP client fails to connect or list tools.
        """
        print(f"Connecting to MCP server at: {remote_url}...")
        
        # Ensure the URL scheme is http or https
        if not remote_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail=f"Invalid MCP server URL scheme: {remote_url}. Must be http:// or https://")

        auth: Optional[Auth] = BearerAuth(token=auth_token) if auth_token else None
        mcp_client = Client(remote_url, auth=auth)

        try:
            async with mcp_client:
                tools_result: List[Tool] = await mcp_client.list_tools()
                print(f"Found {len(tools_result)} tools from {remote_url}.")
                
                # Extract relevant information from Tool objects
                simplified_tools = [
                    {"name": tool.name, "description": tool.description}
                    for tool in tools_result
                ]
                return simplified_tools
        except HTTPStatusError as e:
            print(f"HTTP error connecting to MCP server {remote_url}: {e}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Failed to connect to MCP server or list tools: {e.response.text}")
        except Exception as e:
            print(f"Error connecting to MCP server {remote_url}: {e}")
            # Re-raise as HTTPException for FastAPI
            raise HTTPException(status_code=500, detail=f"Failed to connect to MCP server or list tools: {str(e)}")

# Singleton instance of the service
mcp_client_service = McpClientService()

def get_mcp_client_service() -> McpClientService:
    return mcp_client_service
