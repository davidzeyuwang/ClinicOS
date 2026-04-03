/**
 * Shared clinic harness suite.
 *
 * Contains all 31 focused E2E tests for the ClinicOS UI, parameterised by a
 * `HarnessEnv` adapter so the same scenarios run against both the local SQLite
 * dev server and the Vercel + Supabase production environment.
 *
 * Two thin wrappers provide the adapters:
 *   local-smoke.spec.ts  — resetLocalData before each test, creates room via UI
 *   prod-smoke.spec.ts   — force-available room C1 before each test, pre-seeded staff
 */

import { test, expect, type Page, type APIRequestContext } from "@playwright/test";
import {
  apiGet,
  apiPost,
  expectToast,
  openTab,
  seedAppointment,
  seedPatient,
} from "../helpers";

// ── Public types ──────────────────────────────────────────────────────────────

export interface HarnessEnv {
  suiteName: string;

  /** Primary room used by most tests ("R1" local, "C1" prod). */
  roomCode: string;
  roomName: string;

  /**
   * Alternate room for the comprehensive E2E test (#28).
   * "TRA" local, "C2" prod.
   */
  altRoomCode: string;
  altRoomName: string;

  /** Staff created/used by most tests ("Alice PT" local, pre-seeded name on prod). */
  staffName: string;

  /**
   * Staff created in test #28 ("Dr. Sarah Chen" local, unique per run on prod
   * to avoid duplicate-creation errors on subsequent runs).
   */
  altStaffName: string;

  /**
   * Room code used ONLY in test #1 ("admin can create room and staff").
   * Same as roomCode on local (reset wipes it); unique per run on prod.
   */
  testRoomCode: string;
  testRoomName: string;

  /** Staff name used ONLY in test #1 ("Bob OT" local, unique per run on prod). */
  testStaffName: string;

  /**
   * Service type retired in test #30.
   * "OT" on local (pre-seeded, reset before each test).
   * A unique name on prod so we don't touch real service types.
   */
  retireServiceTypeName: string;

  /**
   * When true, test #30 first creates the service type via UI before retiring it.
   * false on local (OT already seeded); true on prod.
   */
  createRetireTarget: boolean;

  /**
   * When true, setupRoomAndStaff() creates the room + staff through the browser UI.
   * When false (prod), the room + staff are pre-seeded; the helper is a no-op.
   */
  createViaUI: boolean;

  /**
   * When true (local), report count assertions use exact equality.
   * When false (prod, accumulated data), they use >= 1.
   */
  exactCounts: boolean;

  /** Called inside test.beforeEach. */
  beforeEach: (request: APIRequestContext, page: Page) => Promise<void>;

  /** Called inside test.afterEach (optional; prod uses this to reset room). */
  afterEach?: (request: APIRequestContext) => Promise<void>;
}

// ── Factory ───────────────────────────────────────────────────────────────────

