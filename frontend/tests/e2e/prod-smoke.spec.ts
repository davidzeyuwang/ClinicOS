/**
 * Production smoke — thin wrapper around the shared clinic smoke suite.
 *
 * Adapter responsibilities:
 *   setup:         warm up Vercel, reset room C1, create patients via app API
 *   verifyPatient: Supabase REST (direct table queries, no round-trip through app)
 *   teardown:      hard-delete all created records via Supabase REST
 *
 * Requires stable rooms/staff pre-seeded:
 *   python3 scripts/seed_prod.py
 *
 * Run:
 *   npx playwright test --config=playwright.smoke.config.ts
 */

import { expect, type APIRequestContext } from "@playwright/test";
import {
  registerSmokeTests,
  type PatientSpec,
  type SmokeEnv,
} from "./shared/clinic-smoke-suite";
import {
  registerHarnessTests,
  type HarnessEnv,
} from "./shared/clinic-harness-suite";
import {
  registerAuthTests,
  type AuthEnv,
  type AuthCreated,
} from "./shared/auth-suite";

// ── Patient definitions ───────────────────────────────────────────────────────

/** Unique suffix per run — prevents MRN collisions between concurrent CI runs. */
const RUN_SUFFIX = Date.now().toString().slice(-6);

const PATIENTS: PatientSpec[] = [
  {
    first: "SmokeA",
    last: RUN_SUFFIX,
    full: `SmokeA ${RUN_SUFFIX}`,
    mrn: `SMKA${RUN_SUFFIX}`,
    dob: "1985-06-15",
    phone: "555-1001",
    copay: "45",
    paymentStatus: "copay_collected",
    paymentMethod: "card",
    treatments: [
      { modality: "E-stim",  duration: "30" },
      { modality: "Massage", duration: "20" },
    ],
  },
  {
    first: "SmokeB",
    last: RUN_SUFFIX,
    full: `SmokeB ${RUN_SUFFIX}`,
    mrn: `SMKB${RUN_SUFFIX}`,
    dob: "1990-03-22",
    phone: "555-1002",
    copay: "60",
    paymentStatus: "copay_collected",
    paymentMethod: "cash",
    treatments: [
      { modality: "Acupuncture", duration: "25" },
    ],
  },
  {
    first: "SmokeC",
    last: RUN_SUFFIX,
    full: `SmokeC ${RUN_SUFFIX}`,
    mrn: `SMKC${RUN_SUFFIX}`,
    dob: "1975-11-08",
    phone: "555-1003",
    copay: "",          // no_charge — frontend skips copay field, DB stores null
    paymentStatus: "no_charge",
    paymentMethod: "",
    treatments: [
      { modality: "Cupping", duration: "45" },
    ],
  },
];

const SMOKE_A_V2: PatientSpec = {
  ...PATIENTS[0],
  copay: "30",
  paymentStatus: "copay_collected",
  paymentMethod: "card",
  treatments: [{ modality: "OT", duration: "15" }],
};

// ── Supabase helpers ──────────────────────────────────────────────────────────

async function supaGet<T = Record<string, unknown>[]>(
  request: APIRequestContext,
  pathAndQuery: string,
): Promise<T> {
  const url = process.env.SUPABASE_URL!;
  const key = process.env.SUPABASE_SERVICE_KEY!;
  const resp = await request.get(`${url}/rest/v1/${pathAndQuery}`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
  });
  if (!resp.ok()) {
    throw new Error(`supaGet /${pathAndQuery} → ${resp.status()}: ${await resp.text()}`);
  }
  return resp.json();
}

/**
 * Force a prod room to available status by checking out any lingering visits
 * via direct Supabase REST (bypasses app business logic for test isolation).
 */
async function forceProdRoomAvailable(request: APIRequestContext, roomCode: string) {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY;
  if (!url || !key) return;
  const hdrs = {
    apikey: key,
    Authorization: `Bearer ${key}`,
    "Content-Type": "application/json",
    Prefer: "return=minimal",
  };
  const rr = await request.get(`${url}/rest/v1/rooms?select=room_id&code=eq.${roomCode}`, {
    headers: hdrs,
  });
  const rooms: Array<{ room_id: string }> = await rr.json();
  if (!rooms.length) return;
  const rid = rooms[0].room_id;
  const now = new Date().toISOString();
  await request.patch(
    `${url}/rest/v1/visits?room_id=eq.${rid}&status=neq.checked_out`,
    { headers: hdrs, data: { status: "checked_out", check_out_time: now } },
  );
  await request.patch(`${url}/rest/v1/rooms?room_id=eq.${rid}`, {
    headers: hdrs,
    data: { status: "available" },
  });
}

// ── Prod adapter ──────────────────────────────────────────────────────────────

