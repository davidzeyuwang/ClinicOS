import { test, expect } from "@playwright/test";

import { expectToast, openTab, resetLocalData } from "./helpers";

async function checkoutCompletedVisit(page: import("@playwright/test").Page, patientName: string) {
  const visitRow = page.locator("#visits-list tr").filter({ hasText: patientName });
  await expect(visitRow).toContainText("service_completed");
  await visitRow.getByRole("button", { name: /out/i }).click();
}

test.describe("ClinicOS UI harness", () => {
  test.beforeEach(async ({ page, request }) => {
    await resetLocalData(request);
    await page.goto("/ui/index.html");
  });

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

  test("ops board walk-in flow can be completed end-to-end", async ({ page }) => {
    await openTab(page, "tab-admin");

    await page.getByTestId("room-name-input").fill("Room 1");
    await page.getByTestId("room-code-input").fill("R1");
    await page.getByTestId("add-room-button").click();
    await expectToast(page, "Room added");

    await openTab(page, "tab-ops");
    await page.getByTestId("room-checkin-R1").click();
    await page.locator("#rc-search").fill("Walk In John");
    await page.locator("#rc-staff").selectOption({ index: 0 });
    await page.getByRole("button", { name: "Check In & Start" }).click();
    await expectToast(page, "room assigned");

    const roomCard = page.getByTestId("room-card-R1");
    await expect(roomCard).toContainText("Walk In John");
    await expect(roomCard).toContainText("occupied");

    await page.getByTestId("room-end-service-R1").click();
    await expectToast(page, "Service ended");
    await checkoutCompletedVisit(page, "Walk In John");
    await page.getByRole("button", { name: "Skip payment" }).click();
    await expectToast(page, "Checked out");

    await expect(roomCard).toContainText("available");
    await expect(roomCard).toContainText("Empty");
  });

  test("report and event log reflect completed visit", async ({ page }) => {
    await openTab(page, "tab-admin");

    await page.getByTestId("room-name-input").fill("Room 1");
    await page.getByTestId("room-code-input").fill("R1");
    await page.getByTestId("add-room-button").click();
    await expectToast(page, "Room added");

    await openTab(page, "tab-ops");
    await page.getByTestId("room-checkin-R1").click();
    await page.locator("#rc-search").fill("Regression Jane");
    await page.locator("#rc-staff").selectOption({ index: 0 });
    await page.getByRole("button", { name: "Check In & Start" }).click();
    await expectToast(page, "room assigned");
    await page.getByTestId("room-end-service-R1").click();
    await expectToast(page, "Service ended");
    await checkoutCompletedVisit(page, "Regression Jane");
    await page.locator("#co-ps").selectOption("copay_collected");
    await page.locator("#co-amt").fill("30");
    await page.locator("#co-pm").selectOption("card");
    await page.locator("#modal .btn-primary").click();
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
});
