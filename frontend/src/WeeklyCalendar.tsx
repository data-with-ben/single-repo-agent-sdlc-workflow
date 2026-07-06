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

type DayStatus = 'logged' | 'late' | 'missing' | 'pending';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'];
const MIN_DESCRIPTION_LENGTH = 20;
const EOD_HOUR = 15;
const PROJECTION_HOUR = 11;
const MAX_DAILY_POINTS = 30;

function localDateStr(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function startOfWeek(d: Date): Date {
  const weekday = d.getDay(); // 0 = Sunday .. 6 = Saturday
  const diffToMonday = weekday === 0 ? -6 : 1 - weekday;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diffToMonday);
  monday.setHours(0, 0, 0, 0);
  return monday;
}

function weekDates(monday: Date): string[] {
  return Array.from({ length: 5 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return localDateStr(d);
  });
}

function computeDayStatus(
  entries: ApiTimeEntry[],
  workDate: string,
  todayStr: string,
): DayStatus {
  const isPast = workDate < todayStr;

  if (entries.length === 0) {
    return isPast ? 'missing' : 'pending';
  }

  let anyMissing = false;
  let anyLate = false;
  let allLoggedOnDate = true;

  for (const entry of entries) {
    if (!entry.logged_at) {
      anyMissing = true;
      allLoggedOnDate = false;
      continue;
    }
    const loggedDate = entry.logged_at.slice(0, 10);
    if (loggedDate > workDate) {
      anyLate = true;
      allLoggedOnDate = false;
    } else if (loggedDate !== workDate) {
      allLoggedOnDate = false;
    }
  }

  if (isPast && anyMissing) return 'missing';
  if (anyLate) return 'late';
  if (allLoggedOnDate) return 'logged';
  return isPast ? 'missing' : 'pending';
}

function sumHours(entries: ApiTimeEntry[]): number {
  return entries.reduce((total, entry) => total + (entry.actual_hours ?? 0), 0);
}

interface LivePointsHint {
  loggedSameDay: number;
  eodUpdate: number;
  perfectDay: number;
  total: number;
}

function computeLivePointsHint(
  hours: number,
  description: string,
  now: Date,
  existingProjectedAt: string | null,
  todayStr: string,
): LivePointsHint {
  const loggedSameDay = hours > 0 ? 10 : 0;
  const eodUpdate =
    description.trim().length >= MIN_DESCRIPTION_LENGTH && now.getHours() >= EOD_HOUR
      ? 5
      : 0;

  let projectedByEleven = false;
  if (existingProjectedAt) {
    const projected = new Date(existingProjectedAt);
    projectedByEleven =
      localDateStr(projected) === todayStr && projected.getHours() < PROJECTION_HOUR;
  }
  const perfectDay =
    loggedSameDay > 0 && eodUpdate > 0 && projectedByEleven ? 5 : 0;

  return {
    loggedSameDay,
    eodUpdate,
    perfectDay,
    total: Math.min(MAX_DAILY_POINTS, loggedSameDay + eodUpdate + perfectDay),
  };
}

const STATUS_LABELS: Record<DayStatus, string> = {
  logged: 'On time',
  late: 'Logged late',
  missing: 'Missing',
  pending: 'Not yet',
};