export function registerHarnessTests(env: HarnessEnv): void {
  // ── Helpers (close over env) ──────────────────────────────────────────────

  async function setupRoomAndStaff(page: Page) {
    if (!env.createViaUI) return;
    await openTab(page, "tab-admin");
    await page.getByTestId("room-name-input").fill(env.roomName);
    await page.getByTestId("room-code-input").fill(env.roomCode);
    await page.getByTestId("add-room-button").click();
    await expectToast(page, "Room added");
    await page.getByTestId("staff-name-input").fill(env.staffName);
    await page.getByTestId("staff-role-input").selectOption("therapist");
    await page.getByTestId("add-staff-button").click();
    await expectToast(page, "Staff added");
  }

  async function checkinAndStartService(page: Page, patientName: string) {
    await openTab(page, "tab-ops");
    await page.getByTestId(`room-checkin-${env.roomCode}`).click();
    await page.locator("#rc-search").fill(patientName);
    await page.locator("#rc-staff").selectOption({ index: 0 });
    await page.getByRole("button", { name: "Check In & Start" }).click();
    await expectToast(page, "room assigned");
  }

  async function endService(page: Page) {
    await page.getByTestId(`room-end-service-${env.roomCode}`).click();
    await expectToast(page, "Service ended");
  }

  async function openCheckoutModal(page: Page, patientName: string) {
    const visitRow = page.locator("#visits-list tr").filter({ hasText: patientName });
    await expect(visitRow).toContainText("service_completed");
    await visitRow.getByRole("button", { name: /out/i }).click();
  }

  // ── Suite ──────────────────────────────────────────────────────────────────

  test.describe(env.suiteName, () => {
    test.beforeEach(async ({ page, request }) => {
      await env.beforeEach(request, page);
    });

    test.afterEach(async ({ request }) => {
      if (env.afterEach) await env.afterEach(request);
    });

    // ── 1. Admin setup ────────────────────────────────────────────────────────
    test("admin can create room and staff", async ({ page }) => {
      await openTab(page, "tab-admin");

      await page.getByTestId("room-name-input").fill(env.testRoomName);
      await page.getByTestId("room-code-input").fill(env.testRoomCode);
      await page.getByTestId("add-room-button").click();
      await expectToast(page, "Room added");
      await expect(page.getByTestId(`room-list-item-${env.testRoomCode}`)).toContainText(env.testRoomName);

      await page.getByTestId("staff-name-input").fill(env.testStaffName);
      await page.getByTestId("staff-role-input").selectOption("therapist");
      await page.getByTestId("staff-license-input").fill("OT-002");
      await page.getByTestId("add-staff-button").click();
      await expectToast(page, "Staff added");
      await expect(page.getByTestId("staff-list")).toContainText(env.testStaffName);
    });

    // ── 2. Walk-in quick checkout ─────────────────────────────────────────────
    test("ops board walk-in flow: skip payment checkout", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Walk In John");

      const roomCard = page.getByTestId(`room-card-${env.roomCode}`);
      await expect(roomCard).toContainText("Walk In John");
      await expect(roomCard).toContainText("occupied");

      await endService(page);
      await openCheckoutModal(page, "Walk In John");
      await page.getByRole("button", { name: /skip/i }).click();
      await expectToast(page, "Checked out");

      await expect(roomCard).toContainText("available");
      await expect(roomCard).toContainText("Empty");
    });

    // ── 3. Checkout with copay CC + WD + signed ────────────────────────────────
    test("checkout collects copay CC, WD verified, and patient signed", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Copay Patient");
      await endService(page);
      await openCheckoutModal(page, "Copay Patient");

      await page.locator("#co-cc").fill("25");
      await page.locator("#co-ps").selectOption("copay_collected");
      await page.locator("#co-pm").selectOption("cash");
      await page.locator("#co-wd").check();
      await page.locator("#co-signed").check();

      await expect(page.locator("#co-wd")).toBeChecked();
      await expect(page.locator("#co-signed")).toBeChecked();

      await page.getByRole("button", { name: /check out/i }).first().click();
      await expectToast(page, "Checked out");

      await expect(page.getByTestId(`room-card-${env.roomCode}`)).toContainText("available");
    });

    // ── 4. Checkout modal field layout ─────────────────────────────────────────
    test("checkout modal has copay CC, WD, and signed fields", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Field Test Patient");
      await endService(page);
      await openCheckoutModal(page, "Field Test Patient");

      await expect(page.locator("#co-cc")).toBeVisible();
      await expect(page.locator("#co-wd")).toBeVisible();
      await expect(page.locator("#co-signed")).toBeVisible();
      await expect(page.locator("#co-ps")).toBeVisible();
      await expect(page.locator("#co-pm")).toBeVisible();

      await expect(page.locator("#co-wd")).not.toBeChecked();
      await expect(page.locator("#co-signed")).not.toBeChecked();

      await expect(page.getByRole("button", { name: /check out/i }).first()).toBeVisible();
      await expect(page.getByRole("button", { name: /skip/i })).toBeVisible();
    });

    // ── 5. Patient detail shows visit history ──────────────────────────────────
    test("patient detail shows visit history with copay info", async ({ page }) => {
      await setupRoomAndStaff(page);

      await openTab(page, "tab-patients");
      await page.getByRole("button", { name: /new/i }).click();
      await page.locator("#np-fn").fill("History");
      await page.locator("#np-ln").fill("Patient");
      await page.locator("#np-dob").fill("1990-05-15");
      await page.locator("#np-phone").fill("555-9999");
      await page.getByRole("button", { name: /create patient/i }).click();
      await expectToast(page, "Patient created");

      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.roomCode}`).click();
      await page.locator("#rc-search").fill("History");
      await expect(page.locator("#rc-results")).toBeVisible();
      await page.locator("#rc-results div").first().click();
      await page.locator("#rc-staff").selectOption({ index: 0 });
      await page.getByRole("button", { name: "Check In & Start" }).click();
      await expectToast(page, "room assigned");
      await endService(page);
      await openCheckoutModal(page, "History Patient");
      await page.locator("#co-cc").fill("30");
      await page.locator("#co-wd").check();
      await page.locator("#co-signed").check();
      await page.getByRole("button", { name: /check out/i }).first().click();
      await expectToast(page, "Checked out");

      await openTab(page, "tab-patients");
      await page.locator("#pt-search").fill("History");
      await page.locator("#pt-search").press("Enter");
      await page.getByRole("button", { name: /view/i }).first().click();

      await expect(page.locator(".modal-box")).toContainText("Visit History");
      await expect(page.locator(".modal-box")).toContainText("$30.00");
      await expect(page.locator(".modal-box")).toContainText("✓");
    });

    // ── 6. Patient detail has Sign Sheet PDF link ──────────────────────────────
    test("patient detail has sign sheet PDF download link", async ({ page }) => {
      await openTab(page, "tab-patients");
      await page.getByRole("button", { name: /new/i }).click();
      await page.locator("#np-fn").fill("PDF");
      await page.locator("#np-ln").fill("Downloader");
      await page.locator("#np-dob").fill("1985-03-20");
      await page.locator("#np-phone").fill("555-8888");
      await page.getByRole("button", { name: /create patient/i }).click();
      await expectToast(page, "Patient created");

      await page.getByRole("button", { name: /view/i }).first().click();

      const pdfLink = page.locator(".modal-box a[href*='sign-sheet.pdf']");
      await expect(pdfLink).toBeVisible();
      await expect(pdfLink).toContainText("Sign Sheet PDF");
    });

    // ── 7. Report tab daily summary ────────────────────────────────────────────
    test("report tab daily summary shows completed visit with copay", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Summary Test");
      await endService(page);
      await openCheckoutModal(page, "Summary Test");
      await page.locator("#co-cc").fill("45");
      await page.locator("#co-wd").check();
      await page.getByRole("button", { name: /check out/i }).first().click();
      await expectToast(page, "Checked out");

      await openTab(page, "tab-report");
      await expect(page.locator("#sum-stats")).toBeVisible({ timeout: 5000 });

      const ciCount = parseInt((await page.locator("#sum-ci").textContent()) ?? "0");
      expect(ciCount).toBeGreaterThanOrEqual(1);
      const coCount = parseInt((await page.locator("#sum-co").textContent()) ?? "0");
      expect(coCount).toBeGreaterThanOrEqual(1);

      await expect(page.locator("#sum-copay")).toContainText("$45");
      await expect(page.locator("#sum-table")).toContainText("Summary Test");
      await expect(page.locator("#sum-table")).toContainText("✓");
    });

    // ── 8. Report + event log ──────────────────────────────────────────────────
    test("report and event log reflect completed visit", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Regression Jane");
      await endService(page);
      await openCheckoutModal(page, "Regression Jane");

      await page.locator("#co-cc").fill("30");
      await page.locator("#co-ps").selectOption("copay_collected");
      await page.locator("#co-pm").selectOption("card");
      await page.getByRole("button", { name: /check out/i }).first().click();
      await expectToast(page, "Checked out");

      await openTab(page, "tab-report");
      await page.getByTestId("generate-report-button").click();
      await expectToast(page, "Generated");
      await expect(page.getByTestId("report-content")).toBeVisible();

      if (env.exactCounts) {
        await expect(page.locator("#rpt-ci")).toHaveText("1");
        await expect(page.locator("#rpt-co")).toHaveText("1");
        await expect(page.locator("#rpt-svc")).toHaveText("1");
      } else {
        const ci = parseInt((await page.locator("#rpt-ci").textContent()) ?? "0");
        expect(ci).toBeGreaterThanOrEqual(1);
      }

      await openTab(page, "tab-events");
      const events = page.getByTestId("events-list");
      await expect(events).toContainText("PATIENT_CHECKIN");
      await expect(events).toContainText("SERVICE_STARTED");
      await expect(events).toContainText("SERVICE_COMPLETED");
      await expect(events).toContainText("PATIENT_CHECKOUT");
    });

    // ── 9. Disabled status buttons when room occupied ─────────────────────────
    test("free/clean/OOS buttons are disabled when room is occupied", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Disable Test");

      const roomCard = page.getByTestId(`room-card-${env.roomCode}`);
      await expect(roomCard).toContainText("occupied");

      await expect(roomCard.getByTitle("Free")).toBeDisabled();
      await expect(roomCard.getByTitle("Cleaning")).toBeDisabled();
      await expect(roomCard.getByTitle("OOS")).toBeDisabled();
    });

    // ── 10. Deleted patient does not appear in typeahead ──────────────────────
    test("deleted patient does not appear in check-in typeahead", async ({ page }) => {
      await openTab(page, "tab-patients");
      await page.getByRole("button", { name: /new/i }).click();
      await page.locator("#np-fn").fill("Ghost");
      await page.locator("#np-ln").fill("Patient");
      await page.locator("#np-dob").fill("1975-11-30");
      await page.locator("#np-phone").fill("555-7777");
      await page.getByRole("button", { name: /create patient/i }).click();
      await expectToast(page, "Patient created");

      await page.locator("#pt-search").fill("Ghost");
      await page.locator("#pt-search").press("Enter");
      page.once("dialog", (dialog) => dialog.accept());
      await page.getByRole("button", { name: /delete/i }).first().click();
      await expectToast(page, "Patient removed");

      if (env.createViaUI) {
        await openTab(page, "tab-admin");
        await page.getByTestId("room-name-input").fill(env.roomName);
        await page.getByTestId("room-code-input").fill(env.roomCode);
        await page.getByTestId("add-room-button").click();
        await expectToast(page, "Room added");
      }

      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.roomCode}`).click();
      await page.locator("#rc-search").fill("Ghost");
      await expect(page.locator("#rc-results")).toBeVisible();
      await expect(page.locator("#rc-results")).toContainText("No matches");
    });

    // ── 11. Appointments: check-in scheduled patient ──────────────────────────
    test("appointments tab can check in a scheduled patient", async ({ page, request }) => {
      await setupRoomAndStaff(page);
      const staffHours = await apiGet(request, "/projections/staff-hours");
      const therapistId = staffHours.staff.find(
        (m: { role: string }) => m.role === "therapist",
      ).staff_id;
      const patient = await seedPatient(request, "Amy", "Appt", "MRN-2001");
      await seedAppointment(request, patient.patient_id, therapistId, "09:30");

      await openTab(page, "tab-appointments");
      const row = page.locator("#appts-list tr").filter({ hasText: "09:30" });
      await expect(row).toContainText("scheduled");
      await row.getByRole("button", { name: "Check-In" }).click();
      await expectToast(page, "checked in");
      await expect(row).toContainText("checked_in");

      await openTab(page, "tab-ops");
      await expect(page.locator("#visits-list")).toContainText("Amy Appt");
    });

    // ── 12. Appointments: no-show and cancel ──────────────────────────────────
    test("appointments tab can mark no-show and cancel", async ({ page, request }) => {
      await setupRoomAndStaff(page);
      const staffHours = await apiGet(request, "/projections/staff-hours");
      const therapistId = staffHours.staff.find(
        (m: { role: string }) => m.role === "therapist",
      ).staff_id;

      const noShowPatient = await seedPatient(request, "Nora", "Show", "MRN-2002");
      await seedAppointment(request, noShowPatient.patient_id, therapistId, "11:00");
      const cancelPatient = await seedPatient(request, "Carl", "Cancel", "MRN-2003");
      await seedAppointment(request, cancelPatient.patient_id, therapistId, "14:00");

      await openTab(page, "tab-appointments");

      const noShowRow = page.locator("#appts-list tr").filter({ hasText: "11:00" });
      await noShowRow.getByRole("button", { name: "No-Show" }).click();
      await expectToast(page, "No-show");
      await expect(noShowRow).toContainText("no_show");

      const cancelRow = page.locator("#appts-list tr").filter({ hasText: "14:00" });
      await cancelRow.getByRole("button", { name: "Cancel" }).click();
      await expectToast(page, "Cancelled");
      await expect(cancelRow).toContainText("cancelled");
    });

    // ── 13. Refresh keeps occupancy state ─────────────────────────────────────
    test("refresh keeps in-service room occupancy visible", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Refresh Rita");

      const roomCard = page.getByTestId(`room-card-${env.roomCode}`);
      await expect(roomCard).toContainText("Refresh Rita");
      await expect(roomCard).toContainText("occupied");

      await page.reload();
      await expect(roomCard).toContainText("Refresh Rita");
      await expect(roomCard).toContainText("occupied");
    });

    // ── 14. Insurance-only payment path ───────────────────────────────────────
    test("checkout supports insurance-only payment path", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Insured Ivy");
      await endService(page);
      await openCheckoutModal(page, "Insured Ivy");

      await page.locator("#co-ps").selectOption("insurance_only");
      await page.getByRole("button", { name: /check out/i }).first().click();
      await expectToast(page, "Checked out");
      await expect(page.getByTestId(`room-card-${env.roomCode}`)).toContainText("available");
    });

    // ── 15. Add treatment to active visit ─────────────────────────────────────
    test("can add a treatment modality to an in-service visit", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Treatment Tanya");

      const visitRow = page.locator("#visits-list tr").filter({ hasText: "Treatment Tanya" });
      await expect(visitRow).toContainText("in_service");
      await visitRow.getByRole("button", { name: /tx/i }).click();

      await expect(page.locator("#modal, .modal-bg")).toBeVisible();
      await page.locator("#trt-mod").selectOption("E-stim");
      await page.locator("#trt-dur").fill("20");
      await page.getByRole("button", { name: /add treatment/i }).click();
      await expectToast(page, "Treatment added");
    });

    // ── 16. Treatment Records tab ─────────────────────────────────────────────
    test("treatment records tab shows records after adding treatment", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Records Pat");

      const visitRow = page.locator("#visits-list tr").filter({ hasText: "Records Pat" });
      await visitRow.getByRole("button", { name: /tx/i }).click();
      await page.locator("#trt-mod").selectOption("PT");
      await page.locator("#trt-dur").fill("30");
      await page.getByRole("button", { name: /add treatment/i }).click();
      await expectToast(page, "Treatment added");
      await page.getByRole("button", { name: /×/ }).click();

      await openTab(page, "tab-treatments");
      await page.getByRole("button", { name: /search/i }).click();

      await expect(page.locator("#treatment-records-list")).toContainText("Records Pat");
      await expect(page.locator("#treatment-records-list")).toContainText("PT");
    });

    // ── 17. Treatment date format ──────────────────────────────────────────────
    test("treatment records show correct date and duration format", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Date Dan");

      const visitRow = page.locator("#visits-list tr").filter({ hasText: "Date Dan" });
      await visitRow.getByRole("button", { name: /tx/i }).click();
      await page.locator("#trt-mod").selectOption("PT");
      await page.locator("#trt-dur").fill("90"); // 30m initial + 90m = 2h
      await page.getByRole("button", { name: /add treatment/i }).click();
      await expectToast(page, "Treatment added");
      await page.getByRole("button", { name: /×/ }).click();

      await openTab(page, "tab-treatments");
      await page.getByRole("button", { name: /search/i }).click();

      const table = page.locator("#treatment-records-list");
      const dateCell = table.locator("tbody tr").first().locator("td").nth(1);
      await expect(dateCell).not.toHaveText("-");
      await expect(table).toContainText("2h");
    });

    // ── 18. Treatment Records column headers ──────────────────────────────────
    test("treatment records table has all required columns", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Column Check");

      const visitRow = page.locator("#visits-list tr").filter({ hasText: "Column Check" });
      await visitRow.getByRole("button", { name: /tx/i }).click();
      await page.locator("#trt-mod").selectOption("Acupuncture");
      await page.locator("#trt-dur").fill("60");
      await page.getByRole("button", { name: /add treatment/i }).click();
      await expectToast(page, "Treatment added");
      await page.getByRole("button", { name: /×/ }).click();

      await openTab(page, "tab-treatments");
      await page.getByRole("button", { name: /search/i }).click();

      const headers = page.locator("#treatment-records-list thead th");
      await expect(headers).toContainText(["#", "Date", "Patient", "生诊医生", "A", "PT", "CP", "TN", "Room", "Duration", "Note"]);
    });

    // ── 19. Walk-in name appears in treatment records ─────────────────────────
    test("walk-in treatment appears in treatment records with patient name", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Walkin Wayne");

      const visitRow = page.locator("#visits-list tr").filter({ hasText: "Walkin Wayne" });
      await visitRow.getByRole("button", { name: /tx/i }).click();
      await page.locator("#trt-mod").selectOption("Massage");
      await page.locator("#trt-dur").fill("45");
      await page.getByRole("button", { name: /add treatment/i }).click();
      await expectToast(page, "Treatment added");
      await page.getByRole("button", { name: /×/ }).click();

      await openTab(page, "tab-treatments");
      await page.getByRole("button", { name: /search/i }).click();

      const table = page.locator("#treatment-records-list");
      await expect(table).toContainText("Walkin Wayne");
      await expect(table).toContainText("45m");
    });

    // ── 20. Supervising doctor ────────────────────────────────────────────────
    test("start service modal has supervising doctor selector and it appears in treatment records", async ({ page, request }) => {
      await setupRoomAndStaff(page);

      await openTab(page, "tab-admin");
      await page.getByTestId("staff-name-input").fill("Dr. Gao");
      await page.getByTestId("staff-role-input").selectOption("therapist");
      await page.getByTestId("add-staff-button").click();
      await expectToast(page, "Staff added");

      await apiPost(request, "/portal/checkin", {
        patient_name: "Supervised Sue",
        actor_id: "frontdesk",
      });

      await openTab(page, "tab-ops");
      const visitRow = page.locator("#visits-list tr").filter({ hasText: "Supervised Sue" });
      await expect(visitRow).toContainText("checked_in");
      await visitRow.getByRole("button", { name: /start/i }).click();

      await expect(page.locator("#as-super")).toBeVisible();
      await page.locator("#as-super").selectOption({ label: "Dr. Gao" });
      await page.locator("#as-staff").selectOption({ index: 0 });
      await page.locator("#as-room").selectOption({ index: 0 });
      await page.getByRole("button", { name: /start service/i }).click();
      await expectToast(page, "Started");

      await visitRow.getByRole("button", { name: /tx/i }).click();
      await page.locator("#trt-mod").selectOption("Acupuncture");
      await page.locator("#trt-dur").fill("60");
      await page.getByRole("button", { name: /add treatment/i }).click();
      await expectToast(page, "Treatment added");
      await page.getByRole("button", { name: /×/ }).click();

      await openTab(page, "tab-treatments");
      await page.getByRole("button", { name: /search/i }).click();
      await expect(page.locator("#treatment-records-list")).toContainText("Supervised Sue");
      await expect(page.locator("#treatment-records-list")).toContainText("Dr. Gao");
    });

    // ── 21. Sign sheet PDF is valid ────────────────────────────────────────────
    test("sign sheet PDF endpoint returns valid PDF binary", async ({ request }) => {
      const patient = await apiPost(request, "/patients", {
        first_name: "PDF",
        last_name: "Tester",
        date_of_birth: "1980-06-01",
        phone: "555-0001",
      });

      const resp = await request.get(`/prototype/patients/${patient.patient_id}/sign-sheet.pdf`);
      expect(resp.ok()).toBeTruthy();
      expect(resp.headers()["content-type"]).toContain("application/pdf");

      const body = await resp.body();
      expect(body.slice(0, 4).toString()).toBe("%PDF");
      expect(body.length).toBeGreaterThan(1500);
    });

    // ── 22. PDF does not contain raw status strings ────────────────────────────
    test("sign sheet PDF does not contain raw status strings", async ({ request }) => {
      const patient = await apiPost(request, "/patients", {
        first_name: "Status",
        last_name: "Label",
        date_of_birth: "1992-09-15",
        phone: "555-0002",
      });

      const resp = await request.get(`/prototype/patients/${patient.patient_id}/sign-sheet.pdf`);
      const body = await resp.body();
      const text = body.toString("latin1");

      expect(text).not.toContain("service_complet");
      expect(text).not.toContain("checked_in");
      expect(text).not.toContain("in_service");
    });

    // ── 23. Checkout modal pre-fills copay from insurance ─────────────────────
    test("checkout modal pre-fills copay amount from patient insurance", async ({ page, request }) => {
      await setupRoomAndStaff(page);

      const patient = await apiPost(request, "/patients", {
        first_name: "Copay",
        last_name: "Prefill",
        date_of_birth: "1988-02-14",
        phone: "555-4545",
      });
      await apiPost(request, "/insurance", {
        patient_id: patient.patient_id,
        carrier_name: "Test Insurance",
        copay_amount: 45.0,
        visits_authorized: 20,
      });

      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.roomCode}`).click();
      await page.locator("#rc-search").fill("Copay");
      await expect(page.locator("#rc-results")).toBeVisible();
      await page.locator("#rc-results div").first().click();
      await page.locator("#rc-staff").selectOption({ index: 0 });
      await page.getByRole("button", { name: "Check In & Start" }).click();
      await expectToast(page, "room assigned");
      await endService(page);
      await openCheckoutModal(page, "Copay Prefill");

      await expect(page.locator("#co-cc")).toHaveValue("45");
      await expect(page.locator("#co-ps")).toHaveValue("copay_collected");
    });

    // ── 24. Patient creation requires DOB and phone ───────────────────────────
    test("patient creation requires date of birth and phone", async ({ page }) => {
      await openTab(page, "tab-patients");
      await page.getByRole("button", { name: /new/i }).click();

      await page.locator("#np-fn").fill("Incomplete");
      await page.locator("#np-ln").fill("Patient");
      await page.getByRole("button", { name: /create patient/i }).click();
      await expectToast(page, "Date of birth required");

      await page.locator("#np-dob").fill("1990-01-01");
      await page.getByRole("button", { name: /create patient/i }).click();
      await expectToast(page, "Phone required");

      await page.locator("#np-phone").fill("555-1234");
      await page.getByRole("button", { name: /create patient/i }).click();
      await expectToast(page, "Patient created");
    });

    // ── 25. Sign sheet PDF shows expected copay for unchecked-out visits ──────
    test("sign sheet PDF shows expected copay from insurance for unchecked-out visits", async ({ request }) => {
      const patient = await apiPost(request, "/patients", {
        first_name: "Copay",
        last_name: "SignSheet",
        date_of_birth: "1985-07-04",
        phone: "555-1616",
      });
      await apiPost(request, "/insurance", {
        patient_id: patient.patient_id,
        carrier_name: "Shield PPO",
        copay_amount: 35.0,
        visits_authorized: 24,
      });
      await apiPost(request, "/portal/checkin", {
        patient_name: "Copay SignSheet",
        patient_id: patient.patient_id,
        actor_id: "desk",
      });

      const resp = await request.get(`/prototype/patients/${patient.patient_id}/sign-sheet.pdf`);
      expect(resp.ok()).toBeTruthy();
      const body = await resp.body();
      expect(body.slice(0, 4).toString()).toBe("%PDF");
      expect(body.length).toBeGreaterThan(2000);
    });

    // ── 26. Staff hours reflect treatment duration, not wall-clock ────────────
    test("report staff hours reflect treatment duration not wall-clock time", async ({ page }) => {
      await setupRoomAndStaff(page);
      await checkinAndStartService(page, "Hours Test");
      await endService(page);
      await openCheckoutModal(page, "Hours Test");
      await page.locator("#co-cc").fill("0");
      await page.getByRole("button", { name: /check out/i }).first().click();
      await expectToast(page, "Checked out");

      await openTab(page, "tab-report");
      await page.getByTestId("generate-report-button").click();
      await expectToast(page, "Generated");
      await expect(page.getByTestId("report-content")).toBeVisible();
      await expect(page.locator("#rpt-staff")).toContainText("30m");
    });

    // ── 27. Check-in modal service dropdown includes all modalities ───────────
    test("check-in modal service dropdown includes acupuncture cupping massage e-stim", async ({ page }) => {
      await setupRoomAndStaff(page);
      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.roomCode}`).click();

      const svc = page.locator("#rc-svc");
      await expect(svc).toBeVisible();
      for (const option of ["Acupuncture", "Cupping", "Massage", "E-stim"]) {
        await expect(svc.locator(`option[value="${option}"], option:has-text("${option}")`)).toBeAttached();
      }
    });

    // ── 28. Comprehensive E2E: full clinic workflow ────────────────────────────
    test("complete clinic workflow: staff → patient → checkin → treatments → checkout → PDF verification", async ({ page, request }) => {
      await openTab(page, "tab-admin");

      if (env.createViaUI) {
        await page.getByTestId("room-name-input").fill(env.altRoomName);
        await page.getByTestId("room-code-input").fill(env.altRoomCode);
        await page.getByTestId("add-room-button").click();
        await expectToast(page, "Room added");
      }

      await page.getByTestId("staff-name-input").fill(env.altStaffName);
      await page.getByTestId("staff-role-input").selectOption("therapist");
      await page.getByTestId("staff-license-input").fill("PT-9876");
      await page.getByTestId("add-staff-button").click();
      await expectToast(page, "Staff added");
      await expect(page.getByTestId("staff-list")).toContainText(env.altStaffName);

      const patient = await seedPatient(request, "Emily", "Rodriguez", "E2E-001");
      const patientId = patient.patient_id;
      await apiPost(request, "/insurance", {
        patient_id: patientId,
        carrier_name: "Blue Cross PPO",
        member_id: "BC123456789",
        copay_amount: 45.0,
        visits_authorized: 20,
      });

      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.altRoomCode}`).click();
      await page.locator("#rc-search").fill("Emily Rodriguez");
      await page.locator("#rc-staff").selectOption({ index: 1 });
      await page.locator("#rc-svc").selectOption("PT");
      await page.locator("#rc-dur").fill("45");
      await page.getByRole("button", { name: "Check In & Start" }).click();
      await expectToast(page, "room assigned");

      await page.waitForTimeout(500);
      const roomCard = page.getByTestId(`room-card-${env.altRoomCode}`);
      await expect(roomCard).toContainText("Emily Rodriguez");
      await expect(roomCard).toContainText("occupied");

      const visitRow = page.locator("#visits-list tr").filter({ hasText: "Emily Rodriguez" });
      await expect(visitRow).toBeVisible();

      await page.getByTestId(`room-end-service-${env.altRoomCode}`).click();
      await expectToast(page, "Service ended");
      await page.waitForTimeout(500);
      await expect(visitRow).toContainText("service_completed");

      await visitRow.getByRole("button", { name: /out/i }).click();
      await page.locator("#co-cc").fill("45");
      await page.locator("#co-wd").check();
      await page.getByRole("button", { name: /check out/i }).first().click();
      await expectToast(page, "Checked out");
      await page.waitForTimeout(500);

      const pdfResp = await request.get(`/prototype/patients/${patientId}/sign-sheet.pdf`);
      expect(pdfResp.ok()).toBeTruthy();
      const pdfBody = await pdfResp.body();
      expect(pdfBody.slice(0, 4).toString()).toBe("%PDF");
      expect(pdfBody.length).toBeGreaterThan(2000);
      const pdfText = pdfBody.toString("latin1");
      expect(pdfText).toContain("/Type /Page");
      expect(pdfText).toContain("endobj");
      expect(pdfText).toContain("%%EOF");

      await openTab(page, "tab-report");
      await page.getByTestId("generate-report-button").click();
      await expectToast(page, "Generated");
      const reportContent = page.getByTestId("report-content");
      await expect(reportContent).toBeVisible();
      await expect(reportContent).toContainText("1");
      await expect(reportContent).toContainText("45");
    });

    // ── 29. Admin can add service type ────────────────────────────────────────
    test("admin can add service type and it appears in check-in dropdown", async ({ page }) => {
      await setupRoomAndStaff(page);

      await openTab(page, "tab-admin");
      await page.getByTestId("svc-type-name-input").fill("Lymphatic Massage");
      await page.getByTestId("add-svc-type-button").click();
      await expectToast(page, "Service type added");

      await expect(page.locator("#service-type-list")).toContainText("Lymphatic Massage");

      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.roomCode}`).click();
      const svcSel = page.locator("#rc-svc");
      await expect(svcSel).toBeVisible();
      await expect(svcSel.locator('option[value="Lymphatic Massage"]')).toBeAttached();
    });

    // ── 30. Retiring a service type removes it from check-in dropdown ─────────
    test("retiring a service type removes it from check-in dropdown", async ({ page }) => {
      await setupRoomAndStaff(page);

      await openTab(page, "tab-admin");

      if (env.createRetireTarget) {
        // On prod, create a fresh type so we don't accidentally retire real service types
        await page.getByTestId("svc-type-name-input").fill(env.retireServiceTypeName);
        await page.getByTestId("add-svc-type-button").click();
        await expectToast(page, "Service type added");
      }

      const safeId = env.retireServiceTypeName.replace(/\s+/g, "-");
      await page.getByTestId(`svc-type-item-${safeId}`).getByTitle("Deactivate").click();
      await expectToast(page, "Deactivated");

      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.roomCode}`).click();
      const svcSel = page.locator("#rc-svc");
      await expect(svcSel).toBeVisible();
      await expect(svcSel.locator(`option[value="${env.retireServiceTypeName}"]`)).not.toBeAttached();
    });

    // ── 31. Staff dropdown filters by service type qualification ──────────────
    test("staff dropdown filters by service type qualification", async ({ page }) => {
      await openTab(page, "tab-admin");

      if (env.createViaUI) {
        await page.getByTestId("room-name-input").fill(env.roomName);
        await page.getByTestId("room-code-input").fill(env.roomCode);
        await page.getByTestId("add-room-button").click();
        await expectToast(page, "Room added");
      }

      await page.getByTestId("staff-name-input").fill("PT Only Staff");
      await page.getByTestId("staff-role-input").selectOption("therapist");
      await page.getByTestId("add-staff-button").click();
      await expectToast(page, "Staff added");

      await page.getByTestId("staff-name-input").fill("Acupuncture Only Staff");
      await page.getByTestId("staff-role-input").selectOption("therapist");
      await page.getByTestId("add-staff-button").click();
      await expectToast(page, "Staff added");

      await page.getByTestId("staff-list-item-PT-Only-Staff").locator("button.btn-xs").click();
      await expect(page.locator(".svc-cb").first()).toBeVisible();
      await page.locator(".svc-cb").evaluateAll((cbs: HTMLInputElement[]) =>
        cbs.forEach((cb) => { cb.checked = false; }),
      );
      await page.locator("label.cursor-pointer").filter({ hasText: "PT" }).first().locator(".svc-cb").check();
      await page.getByRole("button", { name: "Save" }).click();
      await expectToast(page, "Updated");

      await page.getByTestId("staff-list-item-Acupuncture-Only-Staff").locator("button.btn-xs").click();
      await expect(page.locator(".svc-cb").first()).toBeVisible();
      await page.locator(".svc-cb").evaluateAll((cbs: HTMLInputElement[]) =>
        cbs.forEach((cb) => { cb.checked = false; }),
      );
      await page.locator("label.cursor-pointer").filter({ hasText: "Acupuncture" }).first().locator(".svc-cb").check();
      await page.getByRole("button", { name: "Save" }).click();
      await expectToast(page, "Updated");

      await openTab(page, "tab-ops");
      await page.getByTestId(`room-checkin-${env.roomCode}`).click();
      await page.locator("#rc-svc").selectOption("PT");
      const staffOptions = await page.locator("#rc-staff option").allTextContents();
      expect(staffOptions.some((t) => t.includes("PT Only Staff"))).toBeTruthy();
      expect(staffOptions.some((t) => t.includes("Acupuncture Only Staff"))).toBeFalsy();
    });
  });
}
