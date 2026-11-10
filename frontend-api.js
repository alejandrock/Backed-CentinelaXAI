// Drop this into the React frontend as src/api.js.
// Production assumes Nginx proxies /api/ to the Flask backend.

function getCookie(name) {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${name}=`))
    ?.split('=')[1];
}

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = getCookie('cx_csrf_access');
    if (csrf) headers['X-CSRF-TOKEN'] = decodeURIComponent(csrf);
  }

  const response = await fetch(`/api/v1${path}`, {
    credentials: 'include',
    ...options,
    method,
    headers,
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.message || `HTTP ${response.status}`);
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

export const api = {
  login: (email, password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),
  users: () => request('/users'),
  roles: () => request('/roles'),
  permissions: () => request('/permissions'),
  auditLogs: (params = '') => request(`/audit-logs${params ? `?${params}` : ''}`),
};
