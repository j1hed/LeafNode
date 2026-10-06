export type ApiRecord = Record<string, unknown>;
export type Latest = { status: string; timestamp?: string; esp32: ApiRecord | null; jetson: ApiRecord | null };
export type History = { count: number; data: unknown[] };
export type Commands = { count: number; commands: unknown[] };
export type Session = ApiRecord & { id: string | number; recommendation_json?: unknown };
export type AuthUser = { id: number; username: string; created_at: number };
export type LoginResponse = { access_token: string; token_type: string; expires_in: number; user: AuthUser };

export const API_BASE = (import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
let accessToken: string | null = null;
const authListeners = new Set<() => void>();

export function getAccessToken() { return accessToken; }
export function onAuthChange(listener: () => void) {
  authListeners.add(listener);
  return () => { authListeners.delete(listener); };
}
export function clearAccessToken() {
  if (!accessToken) return;
  accessToken = null;
  authListeners.forEach(listener => listener());
}
function setAccessToken(token: string) {
  accessToken = token;
  authListeners.forEach(listener => listener());
}

export class ApiError extends Error {
  constructor(message: string, public status?: number) { super(message); this.name = 'ApiError'; }
}
export const isRecord = (value: unknown): value is ApiRecord => typeof value === 'object' && value !== null && !Array.isArray(value);
export function record(value: unknown): ApiRecord {
  if (!isRecord(value)) throw new ApiError('The API returned an unexpected response.');
  return value;
}
export function session(value: unknown): Session {
  const result = record(value);
  if ((typeof result.id !== 'string' || !result.id.trim()) && (typeof result.id !== 'number' || !Number.isFinite(result.id))) {
    throw new ApiError('The session response is missing a valid id.');
  }
  return result as Session;
}

export async function request<T = unknown>(path: string, options: { signal?: AbortSignal; body?: unknown; method?: string } = {}): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener('abort', abort, { once: true });
  if (options.signal?.aborted) controller.abort();
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, 12000);
  try {
    const response = await fetch(API_BASE + path, {
      method: options.method || 'GET',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
    });
    const raw = await response.text();
    let data: unknown;
    try { data = raw ? JSON.parse(raw) : null; } catch {
      if (response.ok) throw new ApiError('The API returned invalid JSON.', response.status);
    }
    if (!response.ok) {
      if (response.status === 401) clearAccessToken();
      const detail = isRecord(data) ? data.detail ?? data.message : undefined;
      throw new ApiError(`HTTP ${response.status}${detail ? ': ' + (typeof detail === 'string' ? detail : JSON.stringify(detail)) : ' ' + response.statusText}`, response.status);
    }
    return data as T;
  } catch (error) {
    if (options.signal?.aborted) throw error;
    if (error instanceof ApiError) throw error;
    throw new ApiError(timedOut ? 'The backend request timed out.' : 'Cannot connect to the LeafNode backend. Check its URL, service, and CORS configuration.');
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener('abort', abort);
  }
}
const post = (path: string, signal?: AbortSignal, body?: unknown) => request(path, { method: 'POST', body, signal });
function authUser(value: unknown): AuthUser {
  const result = record(value);
  if (typeof result.id !== 'number' || typeof result.username !== 'string' || typeof result.created_at !== 'number') {
    throw new ApiError('The API returned an invalid user profile.');
  }
  return result as AuthUser;
}
export const api = {
  register: async (body: { username: string; password: string }) => {
    await post('/api/auth/register', undefined, body);
  },
  login: async (body: { username: string; password: string }): Promise<LoginResponse> => {
    const value = record(await post('/api/auth/login', undefined, body));
    if (typeof value.access_token !== 'string' || value.token_type !== 'bearer' || typeof value.expires_in !== 'number') {
      throw new ApiError('The API returned an invalid login response.');
    }
    const result = { ...value, user: authUser(value.user) } as LoginResponse;
    setAccessToken(result.access_token);
    return result;
  },
  me: async (): Promise<AuthUser> => authUser(await request('/api/auth/me')),
  logout: async () => {
    try { await request('/api/auth/logout', { method: 'POST' }); }
    finally { clearAccessToken(); }
  },
  status: async (signal?: AbortSignal) => record(await request('/api/status', { signal })),
  latest: async (signal?: AbortSignal): Promise<Latest> => {
    const value = record(await request('/api/latest', { signal }));
    if (typeof value.status !== 'string' || !('esp32' in value) || !('jetson' in value) ||
      (value.esp32 !== null && !isRecord(value.esp32)) || (value.jetson !== null && !isRecord(value.jetson))) throw new ApiError('Unexpected latest-data schema.');
    return value as Latest;
  },
  history: async (kind: 'sensors' | 'detections', signal?: AbortSignal): Promise<History> => {
    const value = record(await request(`/api/${kind}/history?limit=100`, { signal }));
    if (!Array.isArray(value.data) || typeof value.count !== 'number') throw new ApiError('Unexpected history schema.');
    return value as History;
  },
  analysis: async (signal?: AbortSignal) => record(await request('/api/analysis', { signal })),
  commands: async (signal?: AbortSignal): Promise<Commands> => {
    const value = record(await request('/api/commands', { signal }));
    if (!Array.isArray(value.commands) || typeof value.count !== 'number') throw new ApiError('Unexpected command-list schema.');
    return value as Commands;
  },
  schema: async (signal?: AbortSignal) => record(await request('/openapi.json', { signal })),
  createSession: async (plant_type: string, signal?: AbortSignal) => session(await post('/api/recommendation/sessions', signal, { plant_type })),
  generate: async (id: Session['id'], signal?: AbortSignal) => session(await post(`/api/recommendation/sessions/${encodeURIComponent(id)}/generate`, signal)),
  getSession: async (id: Session['id'], signal?: AbortSignal) => session(await request(`/api/recommendation/sessions/${encodeURIComponent(id)}`, { signal })),
  decide: (id: Session['id'], decision: 'approve' | 'reject', signal?: AbortSignal) => post(`/api/recommendation/sessions/${encodeURIComponent(id)}/${decision}`, signal),
  manual: async (body: { device: string; action: string; duration_minutes: number; reason: string }, signal?: AbortSignal) => {
    const value = record(await post('/api/commands/manual', signal, body));
    if (value.status !== 'queued' || typeof value.command_id !== 'number') throw new ApiError('Unexpected command response. Check the queue before sending another command.');
    return value;
  },
};
