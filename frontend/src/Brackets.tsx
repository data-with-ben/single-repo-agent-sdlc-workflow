import { useEffect, useState } from 'react';
import { apiFetch } from './api';

interface ApiMatchup {
  user_a_id: number;
  user_a_display_name: string;
  user_a_gain: number;
  user_b_id: number;
  user_b_display_name: string;
  user_b_gain: number;
  winner_id: number | null;
}

interface ApiBrackets {
  matchups: ApiMatchup[];
  bye_user_id: number | null;
}

function currentWeekStart(): string {
  const now = new Date();
  const day = now.getDay(); // 0 = Sunday, 1 = Monday, ...
  const daysSinceMonday = (day + 6) % 7;
  const monday = new Date(now);
  monday.setDate(now.getDate() - daysSinceMonday);
  return monday.toISOString().slice(0, 10);
}

function gain(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(0)}`;
}

function Brackets() {
  const [brackets, setBrackets] = useState<ApiBrackets | null>(null);

  useEffect(() => {
    apiFetch(`/brackets?week_start=${currentWeekStart()}`)
      .then((response) => (response.ok ? response.json() : null))
      .then(setBrackets);
  }, []);

  if (!brackets) {
    return null;
  }

  return (
    <section className="card">
      <h2>This week&apos;s brackets</h2>
      <ul>
        {brackets.matchups.map((m) => (
          <li key={`${m.user_a_id}-${m.user_b_id}`} className="card">
            <span
              style={{ fontWeight: m.winner_id === m.user_a_id ? 'bold' : 'normal' }}
            >
              {m.user_a_display_name} ({gain(m.user_a_gain)})
            </span>
            {' vs '}
            <span
              style={{ fontWeight: m.winner_id === m.user_b_id ? 'bold' : 'normal' }}
            >
              {m.user_b_display_name} ({gain(m.user_b_gain)})
            </span>
            {m.winner_id === null && ' — draw'}
          </li>
        ))}
      </ul>
      {brackets.bye_user_id !== null && (
        <p className="text-muted">Bye this week: user {brackets.bye_user_id}</p>
      )}
    </section>
  );
}

export default Brackets;
