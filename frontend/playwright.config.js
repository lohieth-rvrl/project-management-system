import { defineConfig } from "@playwright/test";

// Starts the Django API (fresh SQLite database with demo data) and the Vite dev server.
// In CI run `npx playwright install --with-deps chromium` first. Locally you can point
// PW_CHROMIUM_PATH at an existing Chromium binary instead.
const chromium = process.env.PW_CHROMIUM_PATH;
const sqlite = process.env.E2E_SQLITE || "/var/tmp/pms-e2e.sqlite3";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  workers: 1,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    launchOptions: chromium ? { executablePath: chromium } : {},
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `rm -f ${sqlite} && python manage.py migrate --noinput -v0 && python manage.py seed_demo && python manage.py runserver 8000 --noreload`,
      cwd: "../backend",
      url: "http://localhost:8000/api/health/",
      timeout: 120_000,
      reuseExistingServer: false,
      env: { SQLITE_PATH: sqlite, DJANGO_DEBUG: "1" },
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
