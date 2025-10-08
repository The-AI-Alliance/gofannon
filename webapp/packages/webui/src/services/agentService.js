import config from '../config';

const API_BASE_URL = config.api.baseUrl;

class AgentService {
  async generateCode(agentConfig) {
    console.log('[AgentService] Generating code with config:', agentConfig);
    console.log('[AgentService] :', JSON.stringify(agentConfig))
    try {
      const response = await fetch(`${API_BASE_URL}/agents/generate-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
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
    console.log('[AgentService] Running code in sandbox with input:', inputDict);
    const requestBody = {
      code,
      inputDict, // This will be correctly serialized as `inputDict`
      tools,
    };

    try {
      const response = await fetch(`${API_BASE_URL}/agents/run-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Failed to run code in sandbox.');
      }
      return data; // returns { result: ..., error: ... }
    } catch (error) {
      console.error('[AgentService] Error running code in sandbox:', error);
      throw error;
    }
  }
}

export default new AgentService();
