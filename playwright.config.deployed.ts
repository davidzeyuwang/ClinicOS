import { defineConfig, devices } from "@playwright/test";

// Config for testing deployed application at https://clinicos-psi.vercel.app
export default defineConfig({
  testDir: "./frontend/tests/e2e",
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "https://clinicos-psi.vercel.app",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    viewport: { width: 1280, height: 900 },
  },
  // No webServer - testing deployed app
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
