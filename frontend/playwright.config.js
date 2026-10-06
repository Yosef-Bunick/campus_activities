import { defineConfig, devices } from '@playwright/test';

// Phone-sized smoke test (architecture §4: e2e/ runs at a phone viewport by
// default). Starts its own API (SQLite e2e.db, local dev sign-in) and the
// production build via `vite preview`, so it never touches dev.db.
const PYTHON = process.env.PYTHON || 'python';

export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'retain-on-failure',
    channel: process.env.PW_CHANNEL || undefined, // e.g. "chrome" to reuse an installed Chrome
  },
  projects: [{ name: 'phone', use: { ...devices['Pixel 7'] } }],
  webServer: [
    {
      command: `${PYTHON} -m alembic upgrade head && ${PYTHON} -m app.seed && ${PYTHON} -m uvicorn app.main:app --port 8000`,
      cwd: '../backend',
      url: 'http://localhost:8000/health',
      env: {
        DATABASE_URL: 'sqlite:///./e2e.db',
        DEV_LOGIN: '1',
        FRONTEND_ORIGIN: 'http://localhost:4173',
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'npm run build && npm run preview -- --port 4173 --strictPort',
      url: 'http://localhost:4173',
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
