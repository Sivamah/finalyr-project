import api from './api';

const routingService = {
  optimizeRoute: async (tripId) => {
    const response = await api.post(`/routing/optimize/${tripId}`);
    return response.data;
  },

  getRouteDetails: async (tripId) => {
    const response = await api.get(`/routing/${tripId}`);
    return response.data;
  }
};

export default routingService;
