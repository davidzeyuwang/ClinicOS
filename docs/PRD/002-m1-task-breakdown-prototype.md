# PRD-002: Milestone 1 Task Breakdown + Prototype Steps

**Status:** Ready to execute  
**Date:** 2026-03-05 (updated 2026-03-16)  
**Depends on:** `PRD/000-product-roadmap.md`, `PRD/001-daily-sign-sheet.md`, `PRD/003-clinic-os-prd-v2.md`

> **Context:** Milestone 1 is the first build target within **PRD v2.0 Phase 1 (运营核心打通)**. It covers the core check-in + room + service tracking + daily report slice of the **Front Desk Operations Board** (§11.3). Other Phase 1 modules (Patient Master §11.1, Appointment §11.2, Document/Signature §11.4, Task Management §11.9) will be addressed in subsequent milestones.

## Objective

Deliver the first shippable milestone of ClinicOS:
- Admin portal data setup (rooms + staff)
- User portal visit lifecycle (check-in → service start/end → checkout)
- Real-time staff hour aggregation
- Daily report generation with persisted snapshots

## Work Breakdown Structure (WBS)

### Track A — Backend Core (Prototype-first)
1. Define event contracts for room/staff/visit/report
2. Implement event appends + in-memory projection updates
3. Add admin APIs (room/staff create + update)
4. Add user APIs (check-in, service start/end, checkout, room status)
5. Add projection APIs (room board, staff hours)
6. Add report APIs (generate + fetch)

### Track B — Frontend Prototype UI
1. Admin screen: room list/form and staff list/form
2. User screen: check-in and service lifecycle actions
3. Live widgets: room board and staff-hour table
4. Daily report panel: generate + view

### Track C — Quality + Compliance Gate
1. API contract tests (happy path + invalid ids)
2. Event immutability check (append-only behavior)
3. Projection freshness check (<5s target in full implementation)
4. RBAC stubs and role matrix validation

## Step-by-Step Prototype (Runbook)

## Step 0 — Start backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open docs:
- `http://127.0.0.1:8000/docs`

Prototype endpoints live under:
- `/prototype/*`

## Step 1 — Admin setup: create rooms

POST `/prototype/admin/rooms`

Example body:
```json
{
  "name": "Room 1",
  "code": "R1",
  "room_type": "treatment",
  "active": true
}
```

Repeat for all clinic rooms.

## Step 2 — Admin setup: create staff

POST `/prototype/admin/staff`

Example body:
```json
{
  "name": "Alice Therapist",
  "role": "therapist",
  "license_id": "PT-001",
  "active": true
}
```

Repeat for front desk + therapists.

## Step 3 — User flow: patient check-in

POST `/prototype/portal/checkin`

```json
{
  "patient_name": "John Doe",
  "patient_ref": "MRN-1001",
  "actor_id": "frontdesk-1"
}
```

Save returned `visit_id`.

## Step 4 — User flow: start service

POST `/prototype/portal/service/start`

```json
{
  "visit_id": "<visit_id>",
  "staff_id": "<staff_id>",
  "room_id": "<room_id>",
  "service_type": "PT",
  "actor_id": "therapist-1"
}
```

## Step 5 — Verify real-time projections

GET `/prototype/projections/room-board`  
GET `/prototype/projections/staff-hours`

Expected:
- room status becomes `occupied`
- active minutes starts accruing for assigned staff

## Step 6 — End service and checkout

POST `/prototype/portal/service/end`
```json
{
  "visit_id": "<visit_id>",
  "actor_id": "therapist-1"
}
```

POST `/prototype/portal/checkout`
```json
{
  "visit_id": "<visit_id>",
  "actor_id": "frontdesk-1"
}
```

Expected:
- room returns to `available`
- completed minutes increments in staff aggregation

## Step 7 — Generate daily report

POST `/prototype/reports/daily/generate`
```json
{
  "actor_id": "manager-1"
}
```

Then fetch:
- GET `/prototype/reports/daily`

## Step 8 — Audit verification

GET `/prototype/events`

Confirm all actions exist as append-only events and can reconstruct daily summary.

## Milestone 1 Task Board (Ready for Assignment)

| ID | Task | Owner Role | Est. |
|---|---|---|---|
| M1-BE-01 | Replace in-memory prototype with PostgreSQL event_log | Backend Engineer | 2d |
| M1-BE-02 | Add DB-backed projections (room/staff/report) | Backend Engineer | 2d |
| M1-BE-03 | Add auth + RBAC guards on prototype endpoints | Backend Engineer + Compliance | 1.5d |
| M1-FE-01 | Build admin portal UI for room/staff CRUD-lite | Frontend Designer | 2d |
| M1-FE-02 | Build user portal flow for visit lifecycle | Frontend Designer | 2d |
| M1-FE-03 | Build live dashboard widgets (room board/staff hours) | Frontend Designer | 1.5d |
| M1-QA-01 | API and flow tests (happy + failure paths) | Tester | 1.5d |
| M1-COMP-01 | PHI/logging/RBAC audit gate | Compliance | 1d |
| M1-REV-01 | Final design/code review + go/no-go | Reviewer | 0.5d |

## Definition of Prototype-Complete

- Admin can create and update rooms + staff via API
- Front desk/therapist can complete full visit lifecycle via API
- Staff hours and room board projections reflect state transitions
- Daily report generates and is retrievable
- Event stream captures all state-changing actions

## Relationship to PRD v2.0 Phase 1

Milestone 1 delivers the **operations board core** (PRD v2.0 §11.3). Remaining Phase 1 modules to be delivered in subsequent milestones:

| Milestone | PRD v2.0 Section | Scope |
|---|---|---|
| M1 (this) | §11.3 partial | Check-in + Room + Service + Daily Report |
| M2 | §11.1, §11.2 | Patient Master + Appointment Management |
| M3 | §11.3 complete, §11.4 | Full Operations Board + Document/Signature |
| M4 | §11.5, §11.6, §11.9, §11.10, §11.11 | Visit + Note + Task + Dashboard + RBAC |
