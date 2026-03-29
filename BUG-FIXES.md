# Bug Fix Log

Each bug links to the feature it belongs to for test harness and regression tracking.

---

## BUG-1: Check-in modal missing service options [x] FIXED
**Feature:** ROADMAP-P1-02 (Front Desk Operations Board)
**Where:** `frontend/index.html` — `openRoomCheckin()` — `<select id="rc-svc">` only had PT/OT/Eval/Re-eval/Speech.
**Fix:** Added Acupuncture, Cupping, Massage, E-stim to match Start Service modal.
**Files changed:** `frontend/index.html`

---

## BUG-2: Checkout + Treatment modals missing initial service [x] FIXED
**Feature:** PRD005-P2-01 (Multiple Treatments UI)
**Where:** `openCheckout()` and `openTreatments()` — both loaded `GET /visits/{vid}/treatments` (VisitTreatment rows only). The service set at ServiceStart lived on the Visit record and was never shown.
**Fix:** Replaced special "initial row" display logic. Instead, `doRoomCheckin()` and `doAssignSvc()` now immediately `POST /visits/{vid}/treatments/add` after `service/start`, persisting the initial service as a real VisitTreatment with duration. All modals then show all treatments uniformly.
**Files changed:** `frontend/index.html`

---

## BUG-3: Sign sheet PDF — treatments grouped on one row instead of separate lines [x] FIXED
**Feature:** ROADMAP-P1-04 (Document/Signature Archive — Sign-sheet PDF)
**Where:** `backend/app/services/pdf_service.py` — `generate_sign_sheet()` built one row per visit, joining modalities with ", ".
**Fix:** Expanded to one row per treatment. If a visit has 2 treatments, renders 2 rows with the same date. Falls back to one row with `service_type` if no explicit treatment records.
**Files changed:** `backend/app/services/pdf_service.py`

---

## BUG-4: Sign sheet PDF — missing duration on each row [x] FIXED
**Feature:** ROADMAP-P1-04 (Document/Signature Archive — Sign-sheet PDF)
**Where:** `backend/app/services/pdf_service.py` — Service column showed modality name only.
**Fix:** Format Service cell as `"PT (30m)"` or `"Acupuncture (20m)"`. Service column widened from 24mm → 30mm to fit.
**Files changed:** `backend/app/services/pdf_service.py`

---

## BUG-5: Treatment tab A/PT/CP/TN columns missing duration [x] FIXED
**Feature:** PRD005-P3-01 (Treatment Records Page)
**Where:** `list_visits_with_treatments()` in `backend/app/services/db_service.py` — `_col_display()` built "Name" string but omitted duration. Frontend rendered name only.
**Fix:** `_col_display()` now returns `"Name / Xm"` (e.g. `"Alice PT / 30m"`). New `/visit-records` endpoint added in `db_routes.py`. Frontend `loadTreatmentRecords()` rewritten to use this endpoint. One-row-per-visit layout with A/PT/CP/TN columns.
**Files changed:** `backend/app/services/db_service.py`, `backend/app/routers/db_routes.py`, `frontend/index.html`

---

## BUG-6: Daily summary total payment = copay only, misses additional amount [x] FIXED
**Feature:** ROADMAP-P1-05 (Daily Summary Report)
**Where:** `backend/app/services/db_service.py` — `get_daily_summary()` — `payment_total = sum(v.payment_amount ...)` excluded `copay_collected`.
**Fix:** `payment_total = sum(copay_collected + payment_amount)` for each checked-out visit.
**Files changed:** `backend/app/services/db_service.py`

---

## BUG-7: Staff hours use wall-clock time instead of treatment durations [x] FIXED
**Feature:** ROADMAP-P1-05 (Daily Summary Report)
**Where:** `backend/app/services/db_service.py` — `get_staff_hours()` — summed `service_end_time - service_start_time`. Showed "3m" when actual treatment durations were 30m + 50m.
**Fix:** Sum `VisitTreatment.duration_minutes` per `therapist_id`. Falls back to wall-clock visit duration only if no treatment records exist.
**Files changed:** `backend/app/services/db_service.py`

