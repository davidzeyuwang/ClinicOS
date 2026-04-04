/**
 * Playwright global setup — authenticates as the test admin and saves:
 *   1. playwright/.auth/token.txt  — raw JWT for request-context API calls
 *   2. playwright/.auth/admin-state.json  — browser localStorage state for page tests
 */
import { chromium, request } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:8000";
const TEST_USERNAME = "admin@test.clinicos.local";
const TEST_PASSWORD = "test1234";
const AUTH_DIR = "playwright/.auth";

export default async function globalSetup() {
  // 1. Obtain JWT via direct API call (no browser needed)
  const ctx = await request.newContext({ baseURL: BASE_URL });
  const resp = await ctx.post("/prototype/auth/login", {
    data: { username: TEST_USERNAME, password: TEST_PASSWORD },
  });
  if (!resp.ok()) {
    const body = await resp.text();
    throw new Error(`[global-setup] Login failed (${resp.status()}): ${body}`);
  }
  const { access_token } = await resp.json();
  await ctx.dispose();

  // 2. Persist token for request-context API calls in beforeEach/beforeAll
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  fs.writeFileSync(path.join(AUTH_DIR, "token.txt"), access_token, "utf-8");

  // 3. Set JWT in browser localStorage + save storageState for all page tests
  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL: BASE_URL });
  const page = await context.newPage();
  await page.goto("/ui/index.html");
  // Inject token into localStorage so initAuth() finds it on page load
  await page.evaluate(
    (token: string) => localStorage.setItem("clinicos_token", token),
    access_token,
  );
  await context.storageState({ path: path.join(AUTH_DIR, "admin-state.json") });
  await browser.close();

  // 4. Make token available as env var for helpers.ts during this process
  process.env.PW_AUTH_TOKEN = access_token;

  console.log("[global-setup] Auth token saved to playwright/.auth/");
}
