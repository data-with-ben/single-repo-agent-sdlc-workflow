import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch } from './api';

interface ApiClient {
  id: number;
  name: string;
  status: 'active' | 'archived';
}

interface ApiTimeEntry {
  id: number;
  consultant_id: number;
  client_id: number;
  work_date: string;
  planned_hours: number | null;
  actual_hours: number | null;
  description: string | null;
  projected_at: string | null;
  logged_at: string | null;
  updated_at: string | null;
  first_submitted_at: string | null;
  state: string;
}

type ClientStatus = 'open' | 'locked-in' | 'missed-late' | 'missed-not-projected';

const CUTOFF_HOUR = 11;
const COUNTDOWN_INTERVAL_MS = 30000;

function localDateStr(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function todayCutoff(now: Date): Date {
  const cutoff = new Date(now);
  cutoff.setHours(CUTOFF_HOUR, 0, 0, 0);
  return cutoff;
}

function formatRemaining(ms: number): string {
  const totalMinutes = Math.floor(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}h ${minutes}m`;
}

function clientStatus(entry: ApiTimeEntry | undefined, now: Date): ClientStatus {
  const cutoff = todayCutoff(now);
  if (entry?.projected_at) {
    const projected = new Date(entry.projected_at);
    return projected <= cutoff ? 'locked-in' : 'missed-late';
  }
  return now >= cutoff ? 'missed-not-projected' : 'open';
}

const STATUS_LABELS: Record<ClientStatus, string> = {
  'locked-in': 'Locked in',
  'missed-late': 'Missed (projected late)',
  'missed-not-projected': 'Missed (not projected)',
  open: 'Open',
};

const STATUS_BADGE_CLASS: Record<ClientStatus, string> = {
  'locked-in': 'badge badge--success',
  'missed-late': 'badge badge--danger',
  'missed-not-projected': 'badge badge--danger',
  open: 'badge',
};

function MorningProjection() {
  const [clients, setClients] = useState<ApiClient[]>([]);
  const [entries, setEntries] = useState<ApiTimeEntry[]>([]);
  const [hoursByClient, setHoursByClient] = useState<Record<number, string>>({});
  const [now, setNow] = useState(() => new Date());

  const todayStr = useMemo(() => localDateStr(now), [now]);

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), COUNTDOWN_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  const loadEntries = useCallback(() => {
    apiFetch(`/me/time-entries?start=${todayStr}&end=${todayStr}`)
      .then((response) => (response.ok ? response.json() : []))
      .then(setEntries);
  }, [todayStr]);

  useEffect(() => {
    apiFetch('/me/clients')
      .then((response) => (response.ok ? response.json() : []))
      .then(setClients);
    loadEntries();
  }, [loadEntries]);

  const entryByClientId = useMemo(() => {
    const map = new Map<number, ApiTimeEntry>();
    for (const entry of entries) {
      if (entry.work_date === todayStr) map.set(entry.client_id, entry);
    }
    return map;
  }, [entries, todayStr]);

  const handleSubmit = async (clientId: number) => {
    const hours = Number(hoursByClient[clientId]);
    if (Number.isNaN(hours)) return;

    await apiFetch('/time-entries/project', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: clientId,
        work_date: todayStr,
        planned_hours: hours,
      }),
    });

    loadEntries();
  };

  const cutoff = todayCutoff(now);
  const beforeCutoff = now < cutoff;
  const countdownText = beforeCutoff
    ? `${formatRemaining(cutoff.getTime() - now.getTime())} until 11am cutoff`
    : 'Cutoff passed';

  return (
    <section className="card">
      <h2>Project your day</h2>
      <p className="text-muted">{countdownText}</p>
      <ul>
        {clients.map((c) => {
          const entry = entryByClientId.get(c.id);
          const status = clientStatus(entry, now);
          const canSubmit = status === 'open' || status === 'missed-not-projected';
          return (
            <li key={c.id}>
              <span>{c.name}</span>
              <span className={STATUS_BADGE_CLASS[status]}>{STATUS_LABELS[status]}</span>
              {canSubmit && (
                <>
                  <input
                    aria-label={`Planned hours for ${c.name}`}
                    type="number"
                    value={hoursByClient[c.id] ?? ''}
                    onChange={(e) =>
                      setHoursByClient((prev) => ({ ...prev, [c.id]: e.target.value }))
                    }
                  />
                  <button
                    type="button"
                    className="pill-btn pill-btn--primary"
                    onClick={() => handleSubmit(c.id)}
                  >
                    Project
                  </button>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export default MorningProjection;
