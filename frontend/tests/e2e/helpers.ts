import { expect, type APIRequestContext, type Page } from "@playwright/test";

export async function resetLocalData(request: APIRequestContext) {
  const response = await request.post("/prototype/test/reset");
  expect(response.ok()).toBeTruthy();
}

export async function apiPost(request: APIRequestContext, path: string, payload: Record<string, unknown>) {
  const response = await request.post(`/prototype${path}`, { data: payload });
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

export async function apiGet(request: APIRequestContext, path: string) {
  const response = await request.get(`/prototype${path}`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

export async function seedPatient(
  request: APIRequestContext,
  firstName: string,
  lastName: string,
  mrn: string,
) {
  return apiPost(request, "/patients", {
    first_name: firstName,
    last_name: lastName,
    date_of_birth: "1990-01-01",
    phone: "555-0000",
    mrn,
  });
}

export async function seedAppointment(
  request: APIRequestContext,
  patientId: string,
  providerId: string,
  appointmentTime: string,
  appointmentType = "regular",
) {
  const today = new Date().toISOString().slice(0, 10);
  return apiPost(request, "/appointments", {
    patient_id: patientId,
    provider_id: providerId,
    appointment_date: today,
    appointment_time: appointmentTime,
    appointment_type: appointmentType,
  });
}

export async function openTab(page: Page, testId: string) {
  await page.getByTestId(testId).click();
}

export async function expectToast(page: Page, text: string) {
  await expect(page.getByTestId("toast")).toContainText(text);
}
