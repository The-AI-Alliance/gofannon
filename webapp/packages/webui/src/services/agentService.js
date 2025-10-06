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
}

export default new AgentService();
