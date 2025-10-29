// frontend/src/api.ts
// One API base that works in Docker & Codespaces.
// - If VITE_BACKEND_URL is set (Docker or Codespaces), we call it directly.
// - Otherwise we fall back to "/api" and let Vite's dev proxy forward requests in local dev.

const BASE =
  (import.meta.env.VITE_BACKEND_URL as string | undefined)?.replace(/\/+$/, '') || '/api';

async function asJsonOrText(r: Response) {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  const ct = r.headers.get('content-type') || '';
  return ct.includes('application/json') ? r.json() : r.text();
}

export async function healthz() {
  const r = await fetch(`${BASE}/healthz`, { credentials: 'omit' });
  return asJsonOrText(r);
}

export async function login(email: string, password: string) {
  const r = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'omit',
    body: JSON.stringify({ email, password }),
  });
  return asJsonOrText(r);
}

export async function chat(token: string, message: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });
  return asJsonOrText(r);
}

// Optional: use the agent endpoint if your UI prefers one path.
// Safe to keep both and choose in the component.
export async function agentChat(token: string, message: string) {
  const r = await fetch(`${BASE}/agent/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });
  return asJsonOrText(r);
}

// New: Function calling agent with reasoning transparency
export async function agentChatV2(
  token: string,
  message: string,
  convo_id?: string
) {
  const r = await fetch(`${BASE}/agent/chat/v2`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, convo_id }),
  });
  return asJsonOrText(r);
}

// Optional helper for the logs table screen (if used by UI)
export async function queryLogs(token: string, params: { date?: string; username?: string; limit?: number }) {
  const r = await fetch(`${BASE}/logs/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(params || {}),
  });
  return asJsonOrText(r);
}

