/**
 * Deployed UI Workflow Tests
 *
 * Runs against the live deployed app (e.g. https://clinicos-psi.vercel.app).
 * Does NOT call any reset/seed API endpoints — all state is driven through the UI only.
 * Uses timestamped unique names so runs don't collide with production data.
 */
import { test, expect, type Page } from "@playwright/test";

// Unique suffix for this test run so data won't clash with existing records
const RUN_ID = Date.now().toString().slice(-6);
const ROOM_CODE = `T${RUN_ID}`;
const ROOM_NAME = `Test Room ${RUN_ID}`;
const STAFF_NAME = `Therapist ${RUN_ID}`;
const PATIENT_FIRST = `TestPt`;
const PATIENT_LAST = `${RUN_ID}`;
const PATIENT_FULL = `${PATIENT_FIRST} ${PATIENT_LAST}`;

// ── Shared helpers ────────────────────────────────────────────────────────────

async function openTab(page: Page, testId: string) {
  await page.getByTestId(testId).click();
}

async function expectToast(page: Page, text: string) {
  await expect(page.getByTestId("toast")).toContainText(text, { timeout: 10_000 });
}

/** Creates a unique room + staff member through the Admin tab. */
async function setupRoomAndStaff(page: Page) {
  await openTab(page, "tab-admin");

  await page.getByTestId("room-name-input").fill(ROOM_NAME);
  await page.getByTestId("room-code-input").fill(ROOM_CODE);
  await page.getByTestId("add-room-button").click();
  await expectToast(page, "Room added");

  await page.getByTestId("staff-name-input").fill(STAFF_NAME);
  await page.getByTestId("staff-role-input").selectOption("therapist");
  await page.getByTestId("add-staff-button").click();
  await expectToast(page, "Staff added");
}

/** Check in a walk-in patient by name to the room created for this run. */
async function checkinAndStartService(page: Page, patientName = `WalkIn ${RUN_ID}`) {
  await openTab(page, "tab-ops");
  await page.getByTestId(`room-checkin-${ROOM_CODE}`).click();
  await page.locator("#rc-search").fill(patientName);
  await page.locator("#rc-staff").selectOption({ index: 0 });
  await page.getByRole("button", { name: "Check In & Start" }).click();
  await expectToast(page, "room assigned");
}

/** End service for the room created for this run. */
async function endService(page: Page) {
  await page.getByTestId(`room-end-service-${ROOM_CODE}`).click();
  await expectToast(page, "Service ended");
}

