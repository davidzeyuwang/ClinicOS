import { defineConfig, devices } from "@playwright/test";

const backendCommand = "bash ./scripts/start-backend.sh";

export default defineConfig({
  testDir: "./frontend/tests/e2e",
  testIgnore: ["**/deployed-workflow.spec.ts", "**/debug-room.spec.ts"],
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    viewport: { width: 1280, height: 900 },
  },
  webServer: {
    command: backendCommand,
    url: "http://127.0.0.1:8000/health",
    reuseExistingServer: true,
    timeout: 120 * 1000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