const prodEnv: SmokeEnv = {
  suiteName: "Smoke — prod (Vercel + Supabase)",
  roomCode: "C1",
  patients: PATIENTS,
  patientV2: SMOKE_A_V2,

  async setup(request) {
    // Warm up Vercel cold start
    console.log("  Warming up server...");
    await request.get("/health");
    await request.get("/prototype/ops");
    console.log("  Server warmed up");

    // Reset room so any lingering visit doesn't block check-in
    await forceProdRoomAvailable(request, "C1");
    console.log("  Reset room C1: cleared lingering visits, status → available");

    // Create the 3 patients
    const ids: string[] = [];
    for (const pt of PATIENTS) {
      const r = await request.post("/prototype/patients", {
        data: {
          first_name:    pt.first,
          last_name:     pt.last,
          date_of_birth: pt.dob,
          phone:         pt.phone,
          mrn:           pt.mrn,
        },
      });
      if (!r.ok()) throw new Error(`createPatient(${pt.full}) failed: ${await r.text()}`);
      const id = (await r.json()).patient_id;
      ids.push(id);
      console.log(`  Created patient ${pt.full} → ${id}`);
    }
    return ids;
  },

  async verifyPatient(request, pt, pid, expectedVisitCount = 1, visitIndex = 0) {
    type VisitRow = {
      visit_id: string; status: string; copay_collected: number | null;
      payment_status: string; payment_method: string | null;
      wd_verified: boolean; patient_signed: boolean;
    };
    type TxRow = { modality: string; duration_minutes: number };
    type EventRow = { event_type: string };

    const visits = await supaGet<VisitRow[]>(
      request,
      `visits?select=visit_id,status,copay_collected,payment_status,payment_method,wd_verified,patient_signed&patient_id=eq.${pid}&order=check_in_time.asc`,
    );
    expect(visits.length, `${pt.full}: expected ${expectedVisitCount} visit(s)`).toBe(
      expectedVisitCount,
    );
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
    console.log(
      `  ✓ Visit DB ok: ${pt.full}  status=${v.payment_status}  copay=${v.copay_collected}`,
    );

    const txRows = await supaGet<TxRow[]>(
      request,
      `visit_treatments?select=modality,duration_minutes&visit_id=eq.${v.visit_id}`,
    );
    const storedModalities = txRows.map((r) => r.modality);
    console.log(`  Treatments in DB for ${pt.full}: [${storedModalities.join(", ")}]`);
    expect(
      txRows.length,
      `${pt.full}: expected ${pt.treatments.length} treatment(s), got ${txRows.length}`,
    ).toBe(pt.treatments.length);
    for (const tx of pt.treatments) {
      expect(storedModalities, `${pt.full}: treatment "${tx.modality}" missing`).toContain(
        tx.modality,
      );
      const row = txRows.find((r) => r.modality === tx.modality)!;
      expect(row.duration_minutes, `${pt.full}: ${tx.modality} duration`).toBe(
        parseInt(tx.duration),
      );
    }
    console.log(`  ✓ Treatments DB ok: ${pt.full}  ${storedModalities.join(", ")}`);

    const jsonFilter = encodeURIComponent(`{"visit_id":"${v.visit_id}"}`);
    const eventRows = await supaGet<EventRow[]>(
      request,
      `event_log?select=event_type&payload=cs.${jsonFilter}`,
    );
    const eventTypes = eventRows.map((e) => e.event_type);
    for (const expected of [
      "PATIENT_CHECKIN",
      "SERVICE_STARTED",
      "SERVICE_COMPLETED",
      "PATIENT_CHECKOUT",
    ]) {
      expect(eventTypes, `${pt.full}: missing event ${expected}`).toContain(expected);
    }
    const txEventCount = eventTypes.filter((t) => t === "TREATMENT_ADDED").length;
    expect(
      txEventCount,
      `${pt.full}: expected ${pt.treatments.length} TREATMENT_ADDED event(s)`,
    ).toBe(pt.treatments.length);
    console.log(`  ✓ Events DB ok: ${pt.full}  ${[...new Set(eventTypes)].join(", ")}`);

    return v.visit_id;
  },

  async teardown(request, patientIds) {
    const url = process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_KEY;
    for (const pid of patientIds) {
      if (url && key) {
        const hdrs = {
          apikey: key,
          Authorization: `Bearer ${key}`,
          Prefer: "return=minimal",
        };
        const vr = await request.get(
          `${url}/rest/v1/visits?select=visit_id,room_id&patient_id=eq.${pid}`,
          { headers: hdrs },
        );
        const visits: Array<{ visit_id: string; room_id: string | null }> = await vr.json();
        if (visits.length) {
          const ids = visits.map((v) => v.visit_id).join(",");
          await request.delete(
            `${url}/rest/v1/visit_treatments?visit_id=in.(${ids})`,
            { headers: hdrs },
          );
          await request.delete(`${url}/rest/v1/visits?patient_id=eq.${pid}`, {
            headers: hdrs,
          });
          const roomIds = [...new Set(visits.map((v) => v.room_id).filter(Boolean))];
          for (const rid of roomIds) {
            await request.patch(
              `${url}/rest/v1/rooms?room_id=eq.${rid}`,
              {
                headers: { ...hdrs, "Content-Type": "application/json" },
                data: { status: "available" },
              },
            );
          }
        }
        await request.delete(`${url}/rest/v1/patients?patient_id=eq.${pid}`, {
          headers: hdrs,
        });
        console.log(`  Cleaned up patient ${pid} (${visits.length} visit(s))`);
      } else {
        await request.delete(`/prototype/patients/${pid}`);
        console.log(`  Soft-deleted patient ${pid}`);
      }
    }
  },
};

