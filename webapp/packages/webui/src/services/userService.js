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
};

export default userService;
