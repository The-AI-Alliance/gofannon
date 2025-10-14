// webapp/packages/webui/src/services/agentService.js
import config from '../config';
import authService from './authService';

const API_BASE_URL = config.api.baseUrl;

class AgentService {
  async _getAuthHeaders() {
    const user = authService.getCurrentUser();
    // The user object from onAuthStateChanged contains getIdToken
    if (user && typeof user.getIdToken === 'function') {
      try {
        const token = await user.getIdToken();
        return { Authorization: `Bearer ${token}` };
      } catch (error) {
        console.error("Error getting auth token:", error);
        return {};
      }
    }
    return {};
  }

  async generateCode(agentConfig) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/generate-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(agentConfig),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to generate agent code.' }));
        throw new Error(errorData.detail || 'Failed to generate agent code.');
      }

      const data = await response.json();
      return data; // Returns { code: "..." }
    } catch (error) {
      console.error('[AgentService] Error generating code:', error);
      throw error;
    }
  }

  async runCodeInSandbox(code, inputDict, tools) {
    
    const requestBody = {
      code,
      inputDict, // This will be correctly serialized as `inputDict`
      tools,
    };

    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/run-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      if (response.status === 400) { // Specific check for sandbox execution errors
        // The backend returns a 400 with an 'error' key in the JSON body
        throw new Error(data.error || 'Sandbox execution failed with a 400 status.');
      }
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to run code in sandbox.');
      }
      return data; // returns { result: ..., error: ... }
    } catch (error) {
      console.error('[AgentService] Error running code in sandbox:', error);
      throw error;
    }
  }

  async saveAgent(agentData) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify(agentData),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to save the agent.');
      }
      return data; // Returns the saved agent document
    } catch (error) {
      console.error('[AgentService] Error saving agent:', error);
      throw error;
    }
  }

  async getAgents() {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents`, {
        headers: { 
          'Accept': 'application/json',
          ...authHeaders 
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch agents.');
      }
      return await response.json(); // Returns a list of agents
    } catch (error) {
      console.error('[AgentService] Error fetching agents:', error);
      throw error;
    }
  }

  async getAgent(agentId) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
        headers: { 
          'Accept': 'application/json',
          ...authHeaders
        },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch agent ${agentId}.`);
      }
      return await response.json();
    } catch (error) {
      console.error(`[AgentService] Error fetching agent ${agentId}:`, error);
      throw error;
    }
  }
}

export default new AgentService();