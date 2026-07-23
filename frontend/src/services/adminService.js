import api from './api';

// ── Users ─────────────────────────────────────
export const listUsers    = (params = {})          => api.get('/admin/users', { params });
export const getUser      = (id)                   => api.get(`/admin/users/${id}`);
export const changeRole   = (id, role)             => api.patch(`/admin/users/${id}/role`, { role });

// ── Bookings ──────────────────────────────────
export const listAllBookings   = (params = {})     => api.get('/admin/bookings', { params });
export const forceBookingStatus = (type, id, status) => api.patch(`/admin/bookings/${type}/${id}/status`, { status });

// ── Stats ─────────────────────────────────────
export const getStats     = ()                     => api.get('/admin/stats');
