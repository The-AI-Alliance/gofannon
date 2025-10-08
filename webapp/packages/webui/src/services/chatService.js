import config from '../config';

const API_BASE_URL = config.api.baseUrl;

class ChatService {
  constructor() {
    this.sessionId = this.getOrCreateSessionId();
  }

  getOrCreateSessionId() {
    let sessionId = sessionStorage.getItem('chat_session_id');
    console.log("Retrieved chat session_id from sessionStorage:", sessionId);
    if (!sessionId) {
      console.log("No existing chat session_id found. Generating new one.");
      sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('chat_session_id', sessionId);
    }
    return sessionId;
  }

  async createSession() {
    // The backend's /chat endpoint does not currently use session_id directly in the request body.
    // However, the frontend ChatPage.jsx calls this to get a session_id.
    // For now, we return the locally generated session_id.
    // If backend session persistence is desired for /chat, the backend route needs to be updated.
    this.sessionId = this.getOrCreateSessionId();
    console.log("Using chat sessionId:", this.sessionId);
    return { sessionId: this.sessionId };
  }

  async getProviders() {
    console.log("Fetching providers from ", `${API_BASE_URL}/providers`);
    const response = await fetch(`${API_BASE_URL}/providers`, { headers: { 'Accept': 'application/json' } });
    
    if (!response.ok) {
        throw new Error('Failed to fetch providers');
    }
    
    const data = await response.json();
    console.log("Fetched providers: ", data);
    return data;
  }

  // Changed `message` to `messages` (plural) and renamed `settings.config` to `parameters`
  async sendMessage(messages, chatSettings) { // messages is List<ChatMessage>, chatSettings contains provider, model, config
    console.log("Sending message with settings:", chatSettings);
    console.log("Messages being sent:", messages);

    const requestBody = {
      messages: messages, // This should be the array of {role, content}
      provider: chatSettings.provider,
      model: chatSettings.model,
      parameters: chatSettings.config, // Renamed from 'config' to 'parameters' to match backend
      stream: false // Explicitly set to false to match backend's default and current handling
    };

    // Corrected endpoint from /chat/send to /chat
    const response = await fetch(`${API_BASE_URL}/chat`, { 
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
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
    
    // If we got a ticket, poll for the result
    if (data.ticket_id) {
      return this.pollForResult(data.ticket_id);
    }
    
    return data;
  }

  async pollForResult(ticketId, maxAttempts = 60, delay = 1000) {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(resolve => setTimeout(resolve, delay));
      
      // Corrected endpoint from /chat/status/{ticketId} to /chat/{ticketId}
      const response = await fetch(`${API_BASE_URL}/chat/${ticketId}`); 
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to check status' }));
        throw new Error(errorData.detail || 'Failed to check status');
      }

      const data = await response.json();
      console.log(`Polling status for ${ticketId}:`, data.status);
      
      if (data.status === 'completed') {
        return data.result;
      } else if (data.status === 'failed') {
        // Use data.error as backend returns 'error' key
        throw new Error(data.error || 'Chat request failed'); 
      }
    }
    
    throw new Error('Request timeout');
  }

  async getHistory() {
    // This endpoint `/chat/history/${this.sessionId}` is not defined in `main.py`
    // The current backend session management is for config, not chat history.
    // If history is needed, a new backend endpoint and storage would be required.
    console.warn("getHistory called but not implemented on backend for sessions. Returning empty array.");
    return []; 
  }

  clearSession() {
    sessionStorage.removeItem('chat_session_id');
    this.sessionId = this.getOrCreateSessionId();
    console.log("Chat session cleared.");
  }
}

export default new ChatService();
