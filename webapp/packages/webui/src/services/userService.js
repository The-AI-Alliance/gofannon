// webapp/packages/webui/src/services/userService.js
import apiClient from './apiClient';

const userService = {
  getProfile() {
    return apiClient.get('/users/me');
  },

  updateMonthlyAllowance(monthlyAllowance) {
    return apiClient.put('/users/me/monthly-allowance', { monthlyAllowance });
  },

  updateResetDate(allowanceResetDate) {
    return apiClient.put('/users/me/allowance-reset-date', { allowanceResetDate });
  },

  resetAllowance() {
    return apiClient.post('/users/me/reset-allowance');
  },

  updateSpendRemaining(spendRemaining) {
    return apiClient.put('/users/me/spend-remaining', { spendRemaining });
  },

  addUsage(responseCost, metadata = null) {
    return apiClient.post('/users/me/usage', { responseCost, metadata });
  },

  getAllUsers(adminPassword) {
    return apiClient.get('/admin/users', {
      headers: { 'X-Admin-Password': adminPassword },
    });
  },

  updateUser(userId, payload, adminPassword) {
    return apiClient.put(`/admin/users/${userId}`, payload, {
      headers: { 'X-Admin-Password': adminPassword },
    });
  },

  // API Key Management
  getApiKeys() {
    return apiClient.get('/users/me/api-keys');
  },

  updateApiKey(provider, apiKey) {
    return apiClient.put('/users/me/api-keys', { provider, api_key: apiKey });
  },

  deleteApiKey(provider) {
    return apiClient.delete(`/users/me/api-keys/${provider}`);
  },

  getEffectiveApiKey(provider) {
    return apiClient.get(`/users/me/api-keys/${provider}/effective`);
  },
};

export default userService;
