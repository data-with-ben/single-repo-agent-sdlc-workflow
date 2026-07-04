import { getStoredUserId } from './currentUserContext';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Fetch wrapper that attaches the dev-mode X-User-Id header from the
 * currently selected user (see currentUser.tsx). All API calls should go
 * through this rather than calling fetch directly, so identity is
 * consistently attached everywhere.
 */
export function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const userId = getStoredUserId();
  const headers = new Headers(init.headers);
  if (userId !== null) {
    headers.set('X-User-Id', userId);
  }

  return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
}
