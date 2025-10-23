// frontend/src/api.ts
import type { ChatResponse } from './types'

// We’ll call relative paths and let Vite proxy to the API container
const BASE = '/api';

export async function login(email: string, password: string) {
  const r = await fetch(`${BASE}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error(`Login failed: ${r.status}`);
  return r.json() as Promise<{ token: string; email: string; role: string }>;
}

export async function chat(token: string, message: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => '');
    throw new Error(`Chat failed: ${r.status} ${text}`);
  }
  return r.json() as Promise<ChatResponse>;
}

export async function health(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/healthz`);
    return r.ok;
  } catch {
    return false;
  }
}

