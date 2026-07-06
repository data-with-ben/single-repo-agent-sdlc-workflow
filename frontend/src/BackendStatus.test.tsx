import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import BackendStatus from './BackendStatus';

describe('BackendStatus', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('shows the healthy state when the backend responds ok', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok' }),
      }),
    );

    render(<BackendStatus />);

    await waitFor(() => {
      expect(screen.getByText('Backend: ok')).not.toBeNull();
    });
  });

  it('shows the unavailable state when the fetch rejects', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('network error')),
    );

    render(<BackendStatus />);

    await waitFor(() => {
      expect(screen.getByText('Backend unavailable')).not.toBeNull();
    });
  });

  it('shows the unavailable state when the backend returns a non-2xx response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: () => Promise.resolve({}),
      }),
    );

    render(<BackendStatus />);

    await waitFor(() => {
      expect(screen.getByText('Backend unavailable')).not.toBeNull();
    });
  });
});
