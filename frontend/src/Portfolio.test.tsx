import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import Portfolio from './Portfolio';

const PORTFOLIO = {
  wallet_balance: 142,
  holdings: [
    {
      consultant_id: 1,
      display_name: 'Priya K.',
      shares: 12,
      buy_price: 18.4,
      sell_price: 18.0,
      movement_pct: 14,
    },
  ],
  dividends: [
    {
      consultant_id: 1,
      game_date: '2026-07-01',
      reason: 'team_win',
      shares: 12,
      per_share: 2.0,
      total: 24.0,
    },
  ],
  market_movers: [
    {
      consultant_id: 3,
      display_name: 'Maria G.',
      movement_pct: 18,
      recent_team_wins: 3,
      recent_missed_projections: 0,
    },
  ],
};

const EXCHANGE = [
  { consultant_id: 5, display_name: 'Chen W.', buy_price: 10.2, sell_price: 9.8 },
];

let postCalls: { path: string; body: unknown }[] = [];
let buyShouldFail = false;

function mockFetchFor(path: string) {
  if (path === '/me/portfolio') return Promise.resolve(PORTFOLIO);
  if (path === '/exchange') return Promise.resolve(EXCHANGE);
  return Promise.resolve([]);
}

describe('Portfolio', () => {
  beforeEach(() => {
    postCalls = [];
    buyShouldFail = false;
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        const path = url.replace('http://localhost:8000', '');
        const method = init?.method ?? 'GET';
        if (method === 'POST') {
          const body = init?.body ? JSON.parse(init.body as string) : undefined;
          postCalls.push({ path, body });
          if (buyShouldFail) {
            return Promise.resolve({
              ok: false,
              json: () => Promise.resolve({ detail: 'insufficient wallet balance' }),
            });
          }
          return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
        }
        return Promise.resolve({ ok: true, json: () => mockFetchFor(path) });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it('shows real holdings with live quotes and 7-day movement', async () => {
    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('Priya K.')).not.toBeNull();
    });
    expect(screen.getByText('18.4')).not.toBeNull();
    expect(screen.getByText('+14%')).not.toBeNull();
  });

  it('shows the dividend feed and market movers', async () => {
    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText(/team_win/)).not.toBeNull();
    });
    expect(screen.getByText(/Maria G\./)).not.toBeNull();
  });

  it('calls the trade buy endpoint when Buy is clicked', async () => {
    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('Buy')).not.toBeNull();
    });
    fireEvent.click(screen.getByText('Buy'));

    await waitFor(() => {
      expect(postCalls.some((c) => c.path === '/trade/buy')).toBe(true);
    });
  });

  it('calls the trade sell endpoint when Sell is clicked', async () => {
    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('Sell')).not.toBeNull();
    });
    fireEvent.click(screen.getByText('Sell'));

    await waitFor(() => {
      expect(postCalls.some((c) => c.path === '/trade/sell')).toBe(true);
    });
  });

  it('surfaces a rejected trade error rather than failing silently', async () => {
    buyShouldFail = true;
    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('Buy')).not.toBeNull();
    });
    fireEvent.click(screen.getByText('Buy'));

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain(
        'insufficient wallet balance',
      );
    });
  });

  it('lets a user browse the exchange to discover an unheld consultant', async () => {
    render(<Portfolio />);

    await waitFor(() => {
      expect(screen.getByText('Browse the exchange')).not.toBeNull();
    });
    expect(screen.queryByText('Chen W.')).toBeNull();

    fireEvent.click(screen.getByText('Browse the exchange'));

    await waitFor(() => {
      expect(screen.getByText('Chen W.')).not.toBeNull();
    });
  });
});
