// In dev and Docker, requests go to /api and the dev server or Nginx proxies them.
// On Render the frontend is a separate static site, so VITE_API_URL holds the full
// backend address, e.g. https://pms-backend.onrender.com/api (set at build time).
import { queryClient } from "./queryClient.js";

const BASE = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");

export const auth = {
  get access() { return localStorage.getItem("access"); },
  get refresh() { return localStorage.getItem("refresh"); },
  set(tokens) {
    localStorage.setItem("access", tokens.access);
    if (tokens.refresh) localStorage.setItem("refresh", tokens.refresh);
  },
  clear() { localStorage.removeItem("access"); localStorage.removeItem("refresh"); },
};

async function refreshToken() {
  if (!auth.refresh) return false;
  const r = await fetch(`${BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: auth.refresh }),
  });
  if (!r.ok) return false;
  auth.set(await r.json());
  return true;
}

export async function api(path, { method = "GET", body, retry = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth.access) headers.Authorization = `Bearer ${auth.access}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && retry && (await refreshToken())) {
    return api(path, { method, body, retry: false });
  }
  if (res.status === 401) {
    auth.clear();
    queryClient.clear();
    window.location.hash = "#/login"; // hash routing: no server rewrite needed
    throw new Error("Session expired");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const msg = data && typeof data === "object"
      ? Object.entries(data).map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`).join("; ")
      : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

export async function login(username, password) {
  const res = await fetch(`${BASE}/auth/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Invalid username or password");
  queryClient.clear(); // never show the previous user's cached data to the new one
  auth.set(await res.json());
}

const withParams = (path, params) => {
  const sep = path.includes("?") ? "&" : "?";
  return `${path}${sep}${new URLSearchParams(params).toString()}`;
};

// One page of a DRF list: returns {count, results, next, previous}
export const paged = (path, page = 1, pageSize = 25) =>
  api(withParams(path, { page, page_size: pageSize }));

// Every row of a list (follows all pages). Use for dropdowns and the board,
// not for large tables, which should use paged().
export const list = async (path) => {
  const rows = [];
  let page = 1;
  for (;;) {
    const data = await paged(path, page, 200);
    if (Array.isArray(data)) return data;
    rows.push(...data.results);
    if (!data.next) return rows;
    page += 1;
  }
};

// Multipart upload (the browser sets the boundary header itself)
export async function upload(path, fields, retry = true) {
  const form = new FormData();
  Object.entries(fields).forEach(([k, v]) => form.append(k, v));
  const res = await fetch(`${BASE}${path}`, {
    method: "POST", headers: auth.access ? { Authorization: `Bearer ${auth.access}` } : {}, body: form,
  });
  if (res.status === 401 && retry && (await refreshToken())) return upload(path, fields, false);
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    throw new Error(data && typeof data === "object"
      ? Object.entries(data).map(([k, v]) => `${k}: ${[].concat(v).join(" ")}`).join("; ")
      : `Upload failed (${res.status})`);
  }
  return data;
}

// Files need the login header, so fetch as a blob and save it from memory
export async function download(path, filename, retry = true) {
  const res = await fetch(`${BASE}${path}`, { headers: auth.access ? { Authorization: `Bearer ${auth.access}` } : {} });
  if (res.status === 401 && retry && (await refreshToken())) return download(path, filename, false);
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