// ── Register smoke suite ──────────────────────────────────────────────────────

registerSmokeTests(prodEnv);

// ── Prod harness env ──────────────────────────────────────────────────────────
//
// Runs the same 31 focused tests as local-smoke.spec.ts against Vercel + Supabase.
// The fixture values are IDENTICAL to local. The only difference is `beforeEach`:
// instead of resetLocalData (which wipes the whole DB), it does targeted Supabase
// REST cleanup — delete rooms R1/TRA (cascading visits + treatments), delete
// test-created staff by name, reactivate OT — giving each test a clean slate
// without touching the stable seed data (C1/C2/C3 rooms, Dr. Smith/Johnson/Chen).

/** Staff names created by harness tests that must be deleted between tests. */
const HARNESS_STAFF = [
  "Alice PT", "Bob OT", "Dr. Gao", "Dr. Sarah Chen",
  "PT Only Staff", "Acupuncture Only Staff",
];

const prodHarnessEnv: HarnessEnv = {
  suiteName: "ClinicOS UI harness — prod",
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

  async beforeEach(request, page) {
    const url = process.env.SUPABASE_URL!;
    const key = process.env.SUPABASE_SERVICE_KEY!;
    const hdrs = {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    };

    // 1. Delete test rooms R1 and TRA, cascading to their visits + treatments
    for (const code of ["R1", "TRA"]) {
      const rr = await request.get(
        `${url}/rest/v1/rooms?select=room_id&code=eq.${code}`,
        { headers: hdrs },
      );
      const rooms: Array<{ room_id: string }> = await rr.json();
      for (const room of rooms) {
        const vr = await request.get(
          `${url}/rest/v1/visits?select=visit_id&room_id=eq.${room.room_id}`,
          { headers: hdrs },
        );
        const visits: Array<{ visit_id: string }> = await vr.json();
        if (visits.length) {
          const ids = visits.map((v) => v.visit_id).join(",");
          await request.delete(
            `${url}/rest/v1/visit_treatments?visit_id=in.(${ids})`,
            { headers: hdrs },
          );
          await request.delete(
            `${url}/rest/v1/visits?room_id=eq.${room.room_id}`,
            { headers: hdrs },
          );
        }
        await request.delete(
          `${url}/rest/v1/rooms?room_id=eq.${room.room_id}`,
          { headers: hdrs },
        );
      }
    }

    // 2. Delete test-created staff by name (visits in R1/TRA deleted first above)
    for (const name of HARNESS_STAFF) {
      await request.delete(
        `${url}/rest/v1/staff?name=eq.${encodeURIComponent(name)}`,
        { headers: hdrs },
      );
    }

    // 3. Reactivate OT (may have been retired by test #30)
    await request.patch(
      `${url}/rest/v1/service_types?name=eq.OT`,
      { headers: hdrs, data: { is_active: true } },
    );

    await page.goto("/ui/index.html");
  },
};

registerHarnessTests(prodHarnessEnv);

// ── Prod auth env ─────────────────────────────────────────────────────────────
//
// Tests login/JWT, RBAC, clinic registration, and multi-tenancy isolation
// against the Vercel + Supabase production environment.
// Uses Supabase REST to hard-delete clinics + users created during the suite.

const prodAuthEnv: AuthEnv = {
  suiteName: "Auth — prod (Vercel + Supabase)",
  adminEmail: "admin@test.clinicos.local",
  adminPassword: "test1234",
  runSuffix: RUN_SUFFIX,

  async setup(request: APIRequestContext) {
    // Warm up Vercel cold start (light endpoints)
    await request.get("/health");
    await request.get("/prototype/auth/me").catch(() => {});
  },

  async teardown(request: APIRequestContext, created: AuthCreated) {
    const url = process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_KEY;
    if (!url || !key || created.clinicIds.length === 0) return;

    const hdrs = {
      apikey: key,
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    };
    const ids = created.clinicIds.join(",");

    // Delete users belonging to the test clinics
    await request.delete(`${url}/rest/v1/users?clinic_id=in.(${ids})`, { headers: hdrs });
    // Delete the test clinics themselves
    await request.delete(`${url}/rest/v1/clinics?clinic_id=in.(${ids})`, { headers: hdrs });
    console.log(`  Auth teardown: removed ${created.clinicIds.length} test clinic(s)`);
  },

  async createFrontdeskUser(_request: APIRequestContext, _suffix: string) {
    // /test/create-user is disabled on prod (Supabase mode)
    return null;
  },
};

registerAuthTests(prodAuthEnv);
