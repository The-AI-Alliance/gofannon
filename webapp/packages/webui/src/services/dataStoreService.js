// webapp/packages/webui/src/services/dataStoreService.js
//
// API client for the Data Store viewer. Mirrors the shape of agentService.js
// — same auth header handling, same base URL, same error-surfacing pattern.

import config from '../config';
import authService from './authService';

const API_BASE_URL = config.api.baseUrl;

class DataStoreService {
  async _getAuthHeaders() {
    const user = authService.getCurrentUser();
    if (user && typeof user.getIdToken === 'function') {
      try {
        const token = await user.getIdToken();
        return { Authorization: `Bearer ${token}` };
      } catch (error) {
        console.error('[DataStoreService] Error getting auth token:', error);
        return {};
      }
    }
    return {};
  }

  async _request(path, options = {}) {
    const authHeaders = await this._getAuthHeaders();
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...authHeaders,
        ...(options.headers || {}),
      },
    });
    if (response.status === 204) return null;
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(err.detail || `Request failed: ${response.status}`);
    }
    return response.json();
  }

  // Namespace-level operations

  async listNamespaces() {
    return this._request('/data-store/namespaces');
  }

  async getNamespaceStats(namespace) {
    return this._request(`/data-store/namespaces/${encodeURIComponent(namespace)}`);
  }

  async clearNamespace(namespace) {
    return this._request(
      `/data-store/namespaces/${encodeURIComponent(namespace)}`,
      { method: 'DELETE' }
    );
  }

  // Record-level operations

  async listRecords(namespace) {
    return this._request(
      `/data-store/namespaces/${encodeURIComponent(namespace)}/records`
    );
  }

  async getRecord(namespace, key) {
    return this._request(
      `/data-store/namespaces/${encodeURIComponent(namespace)}/records/${encodeURIComponent(key)}`
    );
  }

  async setRecord(namespace, key, value, metadata) {
    return this._request(
      `/data-store/namespaces/${encodeURIComponent(namespace)}/records/${encodeURIComponent(key)}`,
      {
        method: 'PUT',
        body: JSON.stringify({ value, metadata }),
      }
    );
  }

  async deleteRecord(namespace, key) {
    return this._request(
      `/data-store/namespaces/${encodeURIComponent(namespace)}/records/${encodeURIComponent(key)}`,
      { method: 'DELETE' }
    );
  }
}

const dataStoreService = new DataStoreService();
export default dataStoreService;
