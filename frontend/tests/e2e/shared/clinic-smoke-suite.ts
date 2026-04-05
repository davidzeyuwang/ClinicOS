/**
 * Shared clinic smoke suite.
 *
 * Contains every reusable piece of the multi-patient full-workflow smoke test:
 *   • PatientSpec / SmokeEnv types
 *   • UI helpers (toastMsg, goTab, runPatientWorkflow)
 *   • registerSmokeTests(env) — wires up test.describe + all 11 steps
 *
 * Two thin wrapper files provide the environment-specific adapters:
 *   smoke.spec.ts       — prod (Supabase REST verify, warmup, hard-delete cleanup)
 *   local-smoke.spec.ts — local (resetLocalData, app-API verify, no-op teardown)
 */

import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import { authHeaders } from "../helpers";

// ── Public types ──────────────────────────────────────────────────────────────

export interface PatientSpec {
  first: string;
  last: string;
  full: string;
  mrn: string;
  dob: string;
  phone: string;
  /** Empty string → no_charge path: frontend skips copay field, DB stores null. */
  copay: string;
  paymentStatus: string;
  /** Empty string → skip payment-method select (no_charge visits). */
  paymentMethod: string;
  treatments: Array<{ modality: string; duration: string }>;
}

export interface SmokeEnv {
  /** Label used in test.describe. */
  suiteName: string;
  /** Room code used for the check-in button test ID, e.g. "C1" or "LS1". */
  roomCode: string;
  /** The 3 base patients (copay/card, copay/cash, no_charge). */
  patients: PatientSpec[];
  /** Second visit for patients[0] — tests multi-visit + selective PDF. */
  patientV2: PatientSpec;

  /**
   * beforeAll hook: reset state, seed room/staff if needed, create the 3 patients.
   * Must return patient IDs in the same order as env.patients.
   */
  setup(request: APIRequestContext): Promise<string[]>;

  /**
   * Verify one visit's DB row, embedded treatments, and event chain.
   * Returns the visit_id of the verified visit (used for the selective-PDF call).
   *
   * visitIndex is 0-based chronologically (0 = first/oldest visit).
   */
  verifyPatient(
    request: APIRequestContext,
    pt: PatientSpec,
    pid: string,
    expectedVisitCount?: number,
    visitIndex?: number,
  ): Promise<string>;

  /** afterAll hook: clean up created test data. No-op for local (next reset handles it). */
  teardown(request: APIRequestContext, patientIds: string[]): Promise<void>;
}

// ── Shared UI helpers ─────────────────────────────────────────────────────────

export async function toastMsg(page: Page, text: string) {
  await expect(page.getByTestId("toast")).toContainText(text, { timeout: 15_000 });
}

export async function goTab(page: Page, testId: string) {
  await page.getByTestId(testId).click();
}

/**
 * Run the full UI workflow for one patient:
 *   check-in (MRN autocomplete) → first treatment set at check-in → additional
 *   treatments via Tx modal → end service → checkout.
 *
 * The doRoomCheckin handler auto-adds a treatment using the #rc-svc value, so
 * pt.treatments[0] is covered at check-in time. treatments.slice(1) are added
 * via the Tx modal.
 *
 * The check-in button being visible implicitly asserts the room was released by
 * the previous checkout.
 */
