import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./frontend/tests/e2e",
  testMatch: ["**/deployed-workflow.spec.ts"],
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "https://clinicos-psi.vercel.app",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1280, height: 900 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