/** Open checkout modal for a patient in the active visits list. */
async function openCheckoutModal(page: Page, patientName: string) {
  const visitRow = page.locator("#visits-list tr").filter({ hasText: patientName });
  await expect(visitRow).toContainText("service_completed");
  await visitRow.getByRole("button", { name: /out/i }).click();
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe("Deployed UI smoke — full workflow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/ui/index.html");
    // Wait for the app shell to be visible
    await expect(page.getByTestId("tab-ops")).toBeVisible({ timeout: 15_000 });
  });

  // ── 1. Page loads ──────────────────────────────────────────────────────────
  test("page loads and all main tabs are visible", async ({ page }) => {
    await expect(page.getByTestId("tab-ops")).toBeVisible();
    await expect(page.getByTestId("tab-admin")).toBeVisible();
    await expect(page.getByTestId("tab-patients")).toBeVisible();
    await expect(page.getByTestId("tab-report")).toBeVisible();
    await expect(page.getByTestId("tab-events")).toBeVisible();
  });

  // ── 2. Admin: create room and staff ───────────────────────────────────────
  test("admin can create room and staff member", async ({ page }) => {
    await openTab(page, "tab-admin");

    await page.getByTestId("room-name-input").fill(ROOM_NAME);
    await page.getByTestId("room-code-input").fill(ROOM_CODE);
    await page.getByTestId("add-room-button").click();
    await expectToast(page, "Room added");
    await expect(page.getByTestId(`room-list-item-${ROOM_CODE}`)).toContainText(ROOM_NAME);

    await page.getByTestId("staff-name-input").fill(STAFF_NAME);
    await page.getByTestId("staff-role-input").selectOption("therapist");
    await page.getByTestId("add-staff-button").click();
    await expectToast(page, "Staff added");
    await expect(page.getByTestId("staff-list")).toContainText(STAFF_NAME);
  });

  // ── 3. Ops board: walk-in check-in shows occupied room ────────────────────
  test("walk-in check-in marks room as occupied", async ({ page }) => {
    await setupRoomAndStaff(page);
    const walkinName = `WalkIn ${RUN_ID}`;
    await checkinAndStartService(page, walkinName);

    const roomCard = page.getByTestId(`room-card-${ROOM_CODE}`);
    await expect(roomCard).toContainText(walkinName);
    await expect(roomCard).toContainText("occupied");
  });

  // ── 4. Full walk-in workflow: check-in → service → skip checkout ──────────
  test("full walk-in workflow: check-in, end service, skip checkout", async ({ page }) => {
    await setupRoomAndStaff(page);
    const walkinName = `Skip ${RUN_ID}`;
    await checkinAndStartService(page, walkinName);

    const roomCard = page.getByTestId(`room-card-${ROOM_CODE}`);
    await expect(roomCard).toContainText("occupied");

    await endService(page);
    await openCheckoutModal(page, walkinName);

    await page.getByRole("button", { name: /skip/i }).click();
    await expectToast(page, "Checked out");

    await expect(roomCard).toContainText("available");
    await expect(roomCard).toContainText("Empty");
  });

  // ── 5. Checkout with copay fields ─────────────────────────────────────────
  test("checkout collects copay, WD, and patient signed fields", async ({ page }) => {
    await setupRoomAndStaff(page);
    const patientName = `Copay ${RUN_ID}`;
    await checkinAndStartService(page, patientName);
    await endService(page);
    await openCheckoutModal(page, patientName);

    // Verify all copay fields are present
    await expect(page.locator("#co-cc")).toBeVisible();
    await expect(page.locator("#co-wd")).toBeVisible();
    await expect(page.locator("#co-signed")).toBeVisible();
    await expect(page.locator("#co-ps")).toBeVisible();
    await expect(page.locator("#co-pm")).toBeVisible();

    // Fill in copay details
    await page.locator("#co-cc").fill("25");
    await page.locator("#co-ps").selectOption("copay_collected");
    await page.locator("#co-pm").selectOption("cash");
    await page.locator("#co-wd").check();
    await page.locator("#co-signed").check();

    await expect(page.locator("#co-wd")).toBeChecked();
    await expect(page.locator("#co-signed")).toBeChecked();

    await page.getByRole("button", { name: /check out/i }).first().click();
    await expectToast(page, "Checked out");

    await expect(page.getByTestId(`room-card-${ROOM_CODE}`)).toContainText("available");
  });

  // ── 6. Patients tab: create and view patient ──────────────────────────────
  test("can create a patient and view their detail", async ({ page }) => {
    await openTab(page, "tab-patients");
    await page.getByRole("button", { name: /new/i }).click();

    await page.locator("#np-fn").fill(PATIENT_FIRST);
    await page.locator("#np-ln").fill(PATIENT_LAST);
    await page.locator("#np-dob").fill("1990-05-15");
    await page.locator("#np-phone").fill("555-9999");
    await page.getByRole("button", { name: /create patient/i }).click();
    await expectToast(page, "Patient created");

    // Search and view
    await page.locator("#pt-search").fill(PATIENT_LAST);
    await page.locator("#pt-search").press("Enter");
    await page.getByRole("button", { name: /view/i }).first().click();

    // Detail modal opens
    await expect(page.locator(".modal-box")).toBeVisible();
    await expect(page.locator(".modal-box")).toContainText(PATIENT_FULL);
    await expect(page.locator(".modal-box")).toContainText("Visit History");
  });

  // ── 7. Patient detail has sign sheet PDF link ─────────────────────────────
  test("patient detail modal shows sign sheet PDF link", async ({ page }) => {
    await openTab(page, "tab-patients");
    await page.getByRole("button", { name: /new/i }).click();

    await page.locator("#np-fn").fill("PDF");
    await page.locator("#np-ln").fill(`Link${RUN_ID}`);
    await page.locator("#np-dob").fill("1985-03-20");
    await page.locator("#np-phone").fill("555-8888");
    await page.getByRole("button", { name: /create patient/i }).click();
    await expectToast(page, "Patient created");

    await page.getByRole("button", { name: /view/i }).first().click();

    const pdfLink = page.locator(".modal-box a[href*='sign-sheet.pdf']");
    await expect(pdfLink).toBeVisible();
    await expect(pdfLink).toContainText("Sign Sheet PDF");
  });

  // ── 8. Full workflow with copay: shows in report summary ──────────────────
  test("completed visit with copay appears in report summary", async ({ page }) => {
    await setupRoomAndStaff(page);
    const patientName = `Report ${RUN_ID}`;
    await checkinAndStartService(page, patientName);
    await endService(page);
    await openCheckoutModal(page, patientName);
    await page.locator("#co-cc").fill("45");
    await page.locator("#co-wd").check();
    await page.getByRole("button", { name: /check out/i }).first().click();
    await expectToast(page, "Checked out");

    await openTab(page, "tab-report");

    // Daily summary section should load automatically
    await expect(page.locator("#sum-stats")).toBeVisible({ timeout: 10_000 });

    // At least 1 check-in today
    const ciCount = await page.locator("#sum-ci").textContent();
    expect(parseInt(ciCount ?? "0")).toBeGreaterThanOrEqual(1);

    // Visit table should contain our patient
    await expect(page.locator("#sum-table")).toContainText(patientName);
    await expect(page.locator("#sum-table")).toContainText("$45");
  });

  // ── 9. Event log shows audit trail ────────────────────────────────────────
  test("event log records check-in and checkout audit trail", async ({ page }) => {
    await setupRoomAndStaff(page);
    const patientName = `Audit ${RUN_ID}`;
    await checkinAndStartService(page, patientName);
    await endService(page);
    await openCheckoutModal(page, patientName);
    await page.getByRole("button", { name: /skip/i }).click();
    await expectToast(page, "Checked out");

    await openTab(page, "tab-events");
    const events = page.getByTestId("events-list");
    await expect(events).toContainText("PATIENT_CHECKIN");
    await expect(events).toContainText("SERVICE_STARTED");
    await expect(events).toContainText("SERVICE_COMPLETED");
    await expect(events).toContainText("PATIENT_CHECKOUT");
  });

  // ── 10. Treatment modality: add and appear in records ─────────────────────
  test("can add a treatment modality and see it in treatment records", async ({ page }) => {
    await setupRoomAndStaff(page);
    const patientName = `Tx ${RUN_ID}`;
    await checkinAndStartService(page, patientName);

    const visitRow = page.locator("#visits-list tr").filter({ hasText: patientName });
    await expect(visitRow).toContainText("in_service");
    await visitRow.getByRole("button", { name: /tx/i }).click();

    await expect(page.locator("#modal, .modal-bg")).toBeVisible();
    await page.locator("#trt-mod").selectOption("E-stim");
    await page.locator("#trt-dur").fill("20");
    await page.getByRole("button", { name: /add treatment/i }).click();
    await expectToast(page, "Treatment added");

    // Close modal
    await page.getByRole("button", { name: /×/ }).click();

    await openTab(page, "tab-treatments");
    await page.getByRole("button", { name: /search/i }).click();

    await expect(page.locator("#treatment-records-list")).toContainText(patientName);
  });

  // ── 11. Room status buttons disabled when occupied ────────────────────────
  test("room status buttons are disabled while room is occupied", async ({ page }) => {
    await setupRoomAndStaff(page);
    await checkinAndStartService(page, `Status ${RUN_ID}`);

    const roomCard = page.getByTestId(`room-card-${ROOM_CODE}`);
    await expect(roomCard).toContainText("occupied");

    await expect(roomCard.getByTitle("Free")).toBeDisabled();
    await expect(roomCard.getByTitle("Cleaning")).toBeDisabled();
    await expect(roomCard.getByTitle("OOS")).toBeDisabled();
  });

  // ── 12. Reload persists room occupancy ───────────────────────────────────
  test("page reload keeps in-service room occupancy visible", async ({ page }) => {
    await setupRoomAndStaff(page);
    const patientName = `Persist ${RUN_ID}`;
    await checkinAndStartService(page, patientName);

    const roomCard = page.getByTestId(`room-card-${ROOM_CODE}`);
    await expect(roomCard).toContainText(patientName);
    await expect(roomCard).toContainText("occupied");

    await page.reload();
    await expect(roomCard).toContainText(patientName);
    await expect(roomCard).toContainText("occupied");
  });

  // ── 13. Insurance-only checkout path ──────────────────────────────────────
  test("checkout with insurance-only payment path works", async ({ page }) => {
    await setupRoomAndStaff(page);
    const patientName = `Insured ${RUN_ID}`;
    await checkinAndStartService(page, patientName);
    await endService(page);
    await openCheckoutModal(page, patientName);

    await page.locator("#co-ps").selectOption("insurance_only");
    await page.getByRole("button", { name: /check out/i }).first().click();
    await expectToast(page, "Checked out");
    await expect(page.getByTestId(`room-card-${ROOM_CODE}`)).toContainText("available");
  });
});
