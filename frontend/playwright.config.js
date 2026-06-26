import { defineConfig, devices } from "@playwright/test"

const backendUrl = "http://127.0.0.1:8000"
const frontendUrl = "http://127.0.0.1:5173"
const backendCommand =
  process.env.PLAYWRIGHT_BACKEND_COMMAND ||
  "py -3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: frontendUrl,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: backendCommand,
      cwd: "..",
      url: `${backendUrl}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        DATABASE_URL: "sqlite:///./quoteops-e2e.db",
        OPENAI_API_KEY: "",
        ALLOWED_ORIGINS: frontendUrl,
      },
    },
    {
      command: "node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173",
      url: frontendUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        VITE_API_BASE_URL: backendUrl,
      },
    },
  ],
})
