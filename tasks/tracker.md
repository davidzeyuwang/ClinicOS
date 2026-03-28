# ClinicOS Task Tracker — DEPRECATED

**⚠️ THIS FILE IS OUTDATED ⚠️**

**Last Updated:** 2026-03-27 (marked as deprecated)

## Active tracking has moved to:
- **IMPLEMENTATION-PLAN.md** — Current implementation status (PRD-005: Multiple Treatments)
- **PROGRESS-SUMMARY.md** — Detailed progress summary

---

## Status: PRD-005 Complete (13/13 tasks - 100%)

**What was completed:**
1. ✅ Phase 1: PDF & Checkout Fixes (3 tasks)
2. ✅ Phase 2: Multiple Treatments UI (4 tasks)
3. ✅ Phase 3: Treatment Records Page (3 tasks)
4. ✅ Phase 4: Selective PDF Generation (3 tasks)

**Production URL:** https://clinicos-psi.vercel.app

---

## Old M1 Milestone (Not Currently Active)

**M1 Scope Clarification:** Patient management, staff management, room management, check-in, check-out, sign-sheet PDF generation, and daily report aggregation. Appointment/insurance/tasking beyond this core flow are tracked as post-M1 or secondary scope.

### Task Summary (M1 - Future Work)
| Status | Count |
|---|---|
| Backlog | 9 |
| Assigned | 0 |
| In Progress | 0 |
| In Review | 0 |
| Done | 0 |
| **Total** | **9** |

**Note:** M1 tasks below are for event-sourcing migration (future work).  
Current system uses Supabase REST API and is production-ready.

### Task Board (M1 - Future)

| ID | Task | Phase | Owner | Status | Priority | Est | Actual | Depends |
|---|---|---|---|---|---|---|---|---|
| M1-BE-01 | PostgreSQL event_log + core events | 4 | SDE-A | backlog | P0 | 2d | - | - |
| M1-BE-02 | DB-backed projections (room/staff/report) | 4 | SDE-A | backlog | P0 | 2d | - | M1-BE-01 |
| M1-BE-03 | Auth + RBAC guards | 4 | SDE-A | backlog | P0 | 1.5d | - | M1-BE-01 |
| M1-FE-01 | Admin portal UI (room/staff CRUD) | 4 | SDE-A | backlog | P0 | 2d | - | M1-BE-01, M1-BE-02 |
| M1-FE-02 | User portal (visit lifecycle flow) | 4 | SDE-A | backlog | P0 | 2d | - | M1-BE-01, M1-BE-02 |
| M1-FE-03 | Live dashboard (room board + staff hours) | 4 | SDE-A | backlog | P1 | 1.5d | - | M1-FE-01, M1-FE-02 |
| M1-QA-01 | API + flow tests (happy + failure) | 5 | QA SDE | backlog | P0 | 1.5d | - | M1-BE-01, M1-BE-02 |
| M1-COMP-01 | PHI/logging/RBAC audit gate | 5 | Compliance | backlog | P0 | 1d | - | M1-BE-03 |
| M1-REV-01 | Final design/code review + go/no-go | 5 | SDE-B | backlog | P0 | 0.5d | - | M1-QA-01, M1-COMP-01 |

### Milestone Progress
```
[░░░░░░░░░░░░░░░░░░░░] 0% (0/9 tasks done)
```

## Completed Milestones
_(none yet)_

## Change Log
| Date | Change | By |
|---|---|---|
| 2026-03-15 | Initialized tracker from PRD-002 task board | Manager |
| 2026-03-27 | Clarified M1 as operations core: patient/staff/room/check-in/check-out/PDF/report | Manager |
