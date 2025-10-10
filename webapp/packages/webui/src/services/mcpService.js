// webapp/packages/webui/src/services/mcpService.js
import config from '../config';

const API_BASE_URL = config.api.baseUrl;

class McpService {
  async listTools(mcpUrl, authToken = null) {
    try {
      const response = await fetch(`${API_BASE_URL}/mcp/tools`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ mcp_url: mcpUrl, auth_token: authToken }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to list tools: Unknown error' }));
        console.error(`[McpService] Error listing tools for ${mcpUrl}:`, errorData);
        throw new Error(errorData.detail || `Failed to list tools for ${mcpUrl}`);
      }

      const data = await response.json();
      return data.tools; // Expecting an array of {name: string, description: string}
    } catch (error) {
      console.error(`[McpService] Network or unexpected error for ${mcpUrl}:`, error);
      throw error;
    }
  }
}

export default new McpService();
