import api from './api';

// ── Ride Bookings ─────────────────────────────
export const createRideBooking  = (data)          => api.post('/bookings/ride', data);
export const listRideBookings   = (params = {})   => api.get('/bookings/ride', { params });
export const getRideBooking     = (id)            => api.get(`/bookings/ride/${id}`);
export const updateRideBooking  = (id, data)      => api.patch(`/bookings/ride/${id}`, data);
export const cancelRideBooking  = (id)            => api.patch(`/bookings/ride/${id}`, { status: 'Cancelled' });

// ── Food Bookings ─────────────────────────────
export const createFoodBooking  = (data)          => api.post('/bookings/food', data);
export const listFoodBookings   = (params = {})   => api.get('/bookings/food', { params });
export const getFoodBooking     = (id)            => api.get(`/bookings/food/${id}`);
export const updateFoodBooking  = (id, data)      => api.patch(`/bookings/food/${id}`, data);
export const cancelFoodBooking  = (id)            => api.patch(`/bookings/food/${id}`, { status: 'Cancelled' });

// ── Parcel Bookings ───────────────────────────
export const createParcelBooking = (data)         => api.post('/bookings/parcel', data);
export const listParcelBookings  = (params = {})  => api.get('/bookings/parcel', { params });
export const getParcelBooking    = (id)           => api.get(`/bookings/parcel/${id}`);
export const updateParcelBooking = (id, data)     => api.patch(`/bookings/parcel/${id}`, data);
export const cancelParcelBooking = (id)           => api.patch(`/bookings/parcel/${id}`, { status: 'Cancelled' });

// ── Unified History ───────────────────────────
export const getBookingHistory   = (params = {})  => api.get('/bookings/history', { params });
