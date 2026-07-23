import api from './api';

const schedulerService = {
  createTripsFromBatches: async () => {
    const response = await api.post('/scheduler/trips/create');
    return response.data;
  },

  getAllTrips: async () => {
    const response = await api.get('/scheduler/trips');
    return response.data;
  },

  assignDriver: async (tripId) => {
    const response = await api.post(`/scheduler/trips/${tripId}/assign`);
    return response.data;
  },

  respondToAssignment: async (assignmentId, action) => {
    const response = await api.post(`/scheduler/assignments/${assignmentId}/respond?action=${action}`);
    return response.data;
  },

  getPendingAssignments: async () => {
    const response = await api.get('/scheduler/assignments/pending');
    return response.data;
  },

  getAssignmentHistory: async () => {
    const response = await api.get('/scheduler/history');
    return response.data;
  },

  updateLocation: async (lat, lng) => {
    const response = await api.post('/scheduler/drivers/location', { lat, lng });
    return response.data;
  },

  getAvailableDrivers: async () => {
    const response = await api.get('/scheduler/drivers/availability');
    return response.data;
  }
};

export default schedulerService;
