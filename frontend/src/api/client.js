export const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8001";

export function apiUrl(path) {
  return `${API_BASE}${path}`;
}

export function apiFetch(path, init) {
  return fetch(apiUrl(path), init);
}
