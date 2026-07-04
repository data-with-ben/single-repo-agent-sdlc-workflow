import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import UserSwitcher from './UserSwitcher';
import { CurrentUserProvider } from './currentUser';
import { getStoredUserId } from './currentUserContext';

const MOCK_USERS = [
  { id: 1, display_name: 'Ada', roles: ['consultant'] },
  { id: 2, display_name: 'Morgan Manager', roles: ['admin'] },
];

describe('UserSwitcher', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        json: () => Promise.resolve(MOCK_USERS),
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('fetches and renders the list of users', async () => {
    render(
      <CurrentUserProvider>
        <UserSwitcher />
      </CurrentUserProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Ada (consultant)')).not.toBeNull();
    });
    expect(screen.getByText('Morgan Manager (admin)')).not.toBeNull();
  });

  it('updates the current user and persists it to localStorage on change', async () => {
    render(
      <CurrentUserProvider>
        <UserSwitcher />
      </CurrentUserProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText('Ada (consultant)')).not.toBeNull();
    });

    const select = screen.getByRole('combobox') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: '2' } });

    expect(select.value).toBe('2');
    expect(getStoredUserId()).toBe('2');
  });
});
