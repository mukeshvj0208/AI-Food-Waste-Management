const BASE = import.meta.env.VITE_API_URL || '/api';
async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, options);
  } catch {
    throw new Error(`FoodBridge API is unavailable at ${BASE}. Start the backend on port 8010.`);
  }
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || 'Request failed'); }
  return response.status === 204 ? null : response.json();
}
export const api = {
  dashboard: () => request('/dashboard'), inventory: (params = {}) => request(`/inventory?${new URLSearchParams(params)}`),
  create: (data) => request('/inventory', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) }),
  update: (id,data) => request(`/inventory/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) }),
  remove: (id) => request(`/inventory/${id}`, {method:'DELETE'}), scan: (code) => request(`/inventory/scan/${encodeURIComponent(code)}`),
  expiry: () => request('/expiry'), importCsv: (file) => { const form = new FormData(); form.append('file', file); return request('/inventory/import',{method:'POST',body:form}); }
};
