const BACKEND_URL = process.env.API_BACKEND_URL || "http://127.0.0.1:8000";

export { BACKEND_URL };

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body) || res.statusText
    );
  }
  return res.json();
}
