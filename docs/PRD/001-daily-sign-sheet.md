# PRD-001: Electronic Daily Sign Sheet

**Status:** Draft v2 — scoped under PRD-003 §11.3 (Front Desk Operations Board)
**Date:** 2026-03-02 (updated 2026-03-16)
**Context:** See `docs/clinic-workflow.md` for full as-is workflow (18 steps)
**Parent PRD:** `PRD/003-clinic-os-prd-v2.md` — this document provides detailed user stories, acceptance criteria, and event model for the **Front Desk Operations Board** module defined in PRD v2.0 §11.3.

> **Note:** PRD v2.0 broadens this module's scope beyond the sign sheet. The unified **Front Desk Operations Board** merges the Daily Sign In Sheet, Google Sheets room board, and manual tallying into a single operational hub that also surfaces appointment status, payment/insurance hints, resource allocation, and next-appointment recording. This PRD-001 remains the detailed spec for the core check-in + room + service tracking + daily report slice.

## Background

The clinic runs on a **paper Daily Sign Sheet** (Step ⑧) combined with a **Google Sheet for room status** (Step ⑨) and **manual end-of-day tallying** (Step ⑱). This is the operational heartbeat of the clinic — every patient visit flows through it.

Per PRD v2.0 §7, these tools will be phased out:
- **Daily Sign In Sheet** → 迁移期可并存 → 停用主流程
- **Google Sheets (room board)** → 迁移期对照使用 → 被替代

### Current Pain Points
- **Paper PHI exposure:** Sign sheet sits on front desk all day — visible, photographable, losable
- **No real-time visibility:** Therapists can't see room status without walking to the front desk
- **Google Sheets overwrites history:** Room status updates destroy previous state — no audit trail, BAA status unknown
- **Manual daily reports:** End-of-day tallying is error-prone and not reproducible
- **No traceability:** If a number is wrong, there's no way to trace how it was derived

### What This Replaces
| Current Tool | Problem | Clinic OS Replacement |
|---|---|---|
| Paper Daily Sign Sheet (⑧) | PHI exposure, no backup, no audit | Digital sign sheet with event log |
| Google Sheet room status (⑨) | Overwrites history, BAA unknown | Real-time room board |
| Manual tallying (⑱) | Error-prone, not auditable | Auto-generated projections |

## Goal

Replace the paper Daily Sign Sheet + Google Sheet room board + manual tallying with a single digital interface that is **as fast as paper**, provides **real-time multi-user visibility**, and produces an **immutable audit trail**.

