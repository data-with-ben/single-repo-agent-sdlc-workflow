import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import MorningProjection from './MorningProjection';

const CLIENTS = [{ id: 10, name: 'Acme Corp', status: 'active' }];

// Pinned time so before/after-cutoff scenarios are deterministic regardless
// of the real wall clock.
const BEFORE_CUTOFF = new Date('2026-07-07T09:00:00');
const AFTER_CUTOFF = new Date('2026-07-07T14:00:00');

let mockEntries: unknown[] = [];
let postCalls: { path: string; body: unknown }[] = [];

function mockFetchFor(path: string) {
  if (path === '/me/clients') return Promise.resolve(CLIENTS);
  if (path.startsWith('/me/time-entries')) return Promise.resolve(mockEntries);
  return Promise.resolve([]);
}

function stubFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      const path = url.replace('http://localhost:8000', '');
      const method = init?.method ?? 'GET';
      if (method === 'POST') {
        const body = init?.body ? JSON.parse(init.body as string) : undefined;
        postCalls.push({ path, body });
      }
      return Promise.resolve({ ok: true, json: () => mockFetchFor(path) });
    }),
  );
}

describe('MorningProjection', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockEntries = [];
    postCalls = [];
    stubFetch();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('renders the open state and submits a projection before the cutoff', async () => {
    vi.setSystemTime(BEFORE_CUTOFF);
    render(<MorningProjection />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).not.toBeNull();
    });
    expect(screen.getByText('Open')).not.toBeNull();
    expect(screen.getByText(/until 11am cutoff/)).not.toBeNull();

    fireEvent.change(screen.getByLabelText('Planned hours for Acme Corp'), {
      target: { value: '8' },
    });
    fireEvent.click(screen.getByText('Project'));

    await waitFor(() => {
      expect(postCalls.some((c) => c.path === '/time-entries/project')).toBe(true);
    });
  });

  it('renders the locked-in state when already projected before the cutoff', async () => {
    vi.setSystemTime(BEFORE_CUTOFF);
    mockEntries = [
      {
        id: 1,
        consultant_id: 2,
        client_id: 10,
        work_date: '2026-07-07',
        planned_hours: 8,
        actual_hours: null,
        description: null,
        projected_at: '2026-07-07T08:00:00',
        logged_at: null,
        updated_at: null,
        first_submitted_at: '2026-07-07T08:00:00',
        state: 'projected',
      },
    ];

    render(<MorningProjection />);

    await waitFor(() => {
      expect(screen.getByText('Locked in')).not.toBeNull();
    });
    expect(screen.queryByLabelText('Planned hours for Acme Corp')).toBeNull();
  });

  it('renders the missed-not-projected state and still allows submission after the cutoff', async () => {
    vi.setSystemTime(AFTER_CUTOFF);
    render(<MorningProjection />);

    await waitFor(() => {
      expect(screen.getByText('Missed (not projected)')).not.toBeNull();
    });
    expect(screen.getByText('Cutoff passed')).not.toBeNull();
    expect(screen.getByLabelText('Planned hours for Acme Corp')).not.toBeNull();
  });

  it('renders the missed-late state when projected after the cutoff', async () => {
    vi.setSystemTime(AFTER_CUTOFF);
    mockEntries = [
      {
        id: 1,
        consultant_id: 2,
        client_id: 10,
        work_date: '2026-07-07',
        planned_hours: 8,
        actual_hours: null,
        description: null,
        projected_at: '2026-07-07T12:00:00',
        logged_at: null,
        updated_at: null,
        first_submitted_at: '2026-07-07T12:00:00',
        state: 'projected',
      },
    ];

    render(<MorningProjection />);

    await waitFor(() => {
      expect(screen.getByText('Missed (projected late)')).not.toBeNull();
    });
    expect(screen.queryByLabelText('Planned hours for Acme Corp')).toBeNull();
  });
});
