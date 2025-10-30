// webapp/packages/webui/src/services/chatService.js
import config from '../config';
import authService from './authService';

const API_BASE_URL = config.api.baseUrl;

class ChatService {
  constructor() {
    this.sessionId = this.getOrCreateSessionId();
  }

  async _getAuthHeaders() {
    const user = authService.getCurrentUser();
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

  getOrCreateSessionId() {
    let sessionId = sessionStorage.getItem('chat_session_id');
    
    if (!sessionId) {
      console.log("No existing chat session_id found. Generating new one.");
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  }

  async createSession() {
    this.sessionId = this.getOrCreateSessionId();
    console.log("Using chat sessionId:", this.sessionId);
    return { sessionId: this.sessionId };
  }

  async getProviders() {
    
    const authHeaders = await this._getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/providers`, { 
      headers: { 
        'Accept': 'application/json',
        ...authHeaders 
      } 
    });
    
    if (!response.ok) {
        throw new Error('Failed to fetch providers');
    }
    
    const data = await response.json();
    
    return data;
  }

  async sendMessage(messages, chatSettings) {
    console.log("Sending message with settings:", chatSettings);
    console.log("Messages being sent:", messages);

    const requestBody = {
      messages: messages,
      provider: chatSettings.provider,
      model: chatSettings.model,
      parameters: chatSettings.parameters,
      stream: false,
    };
    
    if (chatSettings.builtInTool) {
      // The backend expects an array of tool IDs.
      requestBody.builtInTools = [chatSettings.builtInTool];
    }

    const authHeaders = await this._getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}/chat`, { 
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to send message' }));
      console.error("Backend error response:", errorData);
      throw new Error(errorData.detail || 'Failed to send message');
    }

    const data = await response.json();
    console.log("Initial chat response (ticket_id):", data);
    
    if (data.ticket_id) {
      return this.pollForResult(data.ticket_id);
    }
    
    return data;
  }

  async pollForResult(ticketId, maxAttempts = 60, delay = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, delay));
      
      const authHeaders = await this._getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/chat/${ticketId}`, {
        headers: { ...authHeaders }
      }); 
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to check status' }));
        throw new Error(errorData.detail || 'Failed to check status');
      }

      const data = await response.json();
      console.log(`Polling status for ${ticketId}:`, data.status);
      
      if (data.status === 'completed') {
        return data.result;
      } else if (data.status === 'failed') {
        throw new Error(data.error || 'Chat request failed'); 
      }
    }
    
    throw new Error('Request timeout');
  }

  async getHistory() {
    console.warn("getHistory called but not implemented on backend for sessions. Returning empty array.");
    return []; 
  }

  clearSession() {
    sessionStorage.removeItem('chat_session_id');
    this.sessionId = this.getOrCreateSessionId();
  }
}

export default new ChatService();