---

## BUG-8: Check-in and Start Service modals missing duration field [x] FIXED
**Feature:** PRD005-P2-01 (Multiple Treatments UI) / ROADMAP-P1-02 (Front Desk Operations Board)
**Where:** `frontend/index.html` — `openRoomCheckin()` and `openAssignSvc()` modals had no duration input. Duration was not captured at service start.
**Fix:** Added `<input id="rc-dur">` (default 30) to check-in modal and `<input id="as-dur">` (default 30) to Start Service modal. Duration value is passed to the auto-created VisitTreatment on service start.
**Files changed:** `frontend/index.html`

---

## BUG-9: Initial service never persisted as VisitTreatment — missing from records, PDF, checkout [x] FIXED
**Feature:** PRD005-BE-01 (Multiple treatments per visit — backend) / PRD005-P2-01
**Where:** `doRoomCheckin()` and `doAssignSvc()` in `frontend/index.html` — only called `POST /portal/service/start`. The service_type lived on the Visit, never as a VisitTreatment, so it was invisible in: treatment modal, checkout summary, sign-sheet PDF, and treatment records tab.
**Fix:** Both functions now immediately `POST /visits/{vid}/treatments/add` after `service/start`, using the selected modality and duration. Removed all special "prepend initial service" display hacks from `openTreatments()` and `openCheckout()`.
**Files changed:** `frontend/index.html`

---

## BUG-10: Treatment column blank when no therapist assigned to treatment [x] FIXED
**Feature:** PRD005-P3-01 (Treatment Records Page)
**Where:** `backend/app/services/db_service.py` — `_col_display()` — returned `""` whenever `therapist_id` was null/absent, even if `duration_minutes` > 0. Duration was counted in totals but silently dropped from the column cell.
**Fix:** `_col_display()` now returns `"Xm"` (e.g. `"45m"`) when duration exists but no therapist is assigned, instead of silently returning empty string.
**Files changed:** `backend/app/services/db_service.py`

---

## BUG-11: E2E Playwright tests failing after treatment tab redesign [x] FIXED
**Feature:** PRD005-P3-01 (Treatment Records Page)
**Where:** `frontend/tests/e2e/ops-board.spec.ts` — 3 tests written against the old per-treatment-row design that was replaced by the per-visit grouped design with A/PT/CP/TN columns.
- Test 17 (`treatment records show correct date and duration format`): Expected `1h30m` but initial service (30m) + added PT (90m) = 120m → `2h`.
- Test 18 (`treatment records table has all required columns`): Expected old headers (`Service`, `Modality`, `Therapist`, `Notes`) instead of new (`生诊医生`, `A`, `PT`, `CP`, `TN`, `Note`).
- Test 19 (`walk-in treatment appears in treatment records with patient name`): Expected `Massage` as text (it's now in TN column as `"45m"`) and `45m` wasn't rendered (fixed by BUG-10).
**Fix:** Updated all three test assertions to match the new visit-grouped design. BUG-10 fix resolved test 19's `45m` assertion independently.
**Files changed:** `frontend/tests/e2e/ops-board.spec.ts`

---

## New Feature Requests

### FEATURE-1: Staff setup should include supported service types [ ] TODO
**Feature ref:** NEXT-P1-02 (Staff qualification by service type)
**Need:** When creating or editing a staff member, admin should be able to assign one or more service types that this staff member can perform.
**Why:** Staff capability should be defined in the system instead of relying on manual knowledge.

### FEATURE-2: Staff picker should be filtered by selected service type [ ] TODO
**Feature ref:** NEXT-P1-02 (Staff qualification by service type)
**Need:** In workflows that assign a staff member, users should choose a service type first, and then only see staff members who are qualified for that service type.
**Why:** Prevent invalid assignments and make service assignment faster.

### FEATURE-3: Admin should be able to manage service types [ ] TODO
**Feature ref:** NEXT-P1-01 (Admin-managed service types)
**Need:** Admin can add, edit, and retire service types instead of relying on a hard-coded list.
**Why:** The clinic can expand offerings without code changes.
