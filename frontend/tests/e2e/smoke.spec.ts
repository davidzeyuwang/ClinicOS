/**
 * Production Smoke Test — Full Clinic Workflow
 *
 * Covers every major feature end-to-end against the live deployed app.
 * Requires stable rooms/staff to be seeded first:
 *
 *   python3 scripts/seed_prod.py
 *
 * Run:
 *   npx playwright test --config=playwright.smoke.config.ts
 *
 * Cleanup: the test hard-deletes all created records via Supabase REST
 * in afterAll, so production stays clean after every run.
 */
import { test, expect, type Page, type APIRequestContext } from "@playwright/test";

// ── Constants ────────────────────────────────────────────────────────────────

/** Seeded by scripts/seed_prod.py */
const ROOM_CODE  = "C1";
const COPAY_AMT  = "45";

const RUN_SUFFIX = Date.now().toString().slice(-6);
const PT_FIRST   = "SmokeTest";
const PT_LAST    = RUN_SUFFIX;
const PT_FULL    = `${PT_FIRST} ${PT_LAST}`;
const PT_MRN     = `SMOKE${RUN_SUFFIX}`;

// ── Helpers ──────────────────────────────────────────────────────────────────

async function toast(page: Page, text: string) {
  await expect(page.getByTestId("toast")).toContainText(text, { timeout: 15_000 });
}

async function tab(page: Page, testId: string) {
  await page.getByTestId(testId).click();
}

/** Create patient via API and return patient_id. */
async function createPatient(request: APIRequestContext): Promise<string> {
  const r = await request.post("/prototype/patients", {
    data: {
      first_name: PT_FIRST,
      last_name:  PT_LAST,
      date_of_birth: "1985-06-15",
      phone: "555-9999",
      mrn: PT_MRN,
    },
  });
  if (!r.ok()) throw new Error(`createPatient failed: ${await r.text()}`);
  const p = await r.json();
  return p.patient_id;
}

/**
 * Hard-delete all smoke test records via Supabase REST.
 * Falls back to soft-delete via app API if env vars not set.
 */
async function cleanup(request: APIRequestContext, patientId: string) {
  const supaUrl = process.env.SUPABASE_URL;
  const supaKey = process.env.SUPABASE_SERVICE_KEY;

  if (supaUrl && supaKey) {
    const hdrs = {
      "apikey": supaKey,
      "Authorization": `Bearer ${supaKey}`,
      "Prefer": "return=minimal",
    };
    // Get visit IDs + room_ids for this patient
    const vr = await request.get(`${supaUrl}/rest/v1/visits?select=visit_id,room_id&patient_id=eq.${patientId}`, { headers: hdrs });
    const visits: Array<{ visit_id: string; room_id: string | null }> = await vr.json();
    if (visits.length) {
      const ids = visits.map(v => v.visit_id).join(",");
      await request.delete(`${supaUrl}/rest/v1/visit_treatments?visit_id=in.(${ids})`, { headers: hdrs });
      await request.delete(`${supaUrl}/rest/v1/visits?patient_id=eq.${patientId}`, { headers: hdrs });
      // Reset any rooms this patient occupied back to available
      const roomIds = [...new Set(visits.map(v => v.room_id).filter(Boolean))];
      for (const rid of roomIds) {
        await request.patch(
          `${supaUrl}/rest/v1/rooms?room_id=eq.${rid}`,
          { headers: { ...hdrs, "Content-Type": "application/json" }, data: { status: "available" } },
        );
      }
    }
    await request.delete(`${supaUrl}/rest/v1/patients?patient_id=eq.${patientId}`, { headers: hdrs });
    console.log(`  Cleaned up patient ${patientId} and ${visits.length} visit(s)`);
  } else {
    // Soft-delete fallback
    await request.delete(`/prototype/patients/${patientId}`);
    console.log(`  Soft-deleted patient ${patientId} (set SUPABASE_URL/KEY for hard delete)`);
  }
}

/** Ensure the smoke test room is available before the run. */
async function resetRoom(request: APIRequestContext) {
  const supaUrl = process.env.SUPABASE_URL;
  const supaKey = process.env.SUPABASE_SERVICE_KEY;
  if (!supaUrl || !supaKey) return;
  const hdrs = {
    "apikey": supaKey,
    "Authorization": `Bearer ${supaKey}`,
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
  };
  await request.patch(
    `${supaUrl}/rest/v1/rooms?code=eq.${ROOM_CODE}`,
    { headers: hdrs, data: { status: "available" } },
  );
  console.log(`  Reset room ${ROOM_CODE} to available`);
}

// ── Test ─────────────────────────────────────────────────────────────────────

