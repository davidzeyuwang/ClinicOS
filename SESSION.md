# ClinicOS — Session Handoff

> Update this file at the end of every session.
> The next Agent reads this first (after CLAUDE.md) to locate context in 30 seconds.

---

## Last Updated

**Date:** 2026-04-05  
**Session goal:** Document recently implemented features; update README

---

## What Was Done This Session

1. Updated **README.md** — replaced stale content with accurate tech stack and a "Recently Implemented Features" section covering all 22 completed features.

---

## What Was Completed (cumulative as of 2026-04-03)

### Auth + Multi-Tenancy (2026-04-03) — most recent batch
- ✅ AUTH-00: Clinic owner self-registration (`POST /auth/register`)
- ✅ AUTH-01: JWT authentication (`POST /auth/login` → signed JWT)
- ✅ AUTH-02: Role model (admin · frontdesk · doctor)
- ✅ MT-01: `clinics` table + `clinic_id` FK on all tenant-scoped tables
- ✅ MT-02: Tenant-isolation FastAPI middleware
- ✅ NEXT-P1-01: Admin-managed service types API
- ✅ NEXT-P1-02: Staff qualification by service type

### Multiple Treatments (2026-03-26 – 2026-03-27)
- ✅ PRD005-BE-01: Backend — `visit_treatments` table + 5 endpoints + event logging
- ✅ PRD005-P1-01 – P4-01: Frontend phases (treatment UI, records tab, selective PDF, checkout summary)

### Core Ops (2026-03-26 — foundation)
- ✅ ROADMAP-P1-01 – P1-06: Patient CRUD, Ops Board, Visit lifecycle, PDF archive, Daily report, Supabase backend

## Current State

- **Backend:** Auth endpoints, multi-tenant middleware, treatment APIs all implemented
- **Frontend:** Ops board, treatment management, records tab — all in `frontend/index.html`
- **Tests:** Backend pytest suite in `backend/tests/`; Playwright UI tests at repo root
- **Production:** https://clinicos-psi.vercel.app

## Critical Issues Found (must fix before production-wide launch)

1. **RBAC not enforced on all routes** — auth middleware exists but older routes still unauthenticated
2. **Frontend has no login flow** — JWT exists but `frontend/index.html` doesn't prompt for credentials
3. **Room not released on checkout** — `patient_checkout()` doesn't free room if `service_end` was skipped
4. **EventLog deleted in test reset** — `reset_demo_data()` runs `DELETE FROM event_log`, violating ADR-001 append-only
5. **Hard deletes on room/staff/visit** — should be soft deletes

## Recommended Next Steps (in order)

1. **Add login screen to frontend** — use the JWT auth endpoints already built
2. **Enforce RBAC on all existing routes** — wrap older routes with the tenant middleware
3. **Fix room-not-released bug** at checkout
4. **Fix EventLog in test reset** — skip `event_log` in `reset_demo_data()`

## How to Start Next Session

```bash
./init.sh          # start server + smoke tests
cd backend && python -m pytest tests/ -x -q  # verify all tests pass
```

**Next Priority:** Login UI + RBAC enforcement on all routes  
**Backend Status:** Auth + multi-tenancy + treatments APIs complete ✅

---

## Session Notes

_Previous session (2026-03-27):_

- Created `docs/PRD/005-multiple-treatments-per-visit.md`
- Added `backend/tests/test_treatments.py` (421 lines)
- Modified `backend/app/schemas/prototype.py`, `db_service.py`, `db_routes.py`
- Updated `tasks/features.json` with PRD-005 tasks
