/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    // Pin a fixed, known, non-UTC timezone so tests that assert local-time
    // interpretation of UTC-instant timestamps (e.g. the WeeklyCalendar
    // perfect-day check) produce the same result regardless of the runner's
    // ambient timezone -- a UTC-default CI runner would make correct vs.
    // buggy timestamp parsing indistinguishable.
    env: {
      TZ: 'America/New_York',
    },
  },
});
