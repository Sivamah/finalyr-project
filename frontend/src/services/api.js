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
      // Drop cached GETs so a re-login inside the TTL cannot be served the
      // previous session's /auth/profile response.
      getCache.clear();
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
const MAX_CACHE_ENTRIES = 200;
const getCache = new Map();
const originalGet = api.get.bind(api);

// Drop every cached GET. Any mutation invalidates the whole cache: without
// this, a refetch issued right after a POST/PUT/DELETE could be served the
// pre-mutation copy for up to CACHE_TTL ms, so the dashboard would show the
// state from before the action ("the button did nothing").
export const invalidateCache = () => getCache.clear();

// Mutations are rare compared with polling, so blanket invalidation is both
// cheap and much harder to get wrong than per-endpoint keys.
['post', 'put', 'patch', 'delete'].forEach((verb) => {
  const original = api[verb].bind(api);
  api[verb] = async (...args) => {
    try {
      return await original(...args);
    } finally {
      invalidateCache();
    }
  };
});

api.get = async (url, config = {}) => {
  // Opt out with api.get(url, { noCache: true }) when a caller must see
  // server state that may have changed within the TTL.
  const cacheKey = url + JSON.stringify(config.params || {});
  const now = Date.now();

  if (!config.noCache && getCache.has(cacheKey)) {
    const entry = getCache.get(cacheKey);
    // If request is in flight, return its promise (deduplication)
    if (entry.promise) return entry.promise;
    // If we have a fresh response, return it
    if (now - entry.timestamp < CACHE_TTL) {
      return Promise.resolve({
        // Hand back a copy: entry.data used to be shared by reference, so a
        // component sorting or mutating the array in place poisoned the
        // cache for every other consumer within the TTL.
        data: structuredClone(entry.data),
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
      // Bound the map: it is keyed by url+params and was never pruned, so it
      // grew for the lifetime of the tab under continuous polling.
      if (getCache.size > MAX_CACHE_ENTRIES) getCache.clear();
      // Store a copy, so the caller that triggered this request cannot
      // reach the cached object. Cloning only on read is not enough: the
      // first caller receives res.data itself, and sorting that array in
      // place would mutate what every later reader gets.
      getCache.set(cacheKey, { data: structuredClone(res.data), timestamp: Date.now() });
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
