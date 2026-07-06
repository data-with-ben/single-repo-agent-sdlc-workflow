import { useEffect, useState } from 'react';
import { apiFetch } from './api';

interface ApiGame {
  id: number;
  game_date: string;
  home_team_name: string;
  away_team_name: string;
  revealed: boolean;
  state: string;
  home_score: number | null;
  away_score: number | null;
}

interface ApiPlayerLine {
  consultant_id: number;
  display_name: string;
  projected_by_11: boolean;
  logged_same_day: boolean;
  eod_update: boolean;
  points: number;
}

interface ApiTeamBoxScore {
  team_id: number;
  team_name: string;
  normalized_score: number;
  team_bonus_applied: boolean;
  players: ApiPlayerLine[];
}

interface ApiBoxScore {
  game_id: number;
  home: ApiTeamBoxScore;
  away: ApiTeamBoxScore;
  star_of_game_consultant_id: number | null;
}

function scoreLabel(revealed: boolean, score: number | null): string {
  if (score === null) return '??';
  return revealed ? `${score}` : `${score} (admin preview)`;
}

function checkmark(value: boolean): string {
  return value ? '✓' : '—';
}

function Checkmark({ value }: { value: boolean }) {
  return <span className={value ? 'text-success' : 'text-muted'}>{checkmark(value)}</span>;
}

function TeamTable({ team, starConsultantId }: { team: ApiTeamBoxScore; starConsultantId: number | null }) {
  return (
    <div>
      <h4>
        {team.team_name} · {team.normalized_score.toFixed(1)}/member
      </h4>
      <table className="table">
        <thead>
          <tr>
            <th>Player</th>
            <th>11am</th>
            <th>Same day</th>
            <th>EOD</th>
            <th>Pts</th>
          </tr>
        </thead>
        <tbody>
          {team.players.map((p) => (
            <tr key={p.consultant_id}>
              <td>{p.display_name}</td>
              <td><Checkmark value={p.projected_by_11} /></td>
              <td><Checkmark value={p.logged_same_day} /></td>
              <td><Checkmark value={p.eod_update} /></td>
              <td>{p.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {team.team_bonus_applied && (
        <p className="text-success">Team bonus: all projected by 11am (+10)</p>
      )}
      {team.players.some((p) => p.consultant_id === starConsultantId) && (
        <p aria-label="Star of the game">
          Star of the game: {team.players.find((p) => p.consultant_id === starConsultantId)?.display_name}
        </p>
      )}
    </div>
  );
}

function Scoreboard() {
  const [games, setGames] = useState<ApiGame[]>([]);
  const [selectedGameId, setSelectedGameId] = useState<number | null>(null);
  const [boxScore, setBoxScore] = useState<ApiBoxScore | null>(null);

  useEffect(() => {
    apiFetch('/games')
      .then((response) => (response.ok ? response.json() : []))
      .then((data: ApiGame[]) => {
        setGames(data);
        const firstRevealed = data.find((g) => g.revealed);
        if (firstRevealed) setSelectedGameId(firstRevealed.id);
      });
  }, []);

  const selectedGame = games.find((g) => g.id === selectedGameId);

  useEffect(() => {
    if (selectedGameId === null || !selectedGame?.revealed) {
      return;
    }
    apiFetch(`/games/${selectedGameId}/box-score`)
      .then((response) => (response.ok ? response.json() : null))
      .then(setBoxScore);
  }, [selectedGameId, selectedGame]);

  const visibleBoxScore =
    selectedGame?.revealed && boxScore?.game_id === selectedGameId ? boxScore : null;

  return (
    <section className="card">
      <h2>Today&apos;s games</h2>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {games.map((game) => {
          const isSelected = game.id === selectedGameId;
          return (
            <button
              key={game.id}
              type="button"
              aria-label={`${game.home_team_name} vs ${game.away_team_name}`}
              onClick={() => game.revealed && setSelectedGameId(game.id)}
              className={`tile${isSelected ? ' is-selected' : ''}`}
            >
              <div className={game.revealed ? 'text-muted' : 'badge badge--warning'}>
                {game.revealed ? `Final · ${game.game_date}` : 'In progress · hidden'}
              </div>
              <div>
                {game.home_team_name} {scoreLabel(game.revealed, game.home_score)}
              </div>
              <div>
                {game.away_team_name} {scoreLabel(game.revealed, game.away_score)}
              </div>
            </button>
          );
        })}
      </div>

      {visibleBoxScore && (
        <div style={{ marginTop: '1rem' }}>
          <h3>Box score</h3>
          <div style={{ display: 'flex', gap: '2rem' }}>
            <TeamTable
              team={visibleBoxScore.home}
              starConsultantId={visibleBoxScore.star_of_game_consultant_id}
            />
            <TeamTable
              team={visibleBoxScore.away}
              starConsultantId={visibleBoxScore.star_of_game_consultant_id}
            />
          </div>
        </div>
      )}
    </section>
  );
}

export default Scoreboard;
