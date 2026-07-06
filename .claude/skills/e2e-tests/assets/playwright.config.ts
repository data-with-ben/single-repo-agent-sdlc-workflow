import { defineConfig, devices } from '@playwright/test';

// Backend venv layout differs by OS: Scripts/python.exe on Windows,
// bin/python everywhere else.
const backendPython =
  process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  use: {
    baseURL: 'http://localhost:5173',
    video: 'on',
    trace: 'on',
    screenshot: 'on',
  },

  outputDir: './test-results',

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // e2e tests that exercise real API calls need the backend running too,
  // not just the frontend -- otherwise every authenticated fetch fails and
  // tests can only cover client-only rendering. Runs migrations + seed data
  // against a dedicated DATABASE_URL so it never touches a developer's local
  // dev database.
  webServer: [
    {
      command: `cd ../backend && ${backendPython} -m alembic upgrade head && ${backendPython} -m app.seed && ${backendPython} -m uvicorn app.main:app --port 8000`,
      url: 'http://localhost:8000/',
      reuseExistingServer: !process.env.CI,
      env: { DATABASE_URL: 'sqlite:///./e2e_test.db' },
    },
    {
      command: 'npm --prefix ../frontend run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
  ],
});
