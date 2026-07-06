import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import WeeklyCalendar from './WeeklyCalendar';
import { setStoredUserId } from './currentUserContext';

const CLIENTS = [{ id: 10, name: 'Acme Corp', status: 'active' }];

function localDateStr(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function startOfWeek(d: Date): Date {
  const weekday = d.getDay();
  const diffToMonday = weekday === 0 ? -6 : 1 - weekday;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diffToMonday);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

// Pinned to a Tuesday so "today" always falls inside the Mon-Fri week strip,
// regardless of which day of the real week the test happens to run on.
const FIXED_NOW = new Date('2026-07-07T12:00:00');
const todayStr = localDateStr(FIXED_NOW);
const monday = startOfWeek(FIXED_NOW);
const yesterday = monday; // FIXED_NOW is a Tuesday, so Monday is "yesterday"

let mockEntries: unknown[] = [];
let postCalls: { path: string; body: unknown }[] = [];

function mockFetchFor(path: string) {
  if (path === '/me/clients') return Promise.resolve(CLIENTS);
  if (path.startsWith('/me/time-entries')) return Promise.resolve(mockEntries);
  return Promise.resolve([]);
}

function renderCalendar() {
  setStoredUserId('2');
  return render(<WeeklyCalendar />);
}

describe('WeeklyCalendar', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(FIXED_NOW);
    mockEntries = [];
    postCalls = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        const path = url.replace('http://localhost:8000', '');
        const method = init?.method ?? 'GET';
        if (method === 'POST') {
          const body = init?.body ? JSON.parse(init.body as string) : undefined;
          postCalls.push({ path, body });
        }
        return Promise.resolve({
          json: () => mockFetchFor(path),
        });
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.useRealTimers();
    localStorage.clear();
  });

  it('renders a week strip with today marked as pending when no entry exists', async () => {
    renderCalendar();

    await waitFor(() => {
      expect(screen.getByLabelText(new RegExp(`${todayStr} \\(today\\)`))).not.toBeNull();
    });
    const todayTile = screen.getByLabelText(new RegExp(`${todayStr} \\(today\\)`));
    expect(todayTile.textContent).toContain('Not yet');
  });

  it('shows missing for a past day with no logged entry', async () => {
    mockEntries = [];
    renderCalendar();

    const yesterdayStr = localDateStr(yesterday);
    await waitFor(() => {
      expect(screen.getByLabelText(new RegExp(yesterdayStr))).not.toBeNull();
    });
    const tile = screen.getByLabelText(new RegExp(yesterdayStr));
    expect(tile.textContent).toContain('Missing');
  });

  it('shows logged for a day whose entry was logged on that date', async () => {
    const yesterdayStr = localDateStr(yesterday);
    mockEntries = [
      {
        id: 1,
        consultant_id: 2,
        client_id: 10,
        work_date: yesterdayStr,
        planned_hours: 8,
        actual_hours: 8,
        description: 'Did work',
        projected_at: null,
        logged_at: `${yesterdayStr}T10:00:00`,
        updated_at: null,
        first_submitted_at: `${yesterdayStr}T10:00:00`,
        state: 'logged',
      },
    ];
    renderCalendar();

    await waitFor(() => {
      const tile = screen.getByLabelText(new RegExp(yesterdayStr));
      expect(tile.textContent).toContain('On time');
    });
  });

  it('submits hours and description for the selected day', async () => {
    renderCalendar();

    await waitFor(() => {
      expect(screen.getByLabelText('Client')).not.toBeNull();
    });

    fireEvent.change(screen.getByLabelText('Hours'), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText('What did you work on?'), {
      target: { value: 'Wrapped up the auth refactor and paired on API tests' },
    });
    fireEvent.click(screen.getByText('Submit entry'));

    await waitFor(() => {
      expect(postCalls.some((c) => c.path === '/time-entries/log')).toBe(true);
      expect(postCalls.some((c) => c.path === '/time-entries/eod-update')).toBe(true);
    });
  });

  it('does not call eod-update when no description was entered', async () => {
    renderCalendar();

    await waitFor(() => {
      expect(screen.getByLabelText('Client')).not.toBeNull();
    });

    fireEvent.change(screen.getByLabelText('Hours'), { target: { value: '8' } });
    fireEvent.click(screen.getByText('Submit entry'));

    await waitFor(() => {
      expect(postCalls.some((c) => c.path === '/time-entries/log')).toBe(true);
    });
    expect(postCalls.some((c) => c.path === '/time-entries/eod-update')).toBe(false);
  });

  it('shows a live points hint reflecting hours entered for today', async () => {
    renderCalendar();

    await waitFor(() => {
      expect(screen.getByLabelText('Hours')).not.toBeNull();
    });

    fireEvent.change(screen.getByLabelText('Hours'), { target: { value: '8' } });

    await waitFor(() => {
      expect(screen.getByText(/Submitting now: 10 pts/)).not.toBeNull();
    });
  });

  it('does not show a live points hint when a past day is selected', async () => {
    const yesterdayStr = localDateStr(yesterday);
    mockEntries = [
      {
        id: 1,
        consultant_id: 2,
        client_id: 10,
        work_date: yesterdayStr,
        planned_hours: 8,
        actual_hours: 8,
        description: 'Did work',
        projected_at: null,
        logged_at: `${yesterdayStr}T10:00:00`,
        updated_at: null,
        first_submitted_at: `${yesterdayStr}T10:00:00`,
        state: 'logged',
      },
    ];
    renderCalendar();

    await waitFor(() => {
      expect(screen.getByLabelText(new RegExp(yesterdayStr))).not.toBeNull();
    });
    fireEvent.click(screen.getByLabelText(new RegExp(yesterdayStr)));

    await waitFor(() => {
      expect(screen.getByText(yesterdayStr)).not.toBeNull();
    });
    expect(screen.queryByText(/Submitting now:/)).toBeNull();
  });
});
