import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from './api';

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('attaches the X-User-Id header from the stored current user', async () => {
    localStorage.setItem('currentUserId', '42');

    await apiFetch('/users');

    expect(fetch).toHaveBeenCalledTimes(1);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get('X-User-Id')).toBe('42');
  });

  it('omits the header when no user is selected', async () => {
    await apiFetch('/users');

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get('X-User-Id')).toBeNull();
  });
});
