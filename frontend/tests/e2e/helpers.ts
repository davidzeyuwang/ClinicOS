import { expect, type APIRequestContext, type Page } from "@playwright/test";

export async function resetLocalData(request: APIRequestContext) {
  const response = await request.post("/prototype/test/reset");
  expect(response.ok()).toBeTruthy();
}

export async function openTab(page: Page, testId: string) {
  await page.getByTestId(testId).click();
}

export async function expectToast(page: Page, text: string) {
  await expect(page.getByTestId("toast")).toContainText(text);
}