export async function runPatientWorkflow(page: Page, pt: PatientSpec, roomCode: string) {
  await goTab(page, "tab-ops");

  const checkinBtn = page.getByTestId(`room-checkin-${roomCode}`);
  await expect(checkinBtn).toBeVisible({ timeout: 10_000 });
  await checkinBtn.click();

  await page.locator("#rc-search").fill(pt.mrn);
  await expect(page.locator("#rc-results")).toBeVisible({ timeout: 10_000 });
  await page.locator("#rc-results div").first().click();
  await expect(page.locator("#rc-selected")).toContainText(pt.first, { timeout: 5_000 });

  await page.locator("#rc-staff").selectOption({ index: 0 });
  await page.locator("#rc-svc").selectOption(pt.treatments[0].modality);
  await page.locator("#rc-dur").fill(pt.treatments[0].duration);
  await page.getByRole("button", { name: "Check In & Start" }).click();
  await toastMsg(page, "room assigned");

  const visitRow = page.locator("#visits-list tr").filter({ hasText: pt.full });
  await expect(visitRow).toContainText("in_service", { timeout: 10_000 });

  // Additional treatments via Tx modal
  const additionalTreatments = pt.treatments.slice(1);
  if (additionalTreatments.length > 0) {
    await visitRow.getByRole("button", { name: /tx/i }).click();
    await expect(page.locator("#modal")).toBeVisible({ timeout: 10_000 });

    for (const tx of additionalTreatments) {
      await page.locator("#trt-mod").selectOption(tx.modality);
      await page.locator("#trt-dur").fill(tx.duration);
      await page.getByRole("button", { name: /add treatment/i }).click();
      await toastMsg(page, "Treatment added");
      await expect(page.locator("#modal")).toContainText(tx.modality, { timeout: 15_000 });
    }

    await page.evaluate(() => (window as any).closeModal());
    await expect(page.locator("#modal")).toBeHidden({ timeout: 8_000 });
  }

  // End service — force-close any stale modal first
  await page.evaluate(() => (window as any).closeModal());
  await visitRow.getByRole("button", { name: /end/i }).click();
  await toastMsg(page, "Service ended");

  // Checkout
  await expect(visitRow).toContainText("checked_in", { timeout: 10_000 });
  await page.evaluate(() => (window as any).closeModal());
  await visitRow.getByRole("button", { name: /out/i }).click();
  await page.locator("#co-cc").fill(pt.copay);
  if (pt.paymentStatus === "copay_collected") {
    await page.locator("#co-cc-collected").check();
  } else {
    await page.locator("#co-ps").selectOption(pt.paymentStatus);
  }
  if (pt.paymentMethod) {
    await page.locator("#co-pm").selectOption(pt.paymentMethod);
  }
  await page.locator("#co-wd").check();
  await page.locator("#co-signed").check();
  await page.getByRole("button", { name: /check out/i }).first().click();
  await toastMsg(page, "Checked out");

  console.log(`  ✓ UI workflow complete: ${pt.full}`);
}

// ── Suite registration ────────────────────────────────────────────────────────

/**
 * Register the full 11-step smoke suite under test.describe using the given
 * environment adapter.  Call this at the top level of a *.spec.ts file.
 *
 * Steps:
 *   0.  App loads
 *   1–3. UI workflow for env.patients[0..2]
 *   4.  DB verify all 3
 *   5.  Multi-visit: patients[0] returns (env.patientV2), DB verifies 2 visits
 *   6.  Selective PDF (?visit_ids=v2Id) — valid PDF, non-empty bytes
 *   7.  Full-history PDF — larger than selective (proves ?visit_ids filter works)
 *   8.  Treatment records tab — all 4 patient names present
 *   9.  Report tab — all 3 patients, copay amounts, ≥4 check-ins
 *   10. Events tab — all 5 event types present
 *   11. Patient detail modal + PDF for each of the 3 patients
 */
