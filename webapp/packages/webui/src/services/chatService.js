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

  async getProviders() {
    const response = await fetch(`${API_BASE_URL}/chat/providers`);
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
      throw new Error('Failed to send message');
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
      const response = await fetch(`${API_BASE_URL}/chat/status/${ticketId}`);
      
      if (!response.ok) {
        throw new Error('Failed to check status');
      }

      const data = await response.json();
      
      if (data.status === 'completed') {
        return data;
      } else if (data.status === 'error') {
        throw new Error(data.error || 'Chat request failed');
      }
      
      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, delay));
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