import config from '../config';

const API_BASE_URL = config.api.baseUrl;

class ChatService {
  constructor() {
    this.sessionId = this.getOrCreateSessionId();
  }

  getOrCreateSessionId() {
    let sessionId = sessionStorage.getItem('chat_session_id');
    if (!sessionId) {
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  }

  async createSession() {
    // The component expects an object with a session_id key.
    this.sessionId = this.getOrCreateSessionId();
    return { session_id: this.sessionId };
  }

  async getProviders() {
    const response = await fetch(`${API_BASE_URL}/providers`);
    if (!response.ok) {
      throw new Error('Failed to fetch providers');
    }
    return response.json();
  }

  async sendMessage(message, settings) {
    const response = await fetch(`${API_BASE_URL}/chat/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: this.sessionId,
        message,
        provider: settings.provider,
        model: settings.model,
        config: settings.config,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to send message' }));
      throw new Error(errorData.detail || 'Failed to send message');
    }

    const data = await response.json();
    
    // If we got a ticket, poll for the result
    if (data.ticket_id) {
      return this.pollForResult(data.ticket_id);
    }
    
    return data;
  }

  async pollForResult(ticketId, maxAttempts = 60, delay = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, delay));
      
      const response = await fetch(`${API_BASE_URL}/chat/status/${ticketId}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to check status' }));
        throw new Error(errorData.detail || 'Failed to check status');
      }

      const data = await response.json();
      
      if (data.status === 'completed') {
        return data.result;
      } else if (data.status === 'failed') {
        throw new Error(data.result.error || 'Chat request failed');
      }
    }
    
    throw new Error('Request timeout');
  }

  async getHistory() {
    const response = await fetch(`${API_BASE_URL}/chat/history/${this.sessionId}`);
    if (!response.ok) {
      throw new Error('Failed to fetch history');
    }
    return response.json();
  }

  clearSession() {
    sessionStorage.removeItem('chat_session_id');
    this.sessionId = this.getOrCreateSessionId();
  }
}

export default new ChatService();