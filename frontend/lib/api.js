// frontend/lib/api.js
const BASE = process.env.NEXT_PUBLIC_API_BASE;

export async function apiGet(path) {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

export async function apiUpload(path, filesObj) {
  const fd = new FormData();
  Object.entries(filesObj).forEach(([k, v]) => v && fd.append(k, v));
  const r = await fetch(`${BASE}${path}`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}
