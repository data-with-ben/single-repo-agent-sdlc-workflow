---
id: TASK-39
title: Apply a dark-theme design system across the app
status: Done
assignee:
  - '@agent'
created_date: '2026-07-06 03:12'
updated_date: '2026-07-06 03:34'
labels: []
dependencies: []
references:
  - feature/task-39-dark-theme-design-system
priority: high
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The app currently has zero styling -- every component (WeeklyCalendar, MorningProjection, Scoreboard, Portfolio, Brackets, ClientAdmin, UserSwitcher) renders as plain unstyled HTML with only occasional inline style for basic layout (flex gaps, a selection border). SPEC.md never specifies a design system, but the five wireframe reference images in backlog/backlog/assets/wireframes/ (games-view.png, consultant-view.png, consultant-view-2.png, admin-view-1.png, drafting-view.png) all consistently depict a dark-theme, card-based dashboard aesthetic. This task applies that inferred style guide as the app's default (and only, for now) theme.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A shared style foundation exists (global CSS / theme file) applied app-wide via a single import, not per-component ad hoc styles
- [x] #2 Dark theme is the default: near-black page background, card panels in a slightly lighter dark gray with a subtle 1px border and rounded corners, matching the wireframes
- [x] #3 Semantic colors match the wireframes: blue accent for selection/links/badges (e.g. current-user pill, selected client row, today marker), green for positive/on-time/success states, red for negative/risky/missing states, amber/orange for in-progress/warning/late states
- [x] #4 Primary actions use a solid high-contrast pill button (e.g. Submit entry, Draft Priya); secondary actions use an outlined ghost pill button (e.g. + Add client, Assign)
- [x] #5 Headings are bold and legible against the dark background; secondary/meta text (timestamps, hints) uses a muted gray, matching the wireframes' text hierarchy
- [x] #6 Every existing screen (weekly calendar, morning projection, scoreboard/box score, clients and assignments, portfolio/exchange, brackets) is restyled consistently -- no screen is left in the old unstyled state
- [x] #7 Existing frontend unit tests continue to pass (queries by role/label/text, not by removed default styling)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-39 (Apply a dark-theme design system across the app):

