---
id: doc-1
title: Fantasy Timesheets — Product & Technical Spec
type: specification
created_date: '2026-07-04 01:05'
updated_date: '2026-07-04 01:07'
---
# Fantasy Timesheets — Product & Technical Spec

Durable domain context for the Fantasy Timesheets build. This is the source of truth for domain rules referenced by task acceptance criteria. If code and this doc disagree, this doc wins until updated. **Section 4 (Data Model) is the context required by task-16 AC #1.**

## 1. Concept

A consultancy time-tracking app with a game layer. Consultants log daily time against clients (the real product). On top: consultants are randomly grouped into teams of 3–5 that play daily head-to-head "games" scored from timesheet *behavior* — projecting the day by 11am, logging actuals same day, writing an end-of-day update. Games score behind the scenes and reveal at 6pm. Separately, every user runs a stock portfolio holding shares in individual consultants, earning "dividends" when owned consultants win games or hit objectives; share prices float on rolling performance. Behavioral goal: make entering and organizing time early the winning move, driven by peer incentives.

## 2. Roles

- **Admin / Manager** — creates clients, assigns consultants to clients, manages seasons, views operational dashboards. May also be consultant and holder.
- **Consultant** — logs time, is auto-placed on daily game teams, is a tradable asset.
- **Portfolio holder** — every user; buys/sells shares and earns dividends.

Roles are permission flags on one account, not separate accounts.

## 3. Core behavioral loop

1. Project the day by 11am → manager visibility + game points.
2. Log actuals same day → accurate timesheets + game points.
3. Write an EOD update → richer descriptions + bonus.
4. These decide daily games → teammates and shareholders care about your promptness → peer pressure replaces admin nagging.

Rules are public; live daily scores are hidden until the 6pm reveal.

## 4. Data model  (REQUIRED CONTEXT — task-16 AC #1)

Types are indicative; persistence is an implementation choice. Timestamps stored UTC, thresholds evaluated in the consultant's local zone.

### User
`id, displayName, email, roles[] (admin|consultant), createdAt, status (active|pto|inactive)`

### Client
`id, name, status (active|archived), createdAt`

### Assignment
Which clients a consultant may log against; drives the time-entry client dropdown.
`id, consultantId, clientId, startDate, endDate?`

### TimeEntry  — heart of the system
One consultant's work on one client for one `workDate`. Lifecycle with timestamps at each transition (see Section 5). Multiple entries per (consultant, workDate) allowed — one per client.
```
id
consultantId
workDate            calendar day the work is for
clientId
plannedHours?       set at projection
actualHours?        set at log
description?
projectedAt?        timestamp day was projected (planned hours + client set)
loggedAt?           timestamp actuals first submitted
updatedAt?          timestamp of an EOD description write/revise after 15:00 local
firstSubmittedAt    immutable; earliest submission of any field (anti-gaming)
state               empty|projected|logged|updated
```

### Season
Team-assignment epoch; teams reshuffle each season.
`id, name, startDate, endDate, status (upcoming|active|complete), teamSize (3..5 target)`

### Team
`id, seasonId, name, memberIds[]`  (3–5 consultants, randomly assigned at season start)

### Game
One matchup on one date.
`id, gameDate, seasonId, homeTeamId, awayTeamId, homeScore?, awayScore?, revealed (bool), state (scheduled|in_progress|final)`

### ObjectiveResult
Per consultant, per game date — the box-score row.
`id, gameDate, consultantId, teamId, projectedBy11 (bool), loggedSameDay (bool), eodUpdate (bool), perfectDay (bool), points (int)`

### Holding
`id, userId, consultantId, shares (int)`  — fixed supply per consultant (default 100).

### Transaction
Every buy/sell against the market maker.
`id, userId, consultantId, side (buy|sell), shares, pricePerShare, total, executedAt`

### Dividend
Payout from a game result.
`id, userId, consultantId, gameDate, reason (team_win|perfect_day|star_of_game), shares, perShare, total`

### Wallet
`userId, balance (points)`  — spendable currency; grows via dividends.

## 5. TimeEntry state machine

