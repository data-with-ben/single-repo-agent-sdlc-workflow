import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import ClientAdmin from './ClientAdmin';
import { CurrentUserProvider } from './currentUser';
import { setStoredUserId } from './currentUserContext';

const USERS = [
  { id: 1, display_name: 'Ada Admin', roles: ['admin'] },
  { id: 2, display_name: 'Cara Consultant', roles: ['consultant'] },
];

const CLIENTS = [
  { id: 10, name: 'Acme', status: 'active' },
  { id: 11, name: 'Old Co', status: 'archived' },
];

function mockFetchFor(path: string) {
  if (path === '/users') return Promise.resolve(USERS);
  if (path === '/clients') return Promise.resolve(CLIENTS);
  if (path.startsWith('/clients/10/assignments')) return Promise.resolve([]);
  return Promise.resolve([]);
}

function renderAsUser(userId: number) {
  setStoredUserId(String(userId));
  return render(
    <CurrentUserProvider>
      <ClientAdmin />
    </CurrentUserProvider>,
  );
}

describe('ClientAdmin', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        const path = url.replace('http://localhost:8000', '');
        return Promise.resolve({
          ok: true,
          json: () => mockFetchFor(path),
        });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('renders the client list for any user', async () => {
    renderAsUser(2);

    await waitFor(() => {
      expect(screen.getByText(/Acme/)).not.toBeNull();
    });
    expect(screen.getByText(/Old Co/)).not.toBeNull();
  });

  it('hides admin controls for a non-admin user', async () => {
    renderAsUser(2);

    await waitFor(() => {
      expect(screen.getByText(/Acme/)).not.toBeNull();
    });
    expect(screen.queryByText('+ Add client')).toBeNull();
  });

  it('shows admin controls for an admin user', async () => {
    renderAsUser(1);

    await waitFor(() => {
      expect(screen.getByText('+ Add client')).not.toBeNull();
    });
  });

  it('lets an admin select a client and see the assign control', async () => {
    renderAsUser(1);

    await waitFor(() => {
      expect(screen.getByText(/Acme/)).not.toBeNull();
    });

    fireEvent.click(screen.getByText(/Acme/));

    await waitFor(() => {
      expect(screen.getByLabelText('Assign consultant')).not.toBeNull();
    });
  });

  it('does not crash when /clients returns a non-ok response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        const path = url.replace('http://localhost:8000', '');
        if (path === '/clients') {
          return Promise.resolve({
            ok: false,
            json: () => Promise.resolve({ detail: 'Missing X-User-Id header' }),
          });
        }
        return Promise.resolve({ ok: true, json: () => mockFetchFor(path) });
      }),
    );

    const { container } = renderAsUser(2);

    await waitFor(() => {
      expect(screen.getByText('Clients and assignments')).not.toBeNull();
    });
    expect(container.querySelector('ul')?.children.length ?? 0).toBe(0);
  });
});