function WeeklyCalendar() {
  const today = useMemo(() => new Date(), []);
  const todayStr = useMemo(() => localDateStr(today), [today]);
  const monday = useMemo(() => startOfWeek(today), [today]);
  const days = useMemo(() => weekDates(monday), [monday]);

  const [clients, setClients] = useState<ApiClient[]>([]);
  const [entries, setEntries] = useState<ApiTimeEntry[]>([]);
  const [selectedDate, setSelectedDate] = useState(() =>
    days.includes(todayStr) ? todayStr : days[days.length - 1],
  );
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [hoursInput, setHoursInput] = useState('');
  const [descriptionInput, setDescriptionInput] = useState('');
  const [prefilledFor, setPrefilledFor] = useState('');

  const loadEntries = useCallback(() => {
    const start = days[0];
    const end = days[days.length - 1];
    apiFetch(`/me/time-entries?start=${start}&end=${end}`)
      .then((response) => (response.ok ? response.json() : []))
      .then(setEntries);
  }, [days]);

  useEffect(() => {
    apiFetch('/me/clients')
      .then((response) => (response.ok ? response.json() : []))
      .then((data: ApiClient[]) => {
        setClients(data);
        setSelectedClientId((current) => current ?? data[0]?.id ?? null);
      });
    loadEntries();
  }, [loadEntries]);

  const entriesByDate = useMemo(() => {
    const map = new Map<string, ApiTimeEntry[]>();
    for (const day of days) map.set(day, []);
    for (const entry of entries) {
      map.get(entry.work_date)?.push(entry);
    }
    return map;
  }, [days, entries]);

  const selectedDayEntries = entriesByDate.get(selectedDate) ?? [];
  const selectedClientEntry = selectedDayEntries.find(
    (e) => e.client_id === selectedClientId,
  );

  const selectionKey = `${selectedDate}|${selectedClientId}`;
  if (prefilledFor !== selectionKey) {
    setPrefilledFor(selectionKey);
    setHoursInput(
      selectedClientEntry?.actual_hours != null
        ? String(selectedClientEntry.actual_hours)
        : '',
    );
    setDescriptionInput(selectedClientEntry?.description ?? '');
  }

  const handleSubmit = async () => {
    if (selectedClientId === null) return;
    const actualHours = Number(hoursInput);
    if (Number.isNaN(actualHours)) return;

    await apiFetch('/time-entries/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: selectedClientId,
        work_date: selectedDate,
        actual_hours: actualHours,
      }),
    });

    if (descriptionInput.trim().length > 0) {
      await apiFetch('/time-entries/eod-update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: selectedClientId,
          work_date: selectedDate,
          description: descriptionInput,
        }),
      });
    }

    loadEntries();
  };

  const isToday = selectedDate === todayStr;
  const hint = isToday
    ? computeLivePointsHint(
        Number(hoursInput) || 0,
        descriptionInput,
        new Date(),
        selectedClientEntry?.projected_at ?? null,
        todayStr,
      )
    : null;

  return (
    <section>
      <h2>Weekly calendar</h2>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        {days.map((day, i) => {
          const dayEntries = entriesByDate.get(day) ?? [];
          const status = computeDayStatus(dayEntries, day, todayStr);
          const hours = sumHours(dayEntries);
          const isSelected = day === selectedDate;
          return (
            <button
              key={day}
              type="button"
              aria-label={`${DAY_LABELS[i]} ${day}${day === todayStr ? ' (today)' : ''}`}
              aria-current={isSelected ? 'date' : undefined}
              onClick={() => setSelectedDate(day)}
              style={{
                border: isSelected ? '2px solid blue' : '1px solid gray',
                padding: '0.5rem',
                textAlign: 'left',
              }}
            >
              <div>
                {DAY_LABELS[i]} {day.slice(8, 10)}
                {day === todayStr ? ' · today' : ''}
              </div>
              <div>{hours > 0 ? `${hours}h` : '—'}</div>
              <div>{STATUS_LABELS[status]}</div>
            </button>
          );
        })}
      </div>

      <div style={{ marginTop: '1rem' }}>
        <h3>{selectedDate}</h3>

        <div>
          <label htmlFor="weekly-calendar-client">Client</label>
          <select
            id="weekly-calendar-client"
            aria-label="Client"
            value={selectedClientId ?? ''}
            onChange={(e) => setSelectedClientId(Number(e.target.value))}
          >
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="weekly-calendar-hours">Hours</label>
          <input
            id="weekly-calendar-hours"
            aria-label="Hours"
            type="number"
            value={hoursInput}
            onChange={(e) => setHoursInput(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="weekly-calendar-description">What did you work on?</label>
          <textarea
            id="weekly-calendar-description"
            aria-label="What did you work on?"
            value={descriptionInput}
            onChange={(e) => setDescriptionInput(e.target.value)}
          />
        </div>

        {hint && (
          <p>
            Submitting now: {hint.total} pts
            {hint.perfectDay > 0 ? ' (perfect day)' : ''}
          </p>
        )}

        <button type="button" onClick={handleSubmit}>
          Submit entry
        </button>
      </div>
    </section>
  );
}

export default WeeklyCalendar;
