import api from './api';

// ── Driver Profile ────────────────────────────
export const getDriverProfile    = ()        => api.get('/drivers/profile');
export const createDriverProfile = (data)    => api.post('/drivers/profile', data);
export const updateDriverProfile = (data)    => api.patch('/drivers/profile', data);
export const toggleAvailability  = ()        => api.patch('/drivers/availability');

// ── Requests Feed ─────────────────────────────
export const getPendingRequests  = ()                       => api.get('/drivers/requests');
export const getActiveBooking    = ()                       => api.get('/drivers/active');
export const getCompletedBookings = (params = {})           => api.get('/drivers/completed', { params });

// ── Status Updates ────────────────────────────
export const acceptRequest       = (type, id)               => api.patch(`/drivers/requests/${type}/${id}/accept`);
export const updateBookingStatus = (type, id, status)       => api.patch(`/drivers/requests/${type}/${id}/status`, { status });
