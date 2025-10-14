// webapp/packages/webui/src/services/apiClient.js
import authService from './authService';
import config from '../config';

const API_BASE_URL = config.api.baseUrl;

const getAuthHeader = async () => {
  const user = authService.getCurrentUser();
  if (!user || typeof user.getIdToken !== 'function') {
    return {};
  }
  try {
    const token = await user.getIdToken();
    return { Authorization: `Bearer ${token}` };
  } catch (error) {
    console.error("Error getting auth token:", error);
    return {};
  }
};

const apiClient = {
  async request(endpoint, options = {}) {
    const authHeader = await getAuthHeader();
    
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...authHeader,
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => ({})); // Gracefully handle empty responses

    if (!response.ok) {
      const errorMessage = data.detail || data.error || `Request failed with status ${response.status}`;
      console.error(`API Error on ${endpoint}:`, errorMessage);
      throw new Error(errorMessage);
    }

    return data;
  },

  get(endpoint, options) {
    return this.request(endpoint, { ...options, method: 'GET' });
  },

  post(endpoint, body, options) {
    return this.request(endpoint, { ...options, method: 'POST', body: JSON.stringify(body) });
  },
  
  delete(endpoint, options) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
};

export default apiClient;