test.describe("Prod smoke — full clinic workflow", () => {
  let patientId = "";

  test.beforeAll(async ({ request }) => {
    await resetRoom(request);
    patientId = await createPatient(request);
    console.log(`  Created patient ${PT_FULL} (${patientId})`);
  });

  test.afterAll(async ({ request }) => {
    if (patientId) await cleanup(request, patientId);
  });

  test("check-in → treatment → checkout → report → events → patient detail", async ({ page }) => {

    // ── 1. App loads ──────────────────────────────────────────────────────
    await page.goto("/ui/index.html");
    await expect(page.getByTestId("tab-ops")).toBeVisible({ timeout: 15_000 });

    // ── 2. Check in patient to Room C1 via autocomplete ───────────────────
    await tab(page, "tab-ops");
    const checkinBtn = page.getByTestId(`room-checkin-${ROOM_CODE}`);
    await expect(checkinBtn).toBeVisible({ timeout: 10_000 });
    await checkinBtn.click();

    // Type MRN so autocomplete finds exactly this patient
    await page.locator("#rc-search").fill(PT_MRN);
    await expect(page.locator("#rc-results")).toBeVisible({ timeout: 10_000 });
    await page.locator("#rc-results div").first().click();
    // Confirm patient was selected
    await expect(page.locator("#rc-selected")).toContainText(PT_FIRST, { timeout: 5_000 });

    await page.locator("#rc-staff").selectOption({ index: 0 });
    await page.getByRole("button", { name: "Check In & Start" }).click();
    await toast(page, "room assigned");

    // ── 3. Add treatment ──────────────────────────────────────────────────
    const visitRow = page.locator("#visits-list tr").filter({ hasText: PT_FULL });
    await expect(visitRow).toContainText("in_service", { timeout: 10_000 });
    await visitRow.getByRole("button", { name: /tx/i }).click();

    await expect(page.locator(".modal-bg")).toBeVisible({ timeout: 5_000 });
    await page.locator("#trt-mod").selectOption("E-stim");
    await page.locator("#trt-dur").fill("30");
    await page.getByRole("button", { name: /add treatment/i }).click();
    await toast(page, "Treatment added");
    // openTreatments re-fetches after add — wait for E-stim to appear in the
    // updated list (confirms the in-flight GET completed and modal re-rendered).
    // Then close via JS to avoid any race where a 2nd in-flight GET re-opens
    // the modal between the × click and the subsequent toBeHidden check.
    await expect(page.locator(".modal-bg")).toContainText("E-stim", { timeout: 15_000 });
    await page.evaluate(() => (window as any).closeModal());
    await expect(page.locator(".modal-bg")).toBeHidden({ timeout: 8_000 });

    // ── 4. End service ────────────────────────────────────────────────────
    await page.getByTestId(`room-end-service-${ROOM_CODE}`).click();
    await toast(page, "Service ended");

    // ── 5. Checkout with copay ────────────────────────────────────────────
    await expect(visitRow).toContainText("service_completed", { timeout: 10_000 });
    await visitRow.getByRole("button", { name: /out/i }).click();
    await page.locator("#co-cc").fill(COPAY_AMT);
    await page.locator("#co-ps").selectOption("copay_collected");
    await page.getByRole("button", { name: /check out/i }).first().click();
    await toast(page, "Checked out");

    // ── 6. Treatment records tab ──────────────────────────────────────────
    await tab(page, "tab-treatments");
    await page.getByRole("button", { name: /search/i }).click();
    await expect(page.locator("#treatment-records-list")).toContainText(PT_FULL, { timeout: 10_000 });
    await expect(page.locator("#treatment-records-list")).toContainText("E-stim");

    // ── 7. Report tab — patient appears with copay ────────────────────────
    await tab(page, "tab-report");
    await expect(page.locator("#sum-stats")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("#sum-table")).toContainText(PT_FULL, { timeout: 10_000 });
    await expect(page.locator("#sum-table")).toContainText(`$${COPAY_AMT}`);

    // ── 8. Events tab — all 4 audit events ───────────────────────────────
    await tab(page, "tab-events");
    const events = page.getByTestId("events-list");
    await expect(events).toContainText("PATIENT_CHECKIN",  { timeout: 15_000 });
    await expect(events).toContainText("SERVICE_STARTED",  { timeout: 10_000 });
    await expect(events).toContainText("SERVICE_COMPLETED",{ timeout: 10_000 });
    await expect(events).toContainText("PATIENT_CHECKOUT", { timeout: 10_000 });

    // ── 9. Patient detail — visit history + PDF link ──────────────────────
    await tab(page, "tab-patients");
    await page.locator("#pt-search").fill(PT_MRN);
    await page.locator("#pt-search").press("Enter");
    await expect(page.locator("#patients-list")).toContainText(PT_FULL, { timeout: 10_000 });
    await page.getByRole("button", { name: /view/i }).first().click();

    const modal = page.locator(".modal-box");
    await expect(modal).toBeVisible({ timeout: 5_000 });
    await expect(modal).toContainText(PT_FULL);
    // Visit history shows the checkout with copay
    await expect(modal).toContainText("checked_out");
    await expect(modal).toContainText(`$${COPAY_AMT}`);
    // PDF link is present
    const pdfLink = modal.locator("a[href*='sign-sheet.pdf']");
    await expect(pdfLink).toBeVisible({ timeout: 5_000 });
    await expect(pdfLink).toContainText("Sign Sheet PDF");
  });
});
