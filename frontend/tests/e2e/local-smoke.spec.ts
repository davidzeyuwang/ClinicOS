/**
 * Local E2E test file — thin wrapper around the two shared suites.
 *
 * Registers:
 *   1. clinic-harness-suite  — 31 focused UI tests (resetLocalData before each)
 *   2. clinic-smoke-suite    — 11-step multi-patient smoke scenario
 *
 * Both suites run against the local SQLite dev server.
 * The prod counterpart (prod-smoke.spec.ts) registers the same suites
 * via prod-specific adapters.
 */

import { expect, type APIRequestContext } from "@playwright/test";

import {
  apiGet,
  apiPost,
  resetLocalData,
} from "./helpers";
import {
  registerHarnessTests,
  type HarnessEnv,
} from "./shared/clinic-harness-suite";
import {
  registerSmokeTests,
  type PatientSpec,
  type SmokeEnv,
} from "./shared/clinic-smoke-suite";

// ── Local harness env ─────────────────────────────────────────────────────────

const localHarnessEnv: HarnessEnv = {
  suiteName: "ClinicOS UI harness",
  roomCode: "R1",
  roomName: "Room 1",
  altRoomCode: "TRA",
  altRoomName: "Treatment Room A",
  staffName: "Alice PT",
  altStaffName: "Dr. Sarah Chen",
  testRoomCode: "R1",
  testRoomName: "Room 1",
  testStaffName: "Bob OT",
  retireServiceTypeName: "OT",
  createRetireTarget: false,
  createViaUI: true,
  exactCounts: true,
  async beforeEach(request: APIRequestContext, page: import("@playwright/test").Page) {
    await resetLocalData(request);
    await page.goto("/ui/index.html");
  },
};

registerHarnessTests(localHarnessEnv);

// ── Local smoke env ───────────────────────────────────────────────────────────
//
// Runs the same 11-step multi-patient scenario as prod-smoke.spec.ts,
// using resetLocalData + app-API verify (no Supabase REST needed).

const _SMOKE_PATIENTS: PatientSpec[] = [
  {
    first: "LocalA", last: "Smoke", full: "LocalA Smoke", mrn: "LCL-A001",
    dob: "1985-06-15", phone: "555-2001",
    copay: "45", paymentStatus: "copay_collected", paymentMethod: "card",
    treatments: [
      { modality: "E-stim",  duration: "30" },
      { modality: "Massage", duration: "20" },
    ],
  },
  {
    first: "LocalB", last: "Smoke", full: "LocalB Smoke", mrn: "LCL-B001",
    dob: "1990-03-22", phone: "555-2002",
    copay: "60", paymentStatus: "copay_collected", paymentMethod: "cash",
    treatments: [{ modality: "Acupuncture", duration: "25" }],
  },
  {
    first: "LocalC", last: "Smoke", full: "LocalC Smoke", mrn: "LCL-C001",
    dob: "1975-11-08", phone: "555-2003",
    copay: "",
    paymentStatus: "no_charge", paymentMethod: "",
    treatments: [{ modality: "Cupping", duration: "45" }],
  },
];

const _SMOKE_A_V2: PatientSpec = {
  ..._SMOKE_PATIENTS[0],
  copay: "30", paymentStatus: "copay_collected", paymentMethod: "card",
  treatments: [{ modality: "OT", duration: "15" }],
};