Style guide inferred from the five wireframe images (backlog/backlog/assets/wireframes/):
- Page background: near-black (approx #0f1115). Card panels: a slightly lighter
  dark gray (approx #1a1d24) with a subtle 1px border (approx #2a2e37) and
  8-12px rounded corners.
- Text: off-white headings (approx #f2f3f5), muted gray secondary/meta text
  (approx #9aa0ab).
- Semantic colors: blue accent (approx #3b82f6) for selection/links/badges;
  green (approx #22c55e) for positive/on-time/success; red (approx #ef4444)
  for negative/risky/missing; amber (approx #f59e0b) for in-progress/warning/
  late states.
- Buttons: solid high-contrast pill (white bg, dark text) for primary actions
  (Submit entry, Project); outlined ghost pill (transparent bg, light border,
  light text) as the default/secondary style for every other button.
- Inputs/selects/textareas: dark surface background, subtle border, rounded
  corners, light text.

Implementation approach: plain CSS with custom properties (design tokens),
no new dependency (Tailwind/styled-components would be new scope beyond
what a small app like this needs, and this repo has zero CSS deps today).

1. New file frontend/src/theme.css:
   - :root custom properties for the palette above (--bg, --surface,
     --border, --text, --text-muted, --accent-blue, --accent-green,
     --accent-red, --accent-amber, --radius, spacing scale).
   - Base element styles: html/body (background, color, font-family,
     color-scheme: dark), h1-h4 (bold, off-white), p/span default text,
     table/th/td (border-color, spacing), input/select/textarea (dark
     surface, border, radius, padding), button (default = outlined ghost
     pill: transparent bg, 1px solid border, radius, padding, pointer
     cursor, hover state).
   - Reusable utility classes: .card (surface bg, border, radius, padding,
     margin-bottom -- applied to every top-level <section>), .pill-btn
     and .pill-btn--primary (solid high-contrast variant, applied only to
     the specific primary-action buttons named in AC #4), .badge with
     modifiers --info/--success/--danger/--warning (small rounded pill,
     colored background at low opacity + matching text color), .text-muted,
     .is-selected (blue-tinted background + left border, replacing the
     inline border logic in WeeklyCalendar/Scoreboard's tile selection),
     .table (consistent table styling for Scoreboard's box score).

2. Single import point (AC #1): import './theme.css' once in
   frontend/src/main.tsx, before <App /> renders -- every component picks
   up the cascade with no per-component CSS imports.

3. frontend/index.html: add <meta name=color-scheme content=dark'> so
   native form controls (date pickers, etc.) also render dark by default.

4. Per-component className changes (additive only -- no text content,
   aria-label, or DOM structure that existing tests query by is changed):
   - App.tsx: wrap <main> in className='app-shell' (max-width, centered,
     page padding).
   - Every top-level component's outer <section> (BackendStatus's <p>,
     WeeklyCalendar, MorningProjection, Scoreboard, Portfolio, Brackets,
     ClientAdmin, UserSwitcher's <label>) gets className='card'.
   - WeeklyCalendar.tsx: day-tile <button> gets className='day-tile' plus
     conditional 'is-selected'; the inline style={{border, padding,
     textAlign}} block is removed (replaced by the CSS class) -- no test
     asserts on this inline style (confirmed by grep), so this is safe.
     Status label span gets a conditional badge class from STATUS_LABELS'
     key (logged->badge--success, late->badge--warning,
     missing->badge--danger, pending->badge (neutral/muted)). 'Submit
     entry' button gets className='pill-btn pill-btn--primary'.
   - MorningProjection.tsx: status label span gets a conditional badge
     class from ClientStatus (locked-in->badge--success,
     missed-late/missed-not-projected->badge--danger, open->badge, neutral
     style). 'Project' button gets className='pill-btn pill-btn--primary'.
   - Scoreboard.tsx: game-tile <button> gets className='game-tile' plus
     conditional 'is-selected'; inline style block removed (no test
     depends on it, same as WeeklyCalendar). The 'In progress - hidden'
     label gets className='badge badge--warning'; 'Final - <date>' gets a
     neutral/muted class. TeamTable's <table> gets className='table'.
     checkmark() output spans get a conditional class (checked ->
     text-success, dash -> text-muted) via a small className helper
     rather than changing the glyph itself (preserves existing
     checkmark()-based assertions).
   - Portfolio.tsx: pct() output (movement/gain percentages) gets a
     conditional class (positive -> text-success, negative -> text-danger)
     via a small wrapper span, not by changing the numeric text itself
     (preserves existing getByText(/\+14%/) style assertions). Table gets
     className='table'.
   - Brackets.tsx: matchup <li> gets className='card' styling for each
     row; the existing inline style={{fontWeight}} winner-highlighting is
     left exactly as-is (Brackets.test.tsx asserts
     .style.fontWeight directly -- replacing it with a class would break
     that assertion under AC #7's 'existing tests continue to pass', so
     this one inline style is an intentional, documented exception).
   - ClientAdmin.tsx: selected client list item gets conditional
     className='is-selected'; archived clients get className='text-muted'
     (replacing no existing inline style -- there is none today, this is
     additive); '+ Add client' and 'Assign' buttons get
     className='pill-btn' (ghost, i.e. no --primary modifier, matching
     AC #4's example of these as secondary actions); 'Remove' (x) button
     stays a plain icon-style button (small, ghost, already covered by the
     button base style).
   - UserSwitcher.tsx: wrapping <label> gets className='card
     user-switcher' for a compact pill-like top-bar treatment matching the
     wireframe's small corner badge.

5. AC #7 verification: run the full existing frontend test suite after
   every className/CSS change with zero test-file edits required, since
   every change is additive (new className props) or removes an inline
   style with no corresponding test assertion (confirmed by grep across
   all *.test.tsx files for '.style.' and 'border' before writing any
   code). The one exception (Brackets.tsx's fontWeight inline style) is
   deliberately left untouched, not removed.

6. Explicit scope boundaries (to avoid AC creep beyond what was asked):
   - No new UI elements are invented beyond what already exists (e.g. no
     new avatar-circle markup for ClientAdmin/Scoreboard, even though the
     wireframes show them) -- this task restyles what exists; adding new
     visual elements not backed by an AC is out of scope and would need
     its own follow-up task if wanted.
   - No dark/light theme toggle -- AC #2 says dark is the default (and,
     per the task description, 'the only, for now') theme; no toggle
     mechanism is built.
   - No new npm dependency (CSS framework/CSS-in-JS library) -- plain CSS
     custom properties are sufficient for this scope and match the
     project's existing zero-frontend-dependency footprint.

Tests:
- No new test files -- this is a pure visual/CSS task with no new
  behavior. AC #7 is verified by running the existing full suite
  (frontend/src/*.test.tsx) unchanged and confirming 100% pass, plus a
  manual pass in a running dev server (per CLAUDE.md's UI-change testing
  guidance) to visually confirm every screen against the inferred style
  guide and wireframes.
- e2e suite (e2e/tests/*.spec.ts) re-run unchanged to confirm no
  className change broke any Playwright selector (all existing e2e tests
  select by role/label/text, not CSS classes, per a grep check before
  coding).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW -- PASSED (0 blocking, 1 minor): all six specific claims verified accurate against actual code (Brackets.test.tsx inline-style assertion, WeeklyCalendar/Scoreboard tile-selection tests, Portfolio percentage text-node matching, e2e selector safety, structural querySelector safety). Minor: the plan's grep sweep should also have covered querySelector/container patterns, not just .style./border -- re-verified by the reviewer directly, no gap found in practice. Full test suite re-run remains the real backstop as planned.

Implementation notes for task-39 (Apply a dark-theme design system across the app):

What was implemented:
- New frontend/src/theme.css: CSS custom properties for the full palette
  (background, surface, border, text/text-muted, blue/green/red/amber
  accents), base element styles (html/body, headings, table, button,
  input/select/textarea), and reusable utility classes (.card, .pill-btn
  + --primary modifier, .badge + --info/--success/--danger/--warning
  modifiers, .text-muted/.text-success/.text-danger, .day-tile/.game-tile
  + .is-selected, .table, .app-shell, .user-switcher).
- Single import point: theme.css is imported once in main.tsx (AC #1).
- frontend/index.html: added <meta name=color-scheme content=dark> so
  native form controls also render dark.
- Every existing component (App, BackendStatus, UserSwitcher, ClientAdmin,
  WeeklyCalendar, MorningProjection, Scoreboard, Portfolio, Brackets) got
  additive className props wiring its existing structure into the shared
  classes -- no text content, aria-label, or DOM structure was changed.

Key technical decisions:
- Plain CSS with custom properties, no new npm dependency -- a CSS
  framework or CSS-in-JS library would be new scope beyond what this
  small app's existing zero-frontend-dependency footprint needs.
- WeeklyCalendar.tsx and Scoreboard.tsx's inline style={{border, padding,
  textAlign}} tile-selection logic was replaced by .day-tile/.game-tile +
  .is-selected classes (confirmed via grep, and independently re-verified
  by the hostile plan review, that no test asserts on that inline style).
- Brackets.tsx's inline style={{fontWeight}} winner-highlighting was
  deliberately left untouched: Brackets.test.tsx asserts
  .style.fontWeight directly on the DOM node, so converting it to a class
  would have broken that assertion under AC #7. This is the one
  intentional exception to the otherwise className-only approach,
  called out explicitly in the plan and confirmed correct by the hostile
  review.
- Scoreboard's checkmark() and Portfolio's pct() text-generating helpers
  were left untouched; new small wrapper components (Checkmark, Pct) add
  a conditional className around their existing text output rather than
  changing the text itself, preserving every existing getByText(...)-
  style test assertion (verified: Testing Library's getByText matches
  the innermost node containing the text, so wrapping in a span does not
  break an exact-text query).

Integration points:
- No new npm dependencies (frontend or backend).
- No backend changes -- this is a pure frontend/CSS task.
- Future components should apply the same shared classes (.card,
  .pill-btn, .badge--*, .text-muted/.text-success/.text-danger) rather
  than reintroducing ad hoc inline styles, now that the pattern exists.

Testing coverage:
- No new test files -- this is a pure visual/CSS task with no new
  behavior, per the plan.
- Full existing frontend suite: 42 of 42 passed, with zero test-file
  edits required (as planned and confirmed by the hostile review).
- Full existing e2e suite: 14 of 14 passed.
- Lint (eslint) and build (tsc + vite build) both clean; the production
  build now emits a real CSS bundle (frontend/dist/assets/index-*.css)
  where none existed before.
- Manual visual verification: started the dev server and backend, took a
  full-page screenshot as a seeded admin+consultant user, and confirmed
  every screen (games/box-score, portfolio/exchange, brackets, morning
  projection, clients and assignments, weekly calendar) renders with the
  near-black background, dark card panels, blue selection highlighting,
  green/red/amber semantic badges, and solid-vs-ghost pill buttons
  matching the wireframe reference images. Zero console errors.

Future considerations:
- No dark/light theme toggle exists (out of scope per the task
  description -- dark is 'the only, for now' theme).
- No new visual elements (e.g. avatar-circle initials shown in the
  wireframes for ClientAdmin/drafting screens) were added -- this task
  restyled what already exists; new UI elements not backed by an AC
  would need their own follow-up task.
- task-40 (real authentication) will eventually replace UserSwitcher's
  dev-mode dropdown; the .user-switcher/.card styling applied here should
  carry over to whatever login UI replaces it.

CODE REVIEW: Approved with 1 self-caught minor, fixed before approval -- day-tile/game-tile classNames were semantically wrong when reused on ClientAdmin's client-selection buttons (they are not days or games); consolidated to a single generic .tile class used consistently by WeeklyCalendar, Scoreboard, and ClientAdmin. Re-ran full test/lint/build suite after the rename: 42 frontend tests, lint, and build all still clean.
<!-- SECTION:NOTES:END -->
