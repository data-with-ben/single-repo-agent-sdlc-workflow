import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import Scoreboard from './Scoreboard';

const GAMES = [
  {
    id: 1,
    game_date: '2026-07-06',
    home_team_name: 'Deliverables',
    away_team_name: 'Net 30',
    revealed: false,
    state: 'in_progress',
    home_score: null,
    away_score: null,
  },
  {
    id: 2,
    game_date: '2026-07-05',
    home_team_name: 'Sandbaggers',
    away_team_name: 'Scope Creep',
    revealed: true,
    state: 'final',
    home_score: 87,
    away_score: 71,
  },
];

const BOX_SCORE = {
  game_id: 2,
  home: {
    team_id: 10,
    team_name: 'Sandbaggers',
    normalized_score: 29.0,
    team_bonus_applied: true,
    players: [
      {
        consultant_id: 1,
        display_name: 'Priya K.',
        projected_by_11: true,
        logged_same_day: true,
        eod_update: true,
        points: 30,
      },
    ],
  },
  away: {
    team_id: 20,
    team_name: 'Scope Creep',
    normalized_score: 17.8,
    team_bonus_applied: false,
    players: [
      {
        consultant_id: 2,
        display_name: 'Lee T.',
        projected_by_11: true,
        logged_same_day: true,
        eod_update: true,
        points: 30,
      },
    ],
  },
  star_of_game_consultant_id: 2,
};

function mockFetchFor(path: string) {
  if (path === '/games') return Promise.resolve(GAMES);
  if (path === '/games/2/box-score') return Promise.resolve(BOX_SCORE);
  return Promise.resolve([]);
}

describe('Scoreboard', () => {
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

  it('renders a hidden game without scores', async () => {
    render(<Scoreboard />);

    await waitFor(() => {
      expect(screen.getByLabelText('Deliverables vs Net 30')).not.toBeNull();
    });
    const hiddenGame = screen.getByLabelText('Deliverables vs Net 30');
    expect(hiddenGame.textContent).toContain('In progress · hidden');
    expect(hiddenGame.textContent).toContain('??');
  });

  it('renders the revealed game with real scores', async () => {
    render(<Scoreboard />);

    await waitFor(() => {
      const revealedGame = screen.getByLabelText('Sandbaggers vs Scope Creep');
      expect(revealedGame.textContent).toContain('87');
      expect(revealedGame.textContent).toContain('71');
    });
  });

  it('shows the box score with per-player checkmarks for the revealed game', async () => {
    render(<Scoreboard />);

    await waitFor(() => {
      expect(screen.getByText('Priya K.')).not.toBeNull();
    });
    expect(screen.getByText('Lee T.')).not.toBeNull();
  });

  it('shows the star-of-game callout', async () => {
    render(<Scoreboard />);

    await waitFor(() => {
      expect(screen.getByLabelText('Star of the game')).not.toBeNull();
    });
    expect(screen.getByLabelText('Star of the game').textContent).toContain('Lee T.');
  });

  it('does not fetch a box score for a hidden game when clicked', async () => {
    render(<Scoreboard />);

    await waitFor(() => {
      expect(screen.getByLabelText('Deliverables vs Net 30')).not.toBeNull();
    });
    fireEvent.click(screen.getByLabelText('Deliverables vs Net 30'));

    await waitFor(() => {
      expect(screen.getByText('Priya K.')).not.toBeNull();
    });
    // Selecting the hidden game must not replace the visible box score with
    // one for a game whose scores aren't supposed to be shown.
    expect(screen.getByText('Priya K.')).not.toBeNull();
  });
});