```
empty ──project()──▶ projected ──log()──▶ logged ──eodUpdate()──▶ updated
```
- `project()` sets `plannedHours`, `clientId`, `projectedAt`. Counts for the 11am objective only if `projectedAt <= 11:00` local on `workDate`.
- `log()` sets `actualHours`, `loggedAt`. Counts for same-day objective if `loggedAt` is on `workDate`.
- `eodUpdate()` sets/revises `description`, sets `updatedAt`. Counts if `updatedAt >= 15:00` local on `workDate` and description meets min length (default 20 chars).
- `firstSubmittedAt` is written once, never changes.
- **Anti-gaming:** objective checks read transition timestamps, not mutable current state. Skipping states is allowed but forfeits the skipped objectives.

## 6. Objective scoring (per consultant, per game date; aggregated across the day's entries)

| Objective | Condition | Points |
|---|---|---|
| Projected by 11am | Every working slot has `projectedAt <= 11:00` | 10 |
| Logged same day | Actuals submitted on `workDate` for all projected work | 10 |
| EOD update | Description write/revise `>= 15:00`, meets min length | +5 |
| Perfect day | All three above | +5 |
| Max per consultant/day | | 30 |

Team bonus (added to team score): whole team projected by 11am (all *present* members) → +10.

No assigned work for the day = neutral (excluded from denominators, not penalized). PTO = absent (excluded).

## 7. Teams, games, normalization

- Random partition of active consultants into teams of 3–5 at season start; reshuffle each season (default 2–4 weeks).
- Each game date, pair teams (round-robin). Odd count → one bye.
- Team daily score = sum of members' points **normalized per present member** (`sum / presentMemberCount`) + team bonus. Normalization keeps 3-person teams competitive vs 5-person.
- Higher normalized score wins. Draw handling: draw flag (recommended) — confirm in open decisions.
- PTO members excluded from denominator; team entirely on PTO → game postponed/voided.
- Reveal at 18:00 local (configurable); scores hidden from non-admins before reveal.

## 8. Market

- Fixed supply, default 100 shares/consultant. New hires IPO at season boundaries.
- Automated market maker (no order book):
  ```
  fairValue = BASE + K * rolling10DayAvgPersonalScore
  buyPrice  = fairValue * (1 + spread/2) + demandPressure
  sellPrice = fairValue * (1 - spread/2) - demandPressure
  ```
  Suggested starts: `BASE=2, K=0.4, spread=0.06`; `demandPressure` from recent net volume, decaying over time. Tune against seed data.
- Ownership cap: one user ≤ 25% of a consultant's supply (incl. self). Self/teammate trading allowed by design.
- Dividends (per share held at end of the game date, paid at reveal):

  | Reason | Condition | Per share |
  |---|---|---|
  | Team win | Consultant's team won | +2 |
  | Perfect day | Consultant had a perfect day | +1 |
  | Star of the game | Top normalized performer on the losing team | +0.5 |

- Wallet: dividends credit, buys debit, sells credit.

## 9. Screens

1. Consultant morning "project your day" (pre-11am projection).
2. Consultant weekly calendar + day entry (week strip + live points hint).
3. Admin clients & assignments.
4. Daily games scoreboard + box score (hidden until reveal).
5. Portfolio / exchange (holdings, prices, dividends, movers).

## 10. Architecture notes

- **Objective engine** = pure function `(TimeEntry[], date, ptoCalendar) -> ObjectiveResult[]`, no I/O, heavily unit-tested.
- **Pricing** = pure module implementing Section 8.
- **Reveal/nightly job**: objective engine → team scoring → game winners → write results/dividends/wallets → recompute prices. Idempotent, keyed on `gameDate`, safe to re-run.
- Thresholds (11:00/15:00/18:00) evaluated in local zone; store UTC.
- Ship a seed script: clients, ~15 consultants with varied punctuality profiles, one active season with teams.

## 11. Open decisions

1. Draw handling: draw flag vs both-win (recommend draw flag).
2. Exact `BASE/K/spread` and demand-pressure curve — tune against seed.
3. Admins see live pre-reveal scores? (recommend yes, admin-only).
4. Weekly 1v1 portfolio brackets for user-vs-user rivalry (nice-to-have).
5. Min description length and definition of a "working slot" (org policy).

## 12. Non-goals

- No payroll/invoicing integration, no real money, and no game/market surface may expose billable hours or description *content* — behavioral/timeliness signals only.
