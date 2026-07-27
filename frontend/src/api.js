const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listReasonCodes: () => request("/api/disputes/reason-codes"),
  listDisputes: () => request("/api/disputes"),
  getDispute: (id) => request(`/api/disputes/${id}`),
  fileDispute: (payload) =>
    request("/api/disputes", { method: "POST", body: JSON.stringify(payload) }),
  appealDispute: (id) => request(`/api/disputes/${id}/appeal`, { method: "POST" }),
};
