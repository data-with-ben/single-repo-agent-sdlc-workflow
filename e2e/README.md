# E2E

Playwright end-to-end tests.

## Setup

```bash
npm install
npx playwright install
```

## Run

```bash
npm run test:e2e
```

The Playwright `webServer` config starts the frontend dev server (`../frontend`) automatically. Tests live in `tests/` as `<feature-name>.spec.ts`. Videos, traces, and screenshots are written to `test-results/`.
