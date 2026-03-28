# Bug Fix Plan — 2026-03-28

## BUG-1: Check-in modal missing service options [x] FIXED
**Where:** `openRoomCheckin()` line 436 — `<select id="rc-svc">` only has PT/OT/Eval/Re-eval/Speech. Missing Acupuncture, Cupping, Massage.
**Fix:** Add full service list to match Start Service modal.

## BUG-2: Checkout + Treatment modals missing initial service [x] FIXED
**Where:** `openCheckout()` and `openTreatments()` — both load `GET /visits/{vid}/treatments` (VisitTreatment rows only). The service set at ServiceStart is on the Visit record, never shown.
**Fix:** Fetch visit data alongside treatments; prepend visit's `service_type` as the first display row if not already present as a treatment.

## BUG-3: Sign sheet PDF — treatments grouped on one row instead of separate lines [x] FIXED
**Where:** `pdf_service.generate_sign_sheet()` — builds one row per visit, joins modalities with ", ".
**Fix:** Expand to one row per treatment. If visit has 2 treatments, render 2 rows with same date. If no explicit treatments, fall back to one row with service_type.

## BUG-4: Sign sheet PDF — missing duration on each row [x] FIXED
**Where:** `pdf_service.generate_sign_sheet()` — Service column shows modality name only.
**Fix:** Format Service cell as "PT (30m)" or "Acupuncture (20m)".

## BUG-5: Treatment tab A/PT/CP/TN — missing duration [x] FIXED
**Where:** `list_visits_with_treatments()` backend — stores therapist name only. Frontend renders name only.
**Fix:** Backend: store `"Name / Xm"` string per column (or separate `_dur` fields). Frontend: display combined.

## BUG-6: Daily summary total payment = copay only, misses additional amount [x] FIXED
**Where:** `get_daily_summary()` line 525 — `payment_total = sum(v.payment_amount ...)` excludes copay_collected.
**Fix:** `payment_total = sum(copay_collected + payment_amount)` for each checked-out visit.

## BUG-7: Staff hours use wall-clock time instead of treatment durations [x] FIXED
**Where:** `get_staff_hours()` — sums `service_end_time - service_start_time`. Shows "3m" when treatments were 30m+50m.
**Fix:** Sum `VisitTreatment.duration_minutes` per therapist. Fall back to visit duration only if no treatment records exist.

---

## New Feature Requests

### FEATURE-1: Staff setup should include supported service types [ ] TODO
**Need:** When creating or editing a staff member, admin should be able to assign one or more service types that this staff member can perform.
**Why:** Staff capability should be defined in the system instead of relying on manual knowledge.

### FEATURE-2: Staff picker should be filtered by selected service type [ ] TODO
**Need:** In workflows that assign a staff member, users should choose a service type first, and then only see staff members who are qualified for that service type.
**Why:** Prevent invalid assignments and make service assignment faster.

### FEATURE-3: Admin should be able to manage service types [ ] TODO
**Need:** Admin can add, edit, and retire service types instead of relying on a hard-coded list.
**Why:** The clinic can expand offerings without code changes.
