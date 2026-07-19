import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8080",
    trace: "on-first-retry",
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: "pnpm exec concurrently --kill-others-on-fail --names api,portal,dashboard \"conda run -n codex-agents uvicorn apps.api.src.main:app --host 127.0.0.1 --port 8000 --reload\" \"pnpm --dir apps/founder-portal exec vite --host 127.0.0.1 --port 8080\" \"pnpm --dir apps/vc-dashboard exec vite --host 127.0.0.1 --port 8081\"",
    url: "http://localhost:8080",
    reuseExistingServer: !process.env.CI,
    timeout: 180000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
