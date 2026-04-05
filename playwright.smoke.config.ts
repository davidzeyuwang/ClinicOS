/**
 * Playwright config for production smoke tests.
 *
 * Requires prod to be seeded first:
 *   python3 scripts/seed_prod.py
 *
 * Run:
 *   npx playwright test --config=playwright.smoke.config.ts
 */
import { defineConfig, devices } from "@playwright/test";
import { readFileSync } from "fs";
import { resolve } from "path";

// Load .env.prod so tests can use SUPABASE_URL/KEY for cleanup
try {
  const content = readFileSync(resolve(__dirname, ".env.prod"), "utf-8");
  for (const line of content.split("\n")) {
    const m = line.match(/^([A-Z_][A-Z0-9_]*)\s*=\s*(.+)$/);
    if (m) process.env[m[1]] = m[2].trim().replace(/^["'](.*)["']$/, "$1");
  }
} catch {
  // .env.prod not present — SUPABASE_URL/KEY must already be in process.env
}

export default defineConfig({
  testDir: "./frontend/tests/e2e",
  testMatch: ["**/prod-smoke.spec.ts"],
  globalSetup: "./frontend/tests/global-setup.ts",
  fullyParallel: false,
  retries: 1,
  timeout: 240_000,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || "https://clinicos-psi.vercel.app",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1280, height: 900 },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
