import { test, expect } from "@playwright/test";

import { expectToast, openTab, resetLocalData } from "./helpers";

// ── Shared setup helpers ──────────────────────────────────────────────────────

async function setupRoomAndStaff(page: import("@playwright/test").Page) {
  await openTab(page, "tab-admin");
  await page.getByTestId("room-name-input").fill("Room 1");
  await page.getByTestId("room-code-input").fill("R1");
  await page.getByTestId("add-room-button").click();
  await expectToast(page, "Room added");
  await page.getByTestId("staff-name-input").fill("Alice PT");
  await page.getByTestId("staff-role-input").selectOption("therapist");
  await page.getByTestId("add-staff-button").click();
  await expectToast(page, "Staff added");
}

async function checkinAndStartService(
  page: import("@playwright/test").Page,
  patientName: string
) {
  await openTab(page, "tab-ops");
  await page.getByTestId("room-checkin-R1").click();
  await page.locator("#rc-search").fill(patientName);
  await page.locator("#rc-staff").selectOption({ index: 0 });
  await page.getByRole("button", { name: "Check In & Start" }).click();
  await expectToast(page, "room assigned");
}

async function endService(
  page: import("@playwright/test").Page,
) {
  await page.getByTestId("room-end-service-R1").click();
  await expectToast(page, "Service ended");
}

/** Click the checkout button from the active visits table. */
async function openCheckoutModal(
  page: import("@playwright/test").Page,
  patientName: string
) {
  const visitRow = page.locator("#visits-list tr").filter({ hasText: patientName });
  await expect(visitRow).toContainText("service_completed");
  await visitRow.getByRole("button", { name: /out/i }).click();
}

// ── Test suite ────────────────────────────────────────────────────────────────