const _localSmokeEnv: SmokeEnv = {
  suiteName: "Smoke — local (SQLite)",
  roomCode: "LS1",
  patients: _SMOKE_PATIENTS,
  patientV2: _SMOKE_A_V2,

  async setup(request: APIRequestContext) {
    await resetLocalData(request);
    await apiPost(request, "/admin/rooms", { name: "Smoke Room 1", code: "LS1", room_type: "treatment" });
    await apiPost(request, "/admin/staff", { name: "Smoke Staff", role: "therapist" });
    const ids: string[] = [];
    for (const pt of _SMOKE_PATIENTS) {
      const r = await apiPost(request, "/patients", {
        first_name: pt.first, last_name: pt.last,
        date_of_birth: pt.dob, phone: pt.phone, mrn: pt.mrn,
      });
      ids.push(r.patient_id);
      console.log(`  Created patient ${pt.full} → ${r.patient_id}`);
    }
    return ids;
  },

  async verifyPatient(request: APIRequestContext, pt: PatientSpec, pid: string, expectedVisitCount = 1, visitIndex = 0) {
    type VisitRow = {
      visit_id: string; status: string; copay_collected: number | null;
      payment_status: string; payment_method: string | null;
      wd_verified: boolean; patient_signed: boolean; check_in_time: string;
      treatments: Array<{ modality: string; duration_minutes: number }>;
    };

    const { visits: raw } = await apiGet(request, `/patients/${pid}/visits`);
    const visits: VisitRow[] = [...raw].sort(
      (a: VisitRow, b: VisitRow) =>
        new Date(a.check_in_time).getTime() - new Date(b.check_in_time).getTime(),
    );
    expect(visits.length, `${pt.full}: expected ${expectedVisitCount} visit(s)`).toBe(expectedVisitCount);
    const v = visits[visitIndex];

    const expectedCopay = pt.copay === "" ? null : parseFloat(pt.copay);
    expect(v.status,          `${pt.full}: status`).toBe("checked_out");
    expect(v.copay_collected, `${pt.full}: copay_collected`).toBe(expectedCopay);
    expect(v.payment_status,  `${pt.full}: payment_status`).toBe(pt.paymentStatus);
    if (pt.paymentMethod) {
      expect(v.payment_method, `${pt.full}: payment_method`).toBe(pt.paymentMethod);
    }
    expect(v.wd_verified,    `${pt.full}: wd_verified`).toBe(true);
    expect(v.patient_signed, `${pt.full}: patient_signed`).toBe(true);
    console.log(`  ✓ Visit DB ok: ${pt.full}  status=${v.payment_status}  copay=${v.copay_collected}`);

    const storedModalities = v.treatments.map((t) => t.modality);
    console.log(`  Treatments in DB for ${pt.full}: [${storedModalities.join(", ")}]`);
    expect(v.treatments.length, `${pt.full}: expected ${pt.treatments.length} treatment(s)`).toBe(pt.treatments.length);
    for (const tx of pt.treatments) {
      expect(storedModalities, `${pt.full}: treatment "${tx.modality}" missing`).toContain(tx.modality);
      const row = v.treatments.find((r) => r.modality === tx.modality)!;
      expect(row.duration_minutes, `${pt.full}: ${tx.modality} duration`).toBe(parseInt(tx.duration));
    }
    console.log(`  ✓ Treatments DB ok: ${pt.full}  ${storedModalities.join(", ")}`);

    const { events } = await apiGet(request, "/events");
    const eventTypes = events
      .filter((e: { event_type: string; payload: Record<string, unknown> }) => e.payload?.visit_id === v.visit_id)
      .map((e: { event_type: string }) => e.event_type);
    for (const evt of ["PATIENT_CHECKIN", "SERVICE_STARTED", "SERVICE_COMPLETED", "PATIENT_CHECKOUT"]) {
      expect(eventTypes, `${pt.full}: missing event ${evt}`).toContain(evt);
    }
    const txCount = eventTypes.filter((t: string) => t === "TREATMENT_ADDED").length;
    expect(txCount, `${pt.full}: expected ${pt.treatments.length} TREATMENT_ADDED`).toBe(pt.treatments.length);
    console.log(`  ✓ Events DB ok: ${pt.full}  ${[...new Set(eventTypes)].join(", ")}`);

    return v.visit_id;
  },

  async teardown(_request: APIRequestContext, _patientIds: string[]) {},
};

registerSmokeTests(_localSmokeEnv);
