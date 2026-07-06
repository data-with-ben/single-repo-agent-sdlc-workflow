import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import Brackets from './Brackets';

const BRACKETS = {
  matchups: [
    {
      user_a_id: 1,
      user_a_display_name: 'Morgan Manager',
      user_a_gain: 42,
      user_b_id: 2,
      user_b_display_name: 'Riley Player-Manager',
      user_b_gain: -10,
      winner_id: 1,
    },
    {
      user_a_id: 3,
      user_a_display_name: 'Consultant 1',
      user_a_gain: 0,
      user_b_id: 4,
      user_b_display_name: 'Consultant 2',
      user_b_gain: 0,
      winner_id: null,
    },
  ],
  bye_user_id: 5,
};

describe('Brackets', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        const path = url.replace('http://localhost:8000', '');
        if (path.startsWith('/brackets')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(BRACKETS) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('renders each matchup with both sides gain figures', async () => {
    render(<Brackets />);

    await waitFor(() => {
      expect(screen.getByText(/Morgan Manager/)).not.toBeNull();
    });
    expect(screen.getByText(/\+42/)).not.toBeNull();
    expect(screen.getByText(/-10/)).not.toBeNull();
  });

  it('highlights the winner and marks a tie as a draw', async () => {
    render(<Brackets />);

    await waitFor(() => {
      expect(screen.getByText(/Morgan Manager/).style.fontWeight).toBe('bold');
    });
    expect(screen.getByText(/Riley Player-Manager/).style.fontWeight).toBe('normal');
    expect(screen.getByText(/draw/)).not.toBeNull();
  });

  it('shows a bye when the pool is odd', async () => {
    render(<Brackets />);

    await waitFor(() => {
      expect(screen.getByText(/Bye this week/)).not.toBeNull();
    });
  });
});
