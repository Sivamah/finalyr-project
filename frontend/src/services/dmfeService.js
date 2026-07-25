import api from './api';

export const dmfeService = {
  triggerOptimization: async () => {
    const response = await api.post('/dmfe/evaluate');
    return response.data;
  },
  
  getBatches: async () => {
    const response = await api.get('/dmfe/batches');
    return response.data;
  },
  
  acceptBatch: async (batchId) => {
    const response = await api.patch(`/dmfe/batches/${batchId}/accept`);
    return response.data;
  },
  
  updateBatchStatus: async (batchId, status) => {
    const response = await api.patch(`/dmfe/batches/${batchId}/status`, { status });
    return response.data;
  }
};
