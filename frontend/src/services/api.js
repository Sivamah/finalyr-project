import axios from 'axios';

export const cleanApiUrl = (rawUrl, isProd = false) => {
  let url = (typeof rawUrl === 'string' ? rawUrl : '').trim();

  // 1. Strip outer double/single quotes
  url = url.replace(/^["']+|["']+$/g, '').trim();

  // 2. Strip accidental variable assignment prefix (e.g. "VITE_API_URL=", "API_URL=")
  url = url.replace(/^(?:VITE_)?(?:REACT_APP_)?API_URL\s*=\s*/i, '').trim();

  // 3. Strip inner quotes if value was entered as VITE_API_URL="https://..."
  url = url.replace(/^["']+|["']+$/g, '').trim();

  // 4. Default if empty
  if (!url) {
    return isProd
      ? 'https://rapid-backend-grmw.onrender.com/api'
      : 'http://localhost:8000/api';
  }

  // 5. Fix accidental single slash after protocol (e.g. "https:/domain.com" -> "https://domain.com")
  url = url.replace(/^(https?):\/+([^\/])/i, '$1://$2');

  // 6. Prepend https:// or http:// if missing protocol entirely
  if (!/^https?:\/\//i.test(url)) {
    if (url.startsWith('localhost') || url.startsWith('127.0.0.1')) {
      url = `http://${url}`;
    } else {
      url = `https://${url}`;
    }
  }

  // 7. Parse and normalize via standard URL object
  try {
    const parsed = new URL(url);
    // In production, never point to localhost
    if (isProd && (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1')) {
      return 'https://rapid-backend-grmw.onrender.com/api';
    }
    let pathname = parsed.pathname.replace(/\/+$/, '');
    if (!pathname.endsWith('/api')) {
      pathname = pathname ? `${pathname}/api` : '/api';
    }
    return `${parsed.origin}${pathname}`;
  } catch {
    url = url.replace(/\/+$/, '');
    if (!url.endsWith('/api')) {
      url = `${url}/api`;
    }
    return url;
  }
};

const getBaseUrl = () => {
  return cleanApiUrl(import.meta.env.VITE_API_URL, import.meta.env.PROD);
};

const api = axios.create({
  baseURL: getBaseUrl(),
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
