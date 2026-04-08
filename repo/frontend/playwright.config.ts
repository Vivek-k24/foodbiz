import { defineConfig, devices } from "@playwright/test";

const frontendDir = "./";
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  reporter: [["list"], ["html", { open: "never" }]],
  outputDir: "./test-results",
  use: {
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "pnpm --filter web-ordering exec vite preview --host 127.0.0.1 --port 5173",
      cwd: frontendDir,
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "pnpm --filter dashboard exec vite preview --host 127.0.0.1 --port 5174",
      cwd: frontendDir,
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "pnpm --filter kitchen-display exec vite preview --host 127.0.0.1 --port 5175",
      cwd: frontendDir,
      url: "http://127.0.0.1:5175",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "pnpm --filter restaurant-site exec vite preview --host 127.0.0.1 --port 5176",
      cwd: frontendDir,
      url: "http://127.0.0.1:5176",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
