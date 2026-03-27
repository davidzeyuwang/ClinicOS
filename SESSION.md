# ClinicOS — Session Handoff

> Update this file at the end of every session.
> The next Agent reads this first (after CLAUDE.md) to locate context in 30 seconds.

---

## Last Updated

**Date:** 2026-03-27  
**Session goal:** PRD-005 Multiple Treatments Per Visit — Backend Complete

---

## What Was Done This Session

1. Created **PRD-005** — Complete requirements doc for multiple treatments per visit
2. Implemented backend for multiple treatments:
   - Added `VisitTreatment` table model (already existed in models)
   - Added 3 new Pydantic schemas: `TreatmentAdd`, `TreatmentUpdate`, `TreatmentRecordsFilter`
   - Implemented 5 service functions in `db_service.py`:
     - `add_treatment()` — Add modality to visit
     - `update_treatment()` — Edit duration/notes
     - `delete_treatment()` — Remove treatment
     - `list_visit_treatments()` — Get all treatments for visit
     - `list_treatment_records()` — Query with filters (date/patient/staff/modality)
   - Added 5 API routes in `db_routes.py`:
     - POST `/visits/{id}/treatments/add`
     - GET `/visits/{id}/treatments`
     - PATCH `/visits/{id}/treatments/{tid}/update`
     - DELETE `/visits/{id}/treatments/{tid}/delete`
     - GET `/treatment-records?date_from=X&staff_id=Y`
   - Added event logging: `TREATMENT_ADDED`, `TREATMENT_UPDATED`, `TREATMENT_DELETED`
3. Wrote comprehensive test suite (`test_treatments.py`, 421 lines):
   - `test_prd005_multiple_treatments_workflow` — Full E2E with 3 treatments
   - `test_cannot_add_treatment_to_checked_out_visit` — Edge case
   - `test_treatment_without_therapist_defaults_to_actor` — Default behavior
   - `test_treatment_records_date_filter` — Filter validation
4. Updated `tasks/features.json` — Added 5 new PRD-005 tasks (1 backend complete, 4 frontend pending)
5. Created `TEST-REPORT-PRD005.md` — Comprehensive test report (all tests passing)

## What Was Completed

- ✅ PRD-005 Backend API — 100% complete (5 endpoints working)
- ✅ Treatment event logging — All operations logged to event_log
- ✅ Treatment test suite — 4/4 tests passing
- ✅ Data enrichment — Treatments enriched with therapist_name, patient_name, room_name
- ⚠️ UI not implemented yet (next step)

## Current State

- **Backend:** All treatment APIs working, tested, passing
- **Tests:** 19 total (15 passing, 4 pre-existing failures unrelated to treatments)
- **PRD-005 Status:**
  - Backend: DONE ✅
  - Frontend: NOT STARTED
  - PDF enhancements: NOT STARTED
- **Database:** `visit_treatments` table model exists, will be created on next `alembic migrate` (SQLite auto-creates on first use)

## Critical Issues Found (must fix before production)

**Pre-existing issues (not changed this session):**

1. **No auth** — `backend/app/auth/` empty, all endpoints unprotected (HIPAA violation)
2. **Room not released on checkout** — `patient_checkout()` in `db_service.py` doesn't free the room if `service_end` was skipped
3. **EventLog deleted in test reset** — `reset_demo_data()` runs `DELETE FROM event_log`, violating ADR-001 append-only
4. **3x hard deletes** — `delete_room/delete_staff/delete_visit` physically delete projection rows instead of soft-delete
5. **PDF shows staff UUID** — `_visit_to_dict()` omits `staff_name`, PDF sign sheet shows UUID

**New issue found this session:**
6. **Hardcoded actor_id in treatment routes** — Some routes use `actor_id="admin"` instead of JWT-authenticated user

## Recommended Next Steps (in order)

1. **Implement PRD-005 Frontend** (4 tasks in features.json):
   - Add treatment management to active visits (+ button, list, edit/delete)
   - Checkout modal with treatment summary
   - Treatment records page with filters
   - Selective PDF generation (checkboxes)

2. **Fix critical bugs** (can do in one session):
   - Fix `reset_demo_data` to skip EventLog
   - Fix `patient_checkout` to release room
   - Fix hard deletes → soft deletes in `delete_room/staff/visit`
   - Replace hardcoded actor_id with JWT context

3. **Then start M1-BE-03** (Auth + RBAC) — nothing else matters without this

4. **After auth works**, proceed with M1-BE-01/02 to complete event_log schema

## How to Start Next Session

```bash
./init.sh          # start server + run smoke tests
cd backend && python -m pytest tests/test_treatments.py -v  # verify treatments working
# Then implement PRD-005 frontend (see docs/PRD/005-multiple-treatments-per-visit.md)
```

**Next Priority:** Frontend for PRD-005 (4 UI tasks)  
**Backend Status:** Treatment APIs complete and tested ✅

---

## Session Notes

_Context for next session:_

- **New files created:**
  - `docs/PRD/005-multiple-treatments-per-visit.md` — Complete PRD
  - `backend/tests/test_treatments.py` — 4 comprehensive tests (421 lines)
  - `TEST-REPORT-PRD005.md` — Test report with all results

- **Modified files:**
  - `backend/app/schemas/prototype.py` — Added TreatmentAdd, TreatmentUpdate, TreatmentRecordsFilter
  - `backend/app/services/db_service.py` — Added 5 treatment functions + _treatment_to_dict helper
  - `backend/app/routers/db_routes.py` — Added 5 treatment routes
  - `tasks/features.json` — Added 5 PRD-005 tasks (PRD005-BE-01 passes: true)

- **Database note:** `visit_treatments` table model exists in `models/tables.py` but table not yet created in DB. SQLite will auto-create on first use. Supabase production needs manual migration.

- **Test coverage:** All 4 new treatment tests pass. Backend fully functional. UI completely missing.

- **Known limitation:** Cannot generate PDF at checkout yet (checkbox exists in PRD spec but not implemented). Cannot select visits for PDF (requires UI checkboxes).