Per PRD v2.0 §11.3, the long-term goal extends to a **unified Front Desk Operations Board** that additionally surfaces:
- 今日预约列表 (today's appointment list)
- 保险/资料缺失提醒 (insurance/missing info alerts)
- copay / 未完成 intake / 待更新保险提示
- next appointment 快捷记录
- 当日统计汇总

Milestone 1 focuses on check-in + room + service tracking + daily report. The broader board capabilities will be added incrementally in Phase 1.

## Milestone 1 (First Build Target): Room + Staff + Check-In Core

This milestone is the **first shipping slice** of PRD-001 and becomes the base for all later automation.

### Scope

#### Admin Portal
- Add room (name/code/type/active)
- Edit room and change room active status
- Add staff (name/role/license-id optional/active)
- Edit staff and change staff active status

#### User Portal (Front Desk + Therapist)
- Patient check-in with check-in time
- Select service type
- Start service with service start time
- Complete service with check-out time
- Change room status (available/occupied/cleaning/out-of-service)

#### Real-Time Aggregation
- Live per-staff working hours (sum of completed service durations)
- Live active-session duration counter per staff
- Live room occupancy/state board

#### Reporting + Persistence
- Auto-generate daily report at day close
- Allow manual "generate now" re-run for reconciliation
- Save all events and report snapshots for audit and back-office reference

### Milestone 1 Plan

#### Phase 1 — Event + Data Contracts
- Define event schema for:
  - `ROOM_CREATED`, `ROOM_UPDATED`, `ROOM_STATUS_CHANGED`
  - `STAFF_CREATED`, `STAFF_UPDATED`, `STAFF_STATUS_CHANGED`
  - `PATIENT_CHECKIN`, `SERVICE_STARTED`, `SERVICE_COMPLETED`, `PATIENT_CHECKOUT`
  - `DAILY_REPORT_GENERATED`
- Add idempotency key + actor metadata + recorded_at to all write events

#### Phase 2 — Backend APIs + Projections
- Admin APIs: CRUD-lite for rooms/staff (create, update, activate/deactivate)
- User APIs: check-in, start/end service, checkout, room status update
- Projections:
  - room_board_current
  - staff_hours_daily
  - visit_timeline_daily
  - daily_report_snapshot

#### Phase 3 — UI Delivery
- Admin portal screens: room list/form, staff list/form
- User portal screens: patient flow timeline + room board + status actions
- Real-time sync via WebSocket/SSE for room + staff hours widgets

#### Phase 4 — Daily Report Engine
- Scheduled generation at clinic day-close cut-off
- Manual regeneration endpoint with versioned snapshots
- Report contents:
  - total check-ins / check-outs
  - service counts and total service minutes
  - per-staff hours
  - per-room utilization
  - open/incomplete sessions

#### Phase 5 — Validation + Compliance Gates
- RBAC checks for admin vs user portal actions
- Audit verification: every state mutation maps to immutable event
- Data retention test: report can be fully recomputed from event history

### Milestone 1 Exit Criteria
- Rooms and staff can be fully administered without spreadsheets
- Front desk + therapist can complete the visit lifecycle in-app
- Staff hour aggregates update in near real-time (≤ 5s projection delay)
- Daily report is generated, persisted, and reproducible from event log

## Non-Goals (this PRD)

- ❌ Patient master file CRUD (PRD v2.0 §11.1 — Phase 1, separate spec)
- ❌ Appointment management CRUD (PRD v2.0 §11.2 — Phase 1, separate spec)
- ❌ Document / signature archive (PRD v2.0 §11.4 — Phase 1, separate spec)
- ❌ Patient intake digitization (Step ① — Phase 5+)
- ❌ Eligibility workflow / Asana replacement (Steps ②③④ — Phase 2)
- ❌ Notability patient ledger replacement (Step ⑤ — Phase 2)
- ❌ Claim generation (Steps ⑪⑫ — Phase 2)
- ❌ EOB reconciliation (Steps ⑬–⑰ — Phase 2)
- ❌ EHR integration (Step ⑩ — Phase 5)
- ❌ Multi-location support (Phase 5)
- ❌ AI input / extraction (Phase 3)
- ❌ Offline-first (assume reliable clinic WiFi for MVP)

## User Roles

| Role | What They Do | Access Level |
|---|---|---|
| Front Desk | Check-in, payment recording, room status viewing | Read/write sign sheet, read room board |
| Therapist | Start/end service, assign room, view schedule | Read/write own sessions, read room board |
| Clinic Manager | View daily summary, export reports | Read all, no direct edits |
| Back Office | Reference sign sheet data for claims (Step ⑪) | Read only |

## User Stories

### Check-In (Replaces paper sign-in)
- **US-1:** As front desk, I want to check in a patient with one tap, so the therapist knows they've arrived and I don't have to shout across the clinic.
- **US-2:** As front desk, I want to see all of today's patients in a single scrollable list with color-coded status, so I know at a glance who's waiting, who's in session, who's done.

### Service Tracking (Replaces paper time recording)
- **US-3:** As a therapist, I want to start a service timer with one tap when I bring the patient to the room, so session duration is automatically tracked.
- **US-4:** As a therapist, I want to select the room when starting service, so other staff can see room availability in real-time.
- **US-5:** As a therapist, I want to end a service and confirm the service type (PT, OT, eval, etc.), so billing data is accurate.
- **US-6:** As a therapist, I want to see how long my current session has been running, so I can manage my time.

### Room Board (Replaces Google Sheet)
- **US-7:** As any staff member, I want to see a real-time room board showing which patient is in which room, so I don't have to walk around to check.
- **US-8:** As a therapist, I want to reassign a patient to a different room by dragging their card, and have it update for everyone within 2 seconds.

### Payment (Replaces paper payment column)
- **US-9:** As front desk, I want to record a payment at checkout (copay, cash, card, insurance-only, no-charge), so daily revenue is tracked without manual tallying.
- **US-10:** As front desk, I want to see payment status for each patient (paid, pending, insurance-only), so I know who to collect from before they leave.

### Signature (Replaces paper signature)
- **US-11:** As a patient, I want to sign on the iPad screen to confirm my visit, replacing the paper signature.

### Daily Summary (Replaces manual tallying — Step ⑱)
- **US-12:** As a clinic manager, I want an auto-generated daily summary showing:
  - Total patients seen
  - Total revenue collected (by payment method)
  - Per-therapist hours and patient count
  - Per-room utilization
  - No-shows (checked in but no service)
  - Open sessions (started but not ended — reconciliation flag)
- **US-13:** As a clinic manager, I want to export/print the daily summary.
- **US-14:** As back office, I want to view the daily sign sheet data to reference when creating claims (Step ⑪), reducing transcription errors.

### Audit (Foundation for all compliance)
- **US-15:** As a compliance officer, I want every action recorded as an immutable event with actor, timestamp, and action type, so there's a full audit trail.
- **US-16:** As a compliance officer, I want to query "who accessed patient X's data on date Y" for incident investigation.

## Acceptance Criteria

### Events
- **AC-1:** Patient check-in produces `PATIENT_CHECKIN` event: `{patient_id, checked_in_by, timestamp}`
- **AC-2:** Service start produces `SERVICE_STARTED` event: `{patient_id, therapist_id, room_id, service_type, timestamp}`
- **AC-3:** Service end produces `SERVICE_COMPLETED` event: `{patient_id, therapist_id, service_type, duration_minutes, timestamp}`
- **AC-4:** Room assignment/change produces `ROOM_ASSIGNED` event: `{patient_id, room_id, assigned_by, timestamp}`
- **AC-5:** Payment produces `PAYMENT_RECORDED` event: `{patient_id, amount, method, recorded_by, timestamp}`
- **AC-6:** Signature produces `SIGNATURE_CAPTURED` event: `{patient_id, signature_ref, timestamp}`
- **AC-7:** No event can be modified or deleted after creation. Period.

### Projections
- **AC-8:** Daily summary projection updates within 5 seconds of any event.
- **AC-9:** Room board projection shows current state within 2 seconds of any room event.
- **AC-10:** Patient timeline shows complete visit history (all events for a patient on a given day).

### Security & Compliance
- **AC-11:** All endpoints require JWT authentication.
- **AC-12:** RBAC enforced: front desk cannot see daily summary export; back office cannot edit.
- **AC-13:** No PHI in application logs, error messages, or URLs.
- **AC-14:** All data encrypted at rest (database-level) and in transit (TLS).
- **AC-15:** Signature images stored encrypted, accessible only to authorized roles.

### UX
- **AC-16:** Check-in action ≤ 2 taps from patient list screen.
- **AC-17:** Service start ≤ 3 taps (select patient → select room → tap start).
- **AC-18:** Minimum 44×44px touch targets on all interactive elements.
- **AC-19:** Real-time updates visible to all connected clients without page refresh.

## Event Model

| event_type | payload | triggered_by | feeds_projection |
|---|---|---|---|
| `PATIENT_CHECKIN` | patient_id, checked_in_by | Front Desk | daily_sheet, daily_summary |
| `SERVICE_STARTED` | patient_id, therapist_id, room_id, service_type | Therapist | daily_sheet, room_board, daily_summary |
| `SERVICE_COMPLETED` | patient_id, therapist_id, service_type, duration_min | Therapist | daily_sheet, room_board, daily_summary |
| `ROOM_ASSIGNED` | patient_id, room_id, assigned_by | Therapist | room_board |
| `ROOM_RELEASED` | room_id, released_by | Therapist / System | room_board |
| `PAYMENT_RECORDED` | patient_id, amount, method, recorded_by | Front Desk | daily_sheet, daily_summary |
| `SIGNATURE_CAPTURED` | patient_id, signature_storage_ref | System | daily_sheet |
| `NO_SHOW_MARKED` | patient_id, marked_by | Front Desk | daily_sheet, daily_summary |

## Edge Cases / Boundary Conditions

1. **No-show:** Patient checks in but never starts service → must be explicitly markable as no-show
2. **Forgotten end:** Service started but not ended by EOD → system flags open sessions in daily summary; manager can force-close with `SERVICE_FORCE_COMPLETED` event (includes reason)
3. **Multiple services:** Same patient has PT then OT in one day → each is a separate service event pair
4. **Split payment:** Copay $30 + insurance → two `PAYMENT_RECORDED` events for same patient
5. **Room conflict:** Two patients assigned same room → system warns, allows override (both assignments logged)
6. **Staff role switching:** Therapist also doing front desk → user has multiple roles, system checks role on each action
7. **Network interruption during signature:** Retry with deduplication (idempotency key)
8. **Back-dated entry:** Therapist forgot to end session, does it next morning → event records actual_time + recorded_time
9. **Mid-session room change:** Patient moves rooms → new `ROOM_ASSIGNED` + `ROOM_RELEASED` events

## PHI / Compliance Risks

| Risk | Mitigation |
|---|---|
| iPad screen showing patient list in waiting area | Auto-lock timeout (5 min), screen privacy filter recommended |
| Signature images are PHI | Encrypted storage, access-controlled, never in logs |
| Daily summary with names is PHI | Role-gated: only manager/back office can view with names |
| Staff accessing data after hours | Session timeout, audit log all access |
| Patient data in browser cache | Appropriate cache-control headers, no PHI in localStorage |
| Screenshots of digital sign sheet | Same risk as paper — mitigated by access control + audit |

## Dependencies

- PostgreSQL database with encryption at rest
- FastAPI backend with JWT auth
- WebSocket or SSE for real-time updates
- iPad with modern browser (Safari 16+)
- Secure storage for signature images (S3-compatible with encryption or local encrypted)

## Open Questions

- [ ] **Service types:** What's the full list? (PT, OT, Eval, Re-eval, others?)
- [ ] **Room list:** How many rooms? Names or numbers?
- [ ] **Payment methods:** Copay, cash, card, insurance-only, no-charge — anything else?
- [ ] **Signature storage:** S3-compatible or local encrypted filesystem?
- [ ] **Auth model:** Individual logins per staff, or shared iPad with PIN switch?
- [ ] **PracticeMate integration:** Is there an API? Or is back office reference read-only for now?
- [ ] **Appointment list source:** Where does today's patient list come from? Manual entry or PracticeMate sync?
- [ ] **Google Workspace BAA:** Is there a signed BAA? (Determines urgency of replacing Google Sheets)

## Sprint Scope

### Must Have (Sprint 1)
- Event log table + core events
- Patient check-in flow
- Service start/end with room assignment
- Room board (real-time)
- Payment recording
- Daily summary projection
- JWT auth + basic RBAC
- Audit logging

### Nice to Have (Sprint 1)
- Signature capture
- Daily summary export/print
- No-show marking
- Force-close open sessions

### Deferred
- Patient intake (Step ①)
- Eligibility workflow (Steps ②③④)
- Patient ledger (Step ⑤)
- Claim generation (Step ⑪)
