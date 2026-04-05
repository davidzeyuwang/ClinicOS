/**
 * Shared auth + RBAC + multi-tenancy E2E suite.
 *
 * Covers: AUTH-00 (clinic registration), AUTH-01 (JWT login/me),
 *         AUTH-02 (role enforcement), MT-01/MT-02 (tenant isolation).
 *
 * Two thin wrappers provide environment adapters:
 *   local-smoke.spec.ts  — resetLocalData before all, noop teardown
 *   prod-smoke.spec.ts   — warmup setup, Supabase REST teardown
 */

import { test, expect, type APIRequestContext, type Page } from "@playwright/test";
import { authHeaders } from "../helpers";

// ── Public types ──────────────────────────────────────────────────────────────

export interface AuthEnv {
  suiteName: string;
  /** The admin user's email address (used as login identifier). */
  adminEmail: string;
  adminPassword: string;

  /**
   * Unique suffix per run to avoid slug/username collisions between runs.
   * Example: Date.now().toString().slice(-6)
   */
  runSuffix: string;

  /** Reset state and warm up the server before the suite runs. */
  setup: (request: APIRequestContext) => Promise<void>;

  /**
   * Clean up resources created during the suite.
   * `created` holds slugs of clinics registered during the tests.
   */
  teardown: (request: APIRequestContext, created: AuthCreated) => Promise<void>;

  /**
   * Create a frontdesk user for RBAC tests via a test endpoint.
   * Returns auth headers for that user.
   * On prod this is a no-op (test returns null → RBAC test is skipped).
   */
  createFrontdeskUser: (
    request: APIRequestContext,
    suffix: string,
  ) => Promise<Record<string, string> | null>;

  /**
   * Whether this environment enforces per-clinic data isolation.
   * Set to false for single-tenant Supabase prod (patients table has no clinic_id).
   * Defaults to true (local SQLite with proper multi-tenancy).
   */
  supportsTenantIsolation?: boolean;
}

export interface AuthCreated {
  /** Clinic slugs registered during this test run (for teardown). */
  slugs: string[];
  /** Clinic IDs registered during this test run (for prod Supabase cleanup). */
  clinicIds: string[];
}

// ── Suite factory ─────────────────────────────────────────────────────────────