export function registerSmokeTests(env: SmokeEnv): void {
  test.describe(env.suiteName, () => {
    const patientIds: string[] = [];

    test.beforeAll(async ({ request }) => {
      const ids = await env.setup(request);
      patientIds.push(...ids);
    });

    test.afterAll(async ({ request }) => {
      if (patientIds.length) await env.teardown(request, patientIds);
    });

    test(
      "full clinic day: check in 3 patients (copay / cash / no-charge), add treatments, check out, return visit — verify DB rows, PDF, and all UI tabs",
      async ({ page, request }) => {
        // ── 0. App loads ────────────────────────────────────────────────────
        await page.goto("/ui/index.html");
        await expect(page.getByTestId("tab-ops")).toBeVisible({ timeout: 15_000 });

        // ── 1–3. UI workflow for all 3 patients ─────────────────────────────
        for (const pt of env.patients) {
          await runPatientWorkflow(page, pt, env.roomCode);
        }

        // ── 4. DB verify: visit row + treatments + event chain ───────────────
        const visitIds: string[] = [];
        for (let i = 0; i < env.patients.length; i++) {
          const vid = await env.verifyPatient(request, env.patients[i], patientIds[i]);
          visitIds.push(vid);
        }

        // ── 5. Multi-visit: patients[0] returns for a second visit ───────────
        await runPatientWorkflow(page, env.patientV2, env.roomCode);

        const pid0 = patientIds[0];
        const v2Id = await env.verifyPatient(request, env.patientV2, pid0, 2, 1);
        console.log(`  ✓ ${env.patients[0].first} now has 2 checked-out visits`);

        // ── 6. Selective PDF — visit 2 only ─────────────────────────────────
        // PDF content streams may be FlateDecode-compressed on deployed backends;
        // content is fully verified by DB assertions above.
        const pdfV2Resp = await page.request.get(
          `/prototype/patients/${pid0}/sign-sheet.pdf?visit_ids=${v2Id}`,
          { headers: authHeaders() },
        );
        expect(pdfV2Resp.ok(), "selective PDF request failed").toBeTruthy();
        expect(pdfV2Resp.headers()["content-type"]).toContain("application/pdf");
        const pdfV2Bytes = await pdfV2Resp.body();
        expect(pdfV2Bytes.length, "selective PDF must be non-empty").toBeGreaterThan(0);
        console.log("  ✓ Selective PDF (visit 2 only) verified");

        // ── 7. Full-history PDF — all visits for patients[0] ────────────────
        // 2-visit PDF must be larger than 1-visit selective PDF.
        const pdfAllResp = await page.request.get(
          `/prototype/patients/${pid0}/sign-sheet.pdf`,
          { headers: authHeaders() },
        );
        expect(pdfAllResp.ok(), "full-history PDF request failed").toBeTruthy();
        const pdfAllBytes = await pdfAllResp.body();
        expect(
          pdfAllBytes.length,
          "full-history PDF (2 visits) must be larger than selective PDF (1 visit)",
        ).toBeGreaterThan(pdfV2Bytes.length);
        console.log("  ✓ Full-history PDF (all visits) verified");

        // ── 8. Treatment records tab ─────────────────────────────────────────
        // Records view uses A/PT/CP/TN column format; patient names confirm all
        // 4 workflows appear.  Treatment content verified by DB assertions above.
        await goTab(page, "tab-treatments");
        await page.getByRole("button", { name: /search/i }).click();
        const txList = page.locator("#treatment-records-list");
        for (const pt of [...env.patients, env.patientV2]) {
          await expect(txList).toContainText(pt.full, { timeout: 10_000 });
        }
        console.log("  ✓ Treatment records tab verified");

        // ── 9. Report tab ─────────────────────────────────────────────────────
        await goTab(page, "tab-report");
        await expect(page.locator("#sum-stats")).toBeVisible({ timeout: 10_000 });
        const sumTable = page.locator("#sum-table");
        for (const pt of env.patients) {
          await expect(sumTable).toContainText(pt.full, { timeout: 10_000 });
        }
        await expect(sumTable).toContainText(`$${env.patients[1].copay}`); // cash copay
        await expect(sumTable).toContainText(env.patients[2].full);        // no_charge present

        // patients[0](×2) + patients[1](×1) + patients[2](×1) = 4 minimum
        const ciText = await page.locator("#sum-ci").textContent();
        expect(parseInt(ciText ?? "0")).toBeGreaterThanOrEqual(4);
        console.log("  ✓ Report tab verified");

        // ── 10. Events tab ────────────────────────────────────────────────────
        await goTab(page, "tab-events");
        const eventsWidget = page.getByTestId("events-list");
        for (const evtType of [
          "PATIENT_CHECKIN",
          "SERVICE_STARTED",
          "SERVICE_COMPLETED",
          "PATIENT_CHECKOUT",
          "TREATMENT_ADDED",
        ]) {
          await expect(eventsWidget).toContainText(evtType, { timeout: 15_000 });
        }
        console.log("  ✓ Events tab verified");

        // ── 11. Patient detail modal + PDF for all 3 patients ─────────────────
        await goTab(page, "tab-patients");

        for (let i = 0; i < env.patients.length; i++) {
          const pt  = env.patients[i];
          const pid = patientIds[i];

          await page.locator("#pt-search").fill(pt.mrn);
          await page.locator("#pt-search").press("Enter");
          await expect(page.locator("#patients-list")).toContainText(pt.full, {
            timeout: 10_000,
          });

          await page
            .locator("#patients-list tr")
            .filter({ hasText: pt.full })
            .getByRole("button", { name: /view/i })
            .click();

          const modal = page.locator(".modal-box");
          await expect(modal).toBeVisible({ timeout: 5_000 });
          await expect(modal).toContainText(pt.full);
          await expect(modal).toContainText("checked_out");

          const pdfLink = modal.locator("a[href*='sign-sheet.pdf']");
          await expect(pdfLink).toBeVisible({ timeout: 5_000 });
          await expect(pdfLink).toContainText("Sign Sheet PDF");

          const pdfResp = await page.request.get(
            `/prototype/patients/${pid}/sign-sheet.pdf`,
            { headers: authHeaders() },
          );
          expect(pdfResp.ok(), `PDF request failed for ${pt.full}`).toBeTruthy();
          expect(pdfResp.headers()["content-type"]).toContain("application/pdf");
          const pdfBytes = await pdfResp.body();
          expect(pdfBytes.length, `PDF must be non-empty for ${pt.full}`).toBeGreaterThan(0);
          console.log(`  ✓ Patient detail + PDF verified for ${pt.full}`);

          await page.evaluate(() => (window as any).closeModal());
          await expect(modal).toBeHidden({ timeout: 5_000 });
        }
      },
    );
  });
}
