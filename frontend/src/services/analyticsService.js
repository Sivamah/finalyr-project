import api from './api';

export const getSummary = async () => {
  const response = await api.get('/analytics/summary');
  return response.data;
};

export const getTripAnalytics = async () => {
  const response = await api.get('/analytics/trips');
  return response.data;
};

export const getDriverAnalytics = async () => {
  const response = await api.get('/analytics/drivers');
  return response.data;
};

export const exportReport = async (type, report) => {
  const response = await api.get(`/analytics/export?type=${type}&report=${report}`, {
    responseType: 'blob', // Important for file downloads
  });
  
  // Create a link to download the file
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `${report}_export.${type}`);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

// ── Phase 8: AI Decision & DMFE Analytics ──

export const getDmfeAnalytics = async () => {
  const response = await api.get('/analytics/dmfe');
  return response.data;
};

export const getAIDecisions = async (skip = 0, limit = 50) => {
  const response = await api.get(`/dmfe/decisions?skip=${skip}&limit=${limit}`);
  return response.data;
};

export const getAIDecision = async (id) => {
  const response = await api.get(`/dmfe/decisions/${id}`);
  return response.data;
};

