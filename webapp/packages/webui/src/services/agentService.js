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

  async runCodeInSandbox(code, inputDict, tools, gofannonAgents) {
    
    const requestBody = {
      code,
      inputDict,
      tools,
      gofannonAgents: (gofannonAgents || []).map(agent => agent.id),
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

  async updateAgent(agentId, agentData) {
    try {
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
        method: 'PUT', // Or PATCH if the backend supports partial updates
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(agentData),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to update the agent.');
      }
      return data;
    } catch (error) {
      console.error(`[AgentService] Error updating agent ${agentId}:`, error);
      throw error;
    }
  }

  async deleteAgent(agentId) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
        method: 'DELETE',
        headers: {
          ...authHeaders,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `Failed to delete agent ${agentId}. Status: ${response.status}` }));
        throw new Error(errorData.detail);
      }
      // A successful DELETE (204 No Content) will not have a body to return.
      return;
    } catch (error) {
      console.error(`[AgentService] Error deleting agent ${agentId}:`, error);
      throw error;
    }
  }    
  
  async getDeployments() {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/deployments`, {
        headers: { 
          'Accept': 'application/json',
          ...authHeaders 
        },
      });
      if (!response.ok) {
        throw new Error('Failed to fetch deployments.');
      }
      return await response.json(); // Returns a list of deployed APIs
    } catch (error) {
      console.error('[AgentService] Error fetching deployments:', error);
      throw error;
    }
  } 

  async deployAgent(agentId) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}/deploy`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...authHeaders,
        },
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to deploy agent.');
      }
      return data;
    } catch (error) {
      console.error(`[AgentService] Error deploying agent ${agentId}:`, error);
      throw error;
    }
  }

  async undeployAgent(agentId) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}/undeploy`, {
        method: 'DELETE',
        headers: {
          ...authHeaders,
        },
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `Failed to undeploy agent ${agentId}.` }));
        throw new Error(errorData.detail);
      }
      return; // 204 No Content on success
    } catch (error) {
      console.error(`[AgentService] Error undeploying agent ${agentId}:`, error);
      throw error;
    }
  }

  async getDeployment(agentId) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}/deployment`, {
        headers: { ...authHeaders },
      });
      if (!response.ok) {
        throw new Error('Failed to get deployment status.');
      }
      return await response.json(); // { is_deployed: boolean, friendly_name?: string }
    } catch (error) {
      console.error(`[AgentService] Error getting deployment status for ${agentId}:`, error);
      throw error;
    }
  }  
}

export default new AgentService();