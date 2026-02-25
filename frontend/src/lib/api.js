const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function toQuery(params) {
  if (!params) return '';
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

export async function apiRequest(method, path, options = {}) {
  const url = `${API_BASE_URL}${path}${toQuery(options.params)}`;
  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    credentials: 'include',
  });

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const detail = typeof payload === 'string' ? payload : payload?.detail || 'Request failed';
    return { ok: false, status: response.status, error: detail, data: payload };
  }

  return { ok: true, status: response.status, data: payload };
}