test.describe("ClinicOS UI harness", () => {
  test.beforeEach(async ({ page, request }) => {
    await resetLocalData(request);
    await page.goto("/ui/index.html");
  });

  // ── 1. Admin setup ──────────────────────────────────────────────────────────
  test("admin can create room and staff", async ({ page }) => {
    await openTab(page, "tab-admin");

    await page.getByTestId("room-name-input").fill("Room 1");
    await page.getByTestId("room-code-input").fill("R1");
    await page.getByTestId("add-room-button").click();
    await expectToast(page, "Room added");
    await expect(page.getByTestId("room-list-item-R1")).toContainText("Room 1");

    await page.getByTestId("staff-name-input").fill("Bob OT");
    await page.getByTestId("staff-role-input").selectOption("therapist");
    await page.getByTestId("staff-license-input").fill("OT-002");
    await page.getByTestId("add-staff-button").click();
    await expectToast(page, "Staff added");
    await expect(page.getByTestId("staff-list")).toContainText("Bob OT");
  });

  // ── 2. Walk-in quick checkout (skip payment) ────────────────────────────────
  test("ops board walk-in flow: skip payment checkout", async ({ page }) => {
    await setupRoomAndStaff(page);
    await checkinAndStartService(page, "Walk In John");

    const roomCard = page.getByTestId("room-card-R1");
    await expect(roomCard).toContainText("Walk In John");
    await expect(roomCard).toContainText("occupied");

    await endService(page);
    await openCheckoutModal(page, "Walk In John");

    // New modal: "Skip — just check out" button
    await page.getByRole("button", { name: /skip/i }).click();
    await expectToast(page, "Checked out");

    await expect(roomCard).toContainText("available");
    await expect(roomCard).toContainText("Empty");
  });

  // ── 3. Checkout with copay CC + WD verified + patient signed ───────────────
  test("checkout collects copay CC, WD verified, and patient signed", async ({ page }) => {
    await setupRoomAndStaff(page);
    await checkinAndStartService(page, "Copay Patient");
    await endService(page);
    await openCheckoutModal(page, "Copay Patient");

    // New fields in the enhanced checkout modal
    await page.locator("#co-cc").fill("25");
    await page.locator("#co-ps").selectOption("copay_collected");
    await page.locator("#co-pm").selectOption("cash");
    await page.locator("#co-wd").check();
    await page.locator("#co-signed").check();

    // Verify checkboxes are checked
    await expect(page.locator("#co-wd")).toBeChecked();
    await expect(page.locator("#co-signed")).toBeChecked();

    // Click "Check Out" (primary button)
    await page.getByRole("button", { name: /check out/i }).first().click();
    await expectToast(page, "Checked out");

    // Room should be available again
    await expect(page.getByTestId("room-card-R1")).toContainText("available");
  });

  // ── 4. Checkout modal defaults and field layout ─────────────────────────────
  test("checkout modal has copay CC, WD, and signed fields", async ({ page }) => {
    await setupRoomAndStaff(page);
    await checkinAndStartService(page, "Field Test Patient");
    await endService(page);
    await openCheckoutModal(page, "Field Test Patient");

    // Check all new fields are present
    await expect(page.locator("#co-cc")).toBeVisible();
    await expect(page.locator("#co-wd")).toBeVisible();
    await expect(page.locator("#co-signed")).toBeVisible();
    await expect(page.locator("#co-ps")).toBeVisible();
    await expect(page.locator("#co-pm")).toBeVisible();

    // WD and signed should default unchecked
    await expect(page.locator("#co-wd")).not.toBeChecked();
    await expect(page.locator("#co-signed")).not.toBeChecked();

    // Both action buttons present
    await expect(page.getByRole("button", { name: /check out/i }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /skip/i })).toBeVisible();
  });

  // ── 5. Patient detail shows visit history ──────────────────────────────────
  test("patient detail shows visit history with copay info", async ({ page }) => {
    await setupRoomAndStaff(page);

    // Create a patient via the Patients tab
    await openTab(page, "tab-patients");
    await page.getByRole("button", { name: /new/i }).click();
    await page.locator("#np-fn").fill("History");
    await page.locator("#np-ln").fill("Patient");
    await page.locator("#np-phone").fill("555-9999");
    await page.getByRole("button", { name: /create patient/i }).click();
    await expectToast(page, "Patient created");

    // Check them in using the ops board, using autocomplete
    await openTab(page, "tab-ops");
    await page.getByTestId("room-checkin-R1").click();
    await page.locator("#rc-search").fill("History");
    // Wait for autocomplete suggestion and select it
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

    // Now open patient detail and verify visit history
    await openTab(page, "tab-patients");
    await page.locator("#pt-search").fill("History");
    await page.locator("#pt-search").press("Enter");
    await page.getByRole("button", { name: /view/i }).first().click();

    // Modal should show visit history section
    await expect(page.locator(".modal-box")).toContainText("Visit History");
    // Should show the copay amount
    await expect(page.locator(".modal-box")).toContainText("$30.00");
    // WD and signed columns should show check marks
    await expect(page.locator(".modal-box")).toContainText("✓");
  });

  // ── 6. Patient detail has Sign Sheet PDF download button ───────────────────
  test("patient detail has sign sheet PDF download link", async ({ page }) => {
    await openTab(page, "tab-patients");
    await page.getByRole("button", { name: /new/i }).click();
    await page.locator("#np-fn").fill("PDF");
    await page.locator("#np-ln").fill("Downloader");
    await page.getByRole("button", { name: /create patient/i }).click();
    await expectToast(page, "Patient created");

    await page.getByRole("button", { name: /view/i }).first().click();

    // PDF download link should be present
    const pdfLink = page.locator(".modal-box a[href*='sign-sheet.pdf']");
    await expect(pdfLink).toBeVisible();
    await expect(pdfLink).toContainText("Sign Sheet PDF");
  });

  // ── 7. Report tab daily summary shows today's visits ───────────────────────
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

    // The daily summary date is set to today automatically on tab open
    await expect(page.locator("#sum-stats")).toBeVisible({ timeout: 5000 });

    // Check-in count should be at least 1
    const ciCount = await page.locator("#sum-ci").textContent();
    expect(parseInt(ciCount ?? "0")).toBeGreaterThanOrEqual(1);

    // Checkout count should be at least 1
    const coCount = await page.locator("#sum-co").textContent();
    expect(parseInt(coCount ?? "0")).toBeGreaterThanOrEqual(1);

    // Copay total should reflect $45
    await expect(page.locator("#sum-copay")).toContainText("$45");

    // Visit table should show the patient
    await expect(page.locator("#sum-table")).toContainText("Summary Test");
    // WD column should be checked
    await expect(page.locator("#sum-table")).toContainText("✓");
  });

  // ── 8. Report + event log (existing test, updated for new modal) ────────────
  test("report and event log reflect completed visit", async ({ page }) => {
    await setupRoomAndStaff(page);
    await checkinAndStartService(page, "Regression Jane");
    await endService(page);
    await openCheckoutModal(page, "Regression Jane");

    // Use new co-cc field for copay amount
    await page.locator("#co-cc").fill("30");
    await page.locator("#co-ps").selectOption("copay_collected");
    await page.locator("#co-pm").selectOption("card");
    await page.getByRole("button", { name: /check out/i }).first().click();
    await expectToast(page, "Checked out");

    await openTab(page, "tab-report");
    await page.getByTestId("generate-report-button").click();
    await expectToast(page, "Generated");
    await expect(page.getByTestId("report-content")).toBeVisible();
    await expect(page.locator("#rpt-ci")).toHaveText("1");
    await expect(page.locator("#rpt-co")).toHaveText("1");
    await expect(page.locator("#rpt-svc")).toHaveText("1");

    await openTab(page, "tab-events");
    const events = page.getByTestId("events-list");
    await expect(events).toContainText("PATIENT_CHECKIN");
    await expect(events).toContainText("SERVICE_STARTED");
    await expect(events).toContainText("SERVICE_COMPLETED");
    await expect(events).toContainText("PATIENT_CHECKOUT");
  });

  // ── 9. Disabled status buttons when room occupied ──────────────────────────
  test("free/clean/OOS buttons are disabled when room is occupied", async ({ page }) => {
    await setupRoomAndStaff(page);
    await checkinAndStartService(page, "Disable Test");

    const roomCard = page.getByTestId("room-card-R1");
    await expect(roomCard).toContainText("occupied");

    // All three status-change buttons should be disabled
    const freeBtn  = roomCard.getByTitle("Free");
    const cleanBtn = roomCard.getByTitle("Cleaning");
    const oosBtn   = roomCard.getByTitle("OOS");
    await expect(freeBtn).toBeDisabled();
    await expect(cleanBtn).toBeDisabled();
    await expect(oosBtn).toBeDisabled();
  });

  // ── 10. Deleted patient does not appear in typeahead ──────────────────────
  test("deleted patient does not appear in check-in typeahead", async ({ page }) => {
    // Create then delete a patient
    await openTab(page, "tab-patients");
    await page.getByRole("button", { name: /new/i }).click();
    await page.locator("#np-fn").fill("Ghost");
    await page.locator("#np-ln").fill("Patient");
    await page.getByRole("button", { name: /create patient/i }).click();
    await expectToast(page, "Patient created");

    // Delete them
    await page.locator("#pt-search").fill("Ghost");
    await page.locator("#pt-search").press("Enter");
    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: /delete/i }).first().click();
    await expectToast(page, "Patient removed");

    // Set up a room
    await openTab(page, "tab-admin");
    await page.getByTestId("room-name-input").fill("Room 1");
    await page.getByTestId("room-code-input").fill("R1");
    await page.getByTestId("add-room-button").click();
    await expectToast(page, "Room added");

    // Open check-in and type the deleted patient's name
    await openTab(page, "tab-ops");
    await page.getByTestId("room-checkin-R1").click();
    await page.locator("#rc-search").fill("Ghost");
    await expect(page.locator("#rc-results")).toBeVisible();
    await expect(page.locator("#rc-results")).toContainText("No matches");
  });
});
