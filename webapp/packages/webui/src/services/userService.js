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
};

export default userService;