export function registerAuthTests(env: AuthEnv): void {
  test.describe(env.suiteName, () => {
    const created: AuthCreated = { slugs: [], clinicIds: [] };

    test.beforeAll(async ({ request }) => {
      await env.setup(request);
    });

    test.afterAll(async ({ request }) => {
      await env.teardown(request, created);
    });

    // ── AUTH-01: Login and JWT ─────────────────────────────────────────────────

    test("POST /auth/login with valid credentials returns JWT with all fields", async ({
      request,
    }) => {
      const r = await request.post("/prototype/auth/login", {
        data: { email: env.adminEmail, password: env.adminPassword },
      });
      expect(r.ok(), `login failed: ${await r.text()}`).toBeTruthy();
      const body = await r.json();
      expect(body.access_token, "access_token missing").toBeTruthy();
      expect(body.token_type).toBe("bearer");
      expect(body.role).toBe("admin");
      expect(body.clinic_id, "clinic_id missing").toBeTruthy();
      expect(body.user_id, "user_id missing").toBeTruthy();
      expect(body.display_name, "display_name missing").toBeTruthy();
    });

    test("POST /auth/login with wrong password returns 401", async ({ request }) => {
      const r = await request.post("/prototype/auth/login", {
        data: { email: env.adminEmail, password: "totally-wrong-pass" },
      });
      expect(r.status()).toBe(401);
    });

    test("POST /auth/login with unknown email returns 401", async ({ request }) => {
      const r = await request.post("/prototype/auth/login", {
        data: { email: `nobody-${env.runSuffix}@nowhere.example`, password: "irrelevant" },
      });
      expect(r.status()).toBe(401);
    });

    test("POST /auth/login with username alias returns JWT", async ({ request }) => {
      const fdHeaders = await env.createFrontdeskUser(request, `alias-${env.runSuffix}`);
      if (!fdHeaders) {
        console.log("  ⚠ createFrontdeskUser not available in this env — username alias test skipped");
        return;
      }
      // createFrontdeskUser creates user with email=`frontdesk-alias-<suffix>@local.test`
      // Login using username field (alias) — backend accepts both email and username
      const r = await request.post("/prototype/auth/login", {
        data: { username: `frontdesk-alias-${env.runSuffix}@local.test`, password: "front123!" },
      });
      expect(r.ok(), `username alias login failed: ${await r.text()}`).toBeTruthy();
      expect((await r.json()).access_token, "access_token missing").toBeTruthy();
    });

    test("POST /auth/login without email or username returns 422", async ({ request }) => {
      const r = await request.post("/prototype/auth/login", {
        data: { password: "irrelevant" },
      });
      expect(r.status(), "expected 422 when neither email nor username provided").toBe(422);
    });

    // ── AUTH-01: GET /auth/me ──────────────────────────────────────────────────

    test("GET /auth/me with valid token returns correct user object", async ({ request }) => {
      const loginR = await request.post("/prototype/auth/login", {
        data: { email: env.adminEmail, password: env.adminPassword },
      });
      const { access_token } = await loginR.json();

      const r = await request.get("/prototype/auth/me", {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      expect(r.ok(), await r.text()).toBeTruthy();
      const body = await r.json();
      expect(body.email).toBe(env.adminEmail);
      expect(body.role).toBe("admin");
      expect(body.clinic_id, "clinic_id missing from /auth/me").toBeTruthy();
    });

    test("GET /auth/me without token returns 401", async ({ request }) => {
      const r = await request.get("/prototype/auth/me");
      expect(r.status()).toBe(401);
    });

    // ── AUTH-01: Protected endpoint guard ─────────────────────────────────────

    test("GET /patients without token returns 401", async ({ request }) => {
      const r = await request.get("/prototype/patients");
      expect(r.status()).toBe(401);
    });

    test("GET /patients with valid token returns patient list", async ({ request }) => {
      const r = await request.get("/prototype/patients", { headers: authHeaders() });
      expect(r.ok(), await r.text()).toBeTruthy();
      const body = await r.json();
      expect(Array.isArray(body.patients), "patients array missing").toBeTruthy();
    });

    // ── AUTH-02: Role-based access control ────────────────────────────────────

    test("admin role can call POST /admin/service-types", async ({ request }) => {
      const r = await request.post("/prototype/admin/service-types", {
        data: { name: `RBACSmoke-${env.runSuffix}`, description: "RBAC smoke type" },
        headers: authHeaders(),
      });
      expect(r.ok(), `admin service-type create failed: ${await r.text()}`).toBeTruthy();
    });

    test("frontdesk role cannot call POST /admin/service-types (403)", async ({ request }) => {
      const fdHeaders = await env.createFrontdeskUser(request, env.runSuffix);
      if (!fdHeaders) {
        console.log("  ⚠ createFrontdeskUser not supported in this env — RBAC test skipped");
        return;
      }
      const r = await request.post("/prototype/admin/service-types", {
        data: { name: `FDAttempt-${env.runSuffix}`, description: "should fail" },
        headers: fdHeaders,
      });
      expect(r.status(), "expected 403 for frontdesk role").toBe(403);
    });

    // ── AUTH-00: Clinic self-registration ──────────────────────────────────────

    test("POST /auth/register-clinic creates new clinic and admin user", async ({ request }) => {
      const slug = `auth-reg-${env.runSuffix}`;
      created.slugs.push(slug);
      const r = await request.post("/prototype/auth/register-clinic", {
        data: {
          clinic_name: `Auth Reg Clinic ${env.runSuffix}`,
          slug,
          admin_email: `reg-admin-${env.runSuffix}@auth.test`,
          admin_password: "Reg123!",
          admin_display_name: `Reg Admin ${env.runSuffix}`,
        },
      });
      expect(r.ok(), `register-clinic failed: ${await r.text()}`).toBeTruthy();
      const body = await r.json();
      expect(body.clinic_id, "clinic_id missing").toBeTruthy();
      expect(body.user_id, "user_id missing").toBeTruthy();
      created.clinicIds.push(body.clinic_id);
    });

    test("POST /auth/register-clinic with duplicate slug returns 409", async ({ request }) => {
      const slug = `dup-slug-${env.runSuffix}`;
      created.slugs.push(slug);
      const base = {
        clinic_name: `Dup Clinic ${env.runSuffix}`,
        slug,
        admin_password: "Pass123!",
      };
      const r1 = await request.post("/prototype/auth/register-clinic", {
        data: { ...base, admin_email: `dup1-${env.runSuffix}@dup.test` },
      });
      expect(r1.ok(), await r1.text()).toBeTruthy();
      created.clinicIds.push((await r1.json()).clinic_id);

      const r2 = await request.post("/prototype/auth/register-clinic", {
        data: { ...base, admin_email: `dup2-${env.runSuffix}@dup.test` },
      });
      expect(r2.status(), "expected 409 for duplicate slug").toBe(409);
    });

    // ── MT-01 + MT-02: Multi-tenancy isolation ────────────────────────────────

    test("tenant isolation: clinic B cannot access clinic A patients", async ({ request }) => {
      if (env.supportsTenantIsolation === false) {
        console.log("  ⚠ Tenant isolation not enforced in this env (single-tenant Supabase) — skipped");
        return;
      }
      // Create patient in Clinic A
      const ptR = await request.post("/prototype/patients", {
        data: {
          first_name: "MT",
          last_name: "IsoA",
          date_of_birth: "1990-01-01",
          phone: "555-0000",
        },
        headers: authHeaders(),
      });
      expect(ptR.ok(), await ptR.text()).toBeTruthy();
      const patientId = (await ptR.json()).patient_id;

      // Register Clinic B
      const slug = `mt-iso-${env.runSuffix}`;
      created.slugs.push(slug);
      const regR = await request.post("/prototype/auth/register-clinic", {
        data: {
          clinic_name: `MT Iso Clinic ${env.runSuffix}`,
          slug,
          admin_email: `mt-admin-${env.runSuffix}@mt.test`,
          admin_password: "MTPass123!",
          admin_display_name: "MT Admin",
        },
      });
      expect(regR.ok(), await regR.text()).toBeTruthy();
      created.clinicIds.push((await regR.json()).clinic_id);

      // Login as Clinic B admin
      const loginR = await request.post("/prototype/auth/login", {
        data: { email: `mt-admin-${env.runSuffix}@mt.test`, password: "MTPass123!" },
      });
      const { access_token: bToken } = await loginR.json();
      const bHeaders = { Authorization: `Bearer ${bToken}` };

      // Clinic B sees 0 patients
      const listR = await request.get("/prototype/patients", { headers: bHeaders });
      expect(listR.ok(), await listR.text()).toBeTruthy();
      expect(
        (await listR.json()).patients.length,
        "Clinic B must see 0 patients (tenant isolation)",
      ).toBe(0);

      // Clinic B cannot fetch Clinic A's patient by ID
      const getR = await request.get(`/prototype/patients/${patientId}`, { headers: bHeaders });
      expect(getR.status(), "expected 404 — patient belongs to different clinic").toBe(404);

      console.log("  ✓ Tenant isolation: clinic B cannot access clinic A patients");
    });

    // ── UI: Login modal behavior ──────────────────────────────────────────────

    test("login modal appears when localStorage has no token", async ({ page }) => {
      await page.goto("/ui/index.html");
      await page.evaluate(() => localStorage.removeItem("clinicos_token"));
      await page.reload();
      await expect(page.locator("#login-modal"), "login modal should be visible").toBeVisible({
        timeout: 10_000,
      });
    });

    test("login modal: wrong password shows error message", async ({ page }) => {
      await _clearTokenAndReload(page);
      await page.locator("#login-username").fill(env.adminEmail);
      await page.locator("#login-password").fill("wrong-password-for-smoke-test");
      await page.getByRole("button", { name: /sign in/i }).click();
      await expect(page.locator("#login-error"), "error message should appear").toBeVisible({
        timeout: 5_000,
      });
    });

    test("login modal: correct credentials hide modal and show ops board", async ({ page }) => {
      await _clearTokenAndReload(page);
      await page.locator("#login-username").fill(env.adminEmail);
      await page.locator("#login-password").fill(env.adminPassword);
      await page.getByRole("button", { name: /sign in/i }).click();
      await expect(page.locator("#login-modal"), "login modal should hide").toBeHidden({
        timeout: 10_000,
      });
      await expect(
        page.getByTestId("tab-ops"),
        "ops board tab should be visible after login",
      ).toBeVisible({ timeout: 10_000 });
    });

    test("self-service clinic owner can register clinic and create frontdesk account from admin UI", async ({ page }) => {
      const slug = `ui-auth-${env.runSuffix}`;
      const adminEmail = `ui-admin-${env.runSuffix}@auth.test`;
      const staffEmail = `ui-front-${env.runSuffix}@auth.test`;
      created.slugs.push(slug);

      await _clearTokenAndReload(page);
      await page.getByTestId("open-register-clinic").click();
      await expect(page.locator("#register-modal")).toBeVisible({ timeout: 5_000 });

      await page.getByTestId("register-clinic-name").fill(`UI Auth Clinic ${env.runSuffix}`);
      await page.getByTestId("register-clinic-slug").fill(slug);
      await page.getByTestId("register-admin-name").fill(`UI Owner ${env.runSuffix}`);
      await page.getByTestId("register-admin-email").fill(adminEmail);
      await page.getByTestId("register-admin-username").fill(`owner${env.runSuffix}`);
      await page.getByTestId("register-admin-password").fill("UiOwner123!");
      await page.getByTestId("register-clinic-submit").click();

      await expect(page.locator("#register-modal")).toBeHidden({ timeout: 10_000 });
      await expect(page.getByTestId("tab-admin")).toBeVisible({ timeout: 10_000 });

      const clinicId = await page.evaluate(() => {
        const raw = localStorage.getItem("clinicos_user");
        return raw ? JSON.parse(raw).clinic_id : null;
      });
      if (clinicId) created.clinicIds.push(clinicId);

      await page.getByTestId("tab-admin").click();
      await page.getByTestId("user-display-name-input").fill("Front Desk UI");
      await page.getByTestId("user-email-input").fill(staffEmail);
      await page.getByTestId("user-username-input").fill(`front${env.runSuffix}`);
      await page.getByTestId("user-role-input").selectOption("frontdesk");
      await page.getByTestId("user-password-input").fill("Front123!");
      await page.getByTestId("add-user-button").click();

      await expect(
        page.getByTestId(`users-list-item-${staffEmail.replace(/[^a-zA-Z0-9_-]/g, "-")}`),
      ).toBeVisible({ timeout: 10_000 });
    });
  });
}

// ── Private helpers ───────────────────────────────────────────────────────────

async function _clearTokenAndReload(page: Page) {
  await page.goto("/ui/index.html");
  await page.evaluate(() => localStorage.removeItem("clinicos_token"));
  await page.reload();
  await expect(page.locator("#login-modal")).toBeVisible({ timeout: 10_000 });
}
