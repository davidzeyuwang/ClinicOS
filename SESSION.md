# ClinicOS — Session Handoff

> Update this file at the end of every session.
> The next Agent reads this first (after CLAUDE.md) to locate context in 30 seconds.

---

## Last Updated

**Date:** 2026-03-27
**Session goal:** Harness Engineering setup (Phase A complete)

---

## What Was Done This Session

1. Created `CLAUDE.md` — project contract with architecture invariants, startup commands, file map, prohibited actions, compaction priorities
2. Created `init.sh` — one-command environment startup with smoke tests
3. Created `tasks/features.json` — M1 feature list with machine-verifiable `verify` commands, all `passes: false`
4. Created `.claude/agents/` — wired 7 agents into Claude Code subagent system (backend-engineer, architect, tester, reviewer, compliance, manager, pm)
5. Created `.claude/settings.json` — PostToolUse hook: runs `py_compile` on every Python edit in `backend/`

## What Was Completed

- Harness Phase A (persistent state + context engineering) — DONE
- Harness Phase B (subagent wiring) — DONE
- Harness Phase C (feedback hook) — partial (syntax check only, no test runner yet)

## Current State

- **Backend:** Running, all endpoints working, SQLite local dev
- **Tests:** E2E test suite exists (`backend/tests/test_prototype_e2e.py`), passing
- **M1 Tasks:** 0/9 `passes: true` in `tasks/features.json`
- **Auth:** Completely missing (`backend/app/auth/` is empty)
- **Codebase audit completed:** See critical issues below

## Critical Issues Found (must fix before production)

1. **No auth** — `backend/app/auth/` empty, all endpoints unprotected (HIPAA violation)
2. **Room not released on checkout** — `patient_checkout()` in `db_service.py` doesn't free the room if `service_end` was skipped
3. **EventLog deleted in test reset** — `reset_demo_data()` runs `DELETE FROM event_log`, violating ADR-001 append-only
4. **3x hard deletes** — `delete_room/delete_staff/delete_visit` physically delete projection rows instead of soft-delete
5. **PDF shows staff UUID** — `_visit_to_dict()` omits `staff_name`, PDF sign sheet shows UUID

## Recommended Next Steps (in order)

1. **Fix critical bugs first** (can do in one session):
   - Fix `reset_demo_data` to skip EventLog
   - Fix `patient_checkout` to release room
   - Fix hard deletes → soft deletes in `delete_room/staff/visit`

2. **Then start M1-BE-03** (Auth + RBAC) — nothing else matters without this

3. **After auth works**, proceed with M1-BE-01/02 to complete event_log schema

## How to Start Next Session

```bash
./init.sh          # start server + run smoke tests
# Check what's broken first, then pick next task from tasks/features.json
```

First failing item in features.json: `M1-BE-01` (all pass: false)
But highest priority fix: auth (M1-BE-03) and the 3 bugs above.

---

## Session Notes

_Add any context that would help the next session:_

- The current `db_routes.py` is the **live** router (prefix `/prototype`). The old `prototype.py` router is dead code.
- `db_service.py` is for SQLite local dev. `db_service_supa.py` is for Supabase prod (incomplete, ~100 lines).
- Frontend is a single HTML file at `frontend/index.v1.html` — no build step needed.
- `verify_db.py` is a manual inspection script, not a test — has hardcoded path, not useful in CI.
