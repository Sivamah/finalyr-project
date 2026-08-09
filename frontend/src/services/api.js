import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401/403 globally — drop stale token
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('access_token');
      // Avoid a full page reload while already on /login: it would wipe the
      // error toast ("Incorrect email or password") and make login look dead.
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// ── Cache & Deduplication for Polling ───────────────────────────────────────
const CACHE_TTL = 2000;
const getCache = new Map();
const originalGet = api.get.bind(api);

api.get = async (url, config = {}) => {
  // Only cache plain GET requests (no special config options that change semantics)
  const cacheKey = url + JSON.stringify(config.params || {});
  const now = Date.now();

  if (getCache.has(cacheKey)) {
    const entry = getCache.get(cacheKey);
    // If request is in flight, return its promise (deduplication)
    if (entry.promise) return entry.promise;
    // If we have a fresh response, return it
    if (now - entry.timestamp < CACHE_TTL) {
      return Promise.resolve({
        data: entry.data,
        status: 200,
        statusText: 'OK (Cached)',
        headers: {},
        config
      });
    }
  }

  // Execute actual request and store the promise
  const reqPromise = originalGet(url, config)
    .then((res) => {
      // Store the resolved data
      getCache.set(cacheKey, { data: res.data, timestamp: Date.now() });
      return res;
    })
    .catch((err) => {
      getCache.delete(cacheKey);
      throw err;
    });

  getCache.set(cacheKey, { promise: reqPromise });
  return reqPromise;
};

export default api;
