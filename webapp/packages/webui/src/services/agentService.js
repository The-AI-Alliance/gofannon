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

  async fetchSpecFromUrl(url) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/specs/fetch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...authHeaders,
        },
        body: JSON.stringify({ url }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch spec from URL.');
      }
      return data; // returns { name: string, content: string }
    } catch (error) {
      console.error('[AgentService] Error fetching spec from URL:', error);
      throw error;
    }
  }
  async runCodeInSandbox(code, inputDict, tools, gofannonAgents, llmSettings, outputSchema, friendlyName) {
    
    const requestBody = {
      code,
      inputDict,
      tools,
      gofannonAgents: (gofannonAgents || []).map(agent => agent.id),
      llmSettings,
      outputSchema,
      friendlyName,
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
      if (response.status === 400) { // Specific check for agent execution errors
        // The backend returns a 400 with an 'error' key in the JSON body
        throw new Error(data.error || 'Agent execution failed with a 400 status.');
      }
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to run agent code.');
      }
      return data; // returns { result: ..., error: ... }
    } catch (error) {
      console.error('[AgentService] Error running agent code:', error);
      throw error;
    }
  }

  /**
   * Streaming variant of runCodeInSandbox. Opens an SSE-over-fetch
   * connection to /agents/run-code/stream and dispatches each trace
   * event to onEvent as it arrives. Resolves to {outcome, result,
   * error, schemaWarnings, opsLog} when the server sends the 'done'
   * frame.
   *
   * Why fetch + ReadableStream instead of EventSource: EventSource is
   * GET-only and doesn't support custom headers. We need POST with
   * the agent payload, so we parse SSE frames from a streaming
   * response body manually.
   */
  async runCodeInSandboxStreaming(
    code, inputDict, tools, gofannonAgents, llmSettings, outputSchema, friendlyName,
    onEvent,
  ) {
    const requestBody = {
      code,
      inputDict,
      tools,
      gofannonAgents: (gofannonAgents || []).map((agent) => agent.id),
      llmSettings,
      outputSchema,
      friendlyName,
    };

    const authHeaders = await this._getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/agents/run-code/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...authHeaders,
      },
      body: JSON.stringify(requestBody),
      // Cookies must flow for session auth.
      credentials: 'include',
    });

    if (!response.ok) {
      // Pre-stream errors (auth, validation): bail with a normal
      // error so the caller can show a transport-level message.
      let detail;
      try {
        const data = await response.json();
        detail = data.detail || data.error;
      } catch {
        detail = response.statusText;
      }
      throw new Error(detail || `Stream request failed (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let final = null;

    // Parse SSE frames. Each frame is a block of lines separated
    // from the next by a blank line. Within a frame: 'event: NAME'
    // and 'data: JSON' (one of each, possibly across multiple
    // 'data:' lines that are concatenated with newlines).
    const parseFrame = (raw) => {
      const lines = raw.split('\n');
      let event = 'message';
      const dataParts = [];
      for (const line of lines) {
        if (line.startsWith(':')) continue; // comment / heartbeat
        if (line.startsWith('event:')) {
          event = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataParts.push(line.slice(5).trimStart());
        }
      }
      if (!dataParts.length) return null;
      let data;
      try {
        data = JSON.parse(dataParts.join('\n'));
      } catch {
        return null;
      }
      return { event, data };
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Split on the blank-line frame boundary. Anything after the
      // last \n\n stays in the buffer for the next chunk.
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const frame = parseFrame(raw);
        if (!frame) continue;
        if (frame.event === 'trace') {
          try {
            onEvent && onEvent(frame.data);
          } catch (err) {
            console.error('[AgentService] onEvent handler threw:', err);
          }
        } else if (frame.event === 'done') {
          final = frame.data;
        }
      }

      if (final) break;
    }

    if (!final) {
      // Stream ended without a 'done' frame — likely the server
      // dropped the connection. Treat as an error so the caller
      // doesn't silently end up with no outcome.
      throw new Error('Stream ended without a done frame.');
    }

    return final;
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

  async getChain(agentId) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}/chain`, {
        headers: {
          'Accept': 'application/json',
          ...authHeaders,
        },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch chain for agent ${agentId}.`);
      }
      return await response.json(); // { root, nodes, edges }
    } catch (error) {
      console.error(`[AgentService] Error fetching chain for ${agentId}:`, error);
      throw error;
    }
  }

  async updateAgent(agentId, agentData) {
    try {
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/agents/${agentId}`, {
        method: 'PUT', // Or PATCH if the backend supports partial updates
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...authHeaders,
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