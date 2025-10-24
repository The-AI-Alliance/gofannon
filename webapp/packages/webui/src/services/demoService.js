// webapp/packages/webui/src/services/demoService.js
import apiClient from './apiClient';

const demoService = {
  generateDemoAppCode: (request) => {
    return apiClient.post('/demos/generate-code', request);
  },

  getDemos: () => {
    return apiClient.get('/demos');
  },

  getDemo: (id) => {
    return apiClient.get(`/demos/${id}`);
  },

  saveDemo: (data) => {
    return apiClient.post('/demos', data);
  },

  updateDemo: (id, data) => {
    return apiClient.put(`/demos/${id}`, data);
  },

  deleteDemo: (id) => {
    return apiClient.delete(`/demos/${id}`);
  },
};

export default demoService;