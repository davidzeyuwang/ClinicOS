# PRD-005 Implementation Status

**Feature:** Multiple Treatments Per Visit + Enhanced Workflow  
**Date:** 2026-03-27  
**Status:** Backend Complete ✅ | Frontend Pending ⚠️

---

## ✅ Completed (Backend)

### Database Schema
- [x] `visit_treatments` table model (exists in models/tables.py)
- [x] Fields: treatment_id, visit_id, modality, therapist_id, duration_minutes, started_at, completed_at, notes
- [x] Indexes on visit_id and therapist_id (defined in model)

### API Endpoints (5/5 implemented)
- [x] `POST /visits/{visit_id}/treatments/add` — Add treatment to visit
- [x] `GET /visits/{visit_id}/treatments` — List treatments (enriched with names)
- [x] `PATCH /visits/{visit_id}/treatments/{treatment_id}/update` — Edit duration/notes
- [x] `DELETE /visits/{visit_id}/treatments/{treatment_id}/delete` — Remove treatment
- [x] `GET /treatment-records?filters` — Query all treatments with date/patient/staff/modality filters

### Event Sourcing
- [x] `TREATMENT_ADDED` event logged
- [x] `TREATMENT_UPDATED` event logged
- [x] `TREATMENT_DELETED` event logged
- [x] All events append to immutable event_log

### Business Logic
- [x] Cannot add treatment to checked-out visit (400 error)
- [x] Therapist_id defaults to actor_id if not specified
- [x] Data enrichment: treatments include therapist_name, patient_name, room_name
- [x] Multiple treatments per visit supported (tested with 3 concurrent)

### Testing
- [x] `test_prd005_multiple_treatments_workflow` — Full E2E (25 assertions)
- [x] `test_cannot_add_treatment_to_checked_out_visit` — Edge case validation
- [x] `test_treatment_without_therapist_defaults_to_actor` — Default behavior
- [x] `test_treatment_records_date_filter` — Filter validation
- [x] **Result:** 4/4 tests passing

### Documentation
- [x] PRD-005 written (docs/PRD/005-multiple-treatments-per-visit.md)
- [x] Test report created (TEST-REPORT-PRD005.md)
- [x] Implementation guide exists (docs/IMPLEMENTATION-MULTIPLE-TREATMENTS.md)
- [x] Features.json updated with 5 tasks

---

## ⚠️ Pending (Frontend)

### UI Components Needed

#### 1. Active Visits Card Enhancement
- [ ] Add "Add Treatment" button
- [ ] Display treatment list (modality, therapist, duration)
- [ ] Edit button per treatment (opens modal)
- [ ] Delete button per treatment (confirmation dialog)

#### 2. Add Treatment Modal
- [ ] Modality dropdown (PT, OT, E-stim, Massage, Cupping, Acupuncture, etc.)
- [ ] Therapist dropdown (populated from staff list)
- [ ] Duration input (default 30 min)
- [ ] Notes textarea (optional)
- [ ] Save button → calls POST /visits/{id}/treatments/add

#### 3. Checkout Modal Enhancement
- [ ] Read-only treatment summary table
- [ ] Columns: Modality | Therapist | Duration | Time
- [ ] Checkbox: "Generate PDF for patient signature"
- [ ] If checked → auto-download PDF on checkout completion

#### 4. Patient Detail Modal Enhancement
- [ ] Add checkbox next to each visit in history
- [ ] "Download Selected Visits PDF" button (enabled when ≥1 checked)
- [ ] Button calls GET /patients/{id}/sign-sheet.pdf?visit_ids=x,y,z

#### 5. Treatment Records Page (NEW)
- [ ] New tab/page in main navigation
- [ ] Filters section:
  - Date range picker (from/to)
  - Patient dropdown (all patients)
  - Staff dropdown (therapists only)
  - Modality dropdown (all modalities)
- [ ] Apply Filters button
- [ ] Results table:
  - Patient | Visit Date | Modality | Therapist | Duration | Room
- [ ] Export CSV button
- [ ] Pagination (if >100 records)

---

## 📊 Implementation Progress

| Component | Status | Lines | Tests |
|-----------|--------|-------|-------|
| Database model | ✅ Complete | 20 | N/A |
| Backend schemas | ✅ Complete | 30 | N/A |
| Backend services | ✅ Complete | 200 | 4/4 pass |
| Backend routes | ✅ Complete | 70 | 4/4 pass |
| Frontend (all) | ❌ Not started | 0 | 0 |
| **Total Backend** | **✅ 100%** | **320** | **4/4** |
| **Total Frontend** | **❌ 0%** | **0** | **0** |

---

## 🧪 Test Coverage

### Backend Tests (4 tests, 421 lines)

```
✅ test_prd005_multiple_treatments_workflow
   - Creates 3 treatments (PT, E-stim, Massage)
   - Updates duration (30→45 min)
   - Lists treatments (verifies enrichment)
   - Filters by modality and therapist
   - Deletes one treatment
   - Verifies events logged
   
✅ test_cannot_add_treatment_to_checked_out_visit
   - Completes full visit → checkout
   - Attempts to add treatment
   - Expects 400 error
   
✅ test_treatment_without_therapist_defaults_to_actor
   - Adds treatment without therapist_id
   - Verifies therapist_id = actor_id
   
✅ test_treatment_records_date_filter
   - Creates treatment today
   - Queries for today → 1 result
   - Queries for future → 0 results
```

### Frontend Tests (not written yet)

```
⚠️ test_add_treatment_ui — PENDING
⚠️ test_treatment_list_edit_delete — PENDING
⚠️ test_checkout_treatment_summary — PENDING
⚠️ test_selective_pdf_generation — PENDING
⚠️ test_treatment_records_page_filters — PENDING
```

---

## 🎯 Next Steps (Priority Order)

### P0: Core UX (Backend complete, need UI)
1. [ ] Implement "Add Treatment" button + modal on active visits
2. [ ] Display treatment list with edit/delete on visit cards
3. [ ] Add treatment summary to checkout modal (read-only)
4. [ ] Write Playwright tests for treatment UI

### P1: Enhanced Workflow
5. [ ] Add "Generate PDF" checkbox in checkout modal
6. [ ] Implement auto-download PDF on checkout if checked
7. [ ] Add visit checkboxes in patient detail modal
8. [ ] Implement "Download Selected Visits PDF" button
9. [ ] Update PDF service to accept ?visit_ids query param

### P2: Reporting
10. [ ] Create Treatment Records page/tab
11. [ ] Implement filters (date, patient, staff, modality)
12. [ ] Add CSV export functionality
13. [ ] Add pagination for large result sets

### P3: Polish
14. [ ] Add treatment duration timer (start/stop)
15. [ ] Add treatment templates/favorites
16. [ ] Add modality autocomplete (if list grows)
17. [ ] Add bulk delete treatments

---

## 🐛 Known Issues

1. **Hardcoded actor_id** — Some routes use `actor_id="admin"` instead of JWT auth context
2. **No UI** — Backend APIs have zero UI integration
3. **PDF not enhanced** — Current PDF doesn't show multiple treatments yet
4. **No database migration** — visit_treatments table not created in production Supabase

---

## 📝 API Usage Examples

### Add Treatment
```bash
curl -X POST http://localhost:8000/prototype/visits/{visit_id}/treatments/add \
  -H "Content-Type: application/json" \
  -d '{
    "visit_id": "uuid",
    "modality": "E-stim",
    "therapist_id": "staff-uuid",
    "duration_minutes": 15,
    "notes": "Applied to lower back",
    "actor_id": "staff-uuid"
  }'
```

### List Treatments
```bash
curl http://localhost:8000/prototype/visits/{visit_id}/treatments
# Returns: {"treatments": [{"treatment_id": "...", "modality": "PT", "therapist_name": "Dr. Chen", ...}]}
```

### Query Treatment Records
```bash
curl "http://localhost:8000/prototype/treatment-records?date_from=2026-03-01&date_to=2026-03-31&modality=PT&staff_id=uuid"
# Returns: {"treatments": [{"patient_name": "John Doe", "therapist_name": "Dr. Chen", ...}]}
```

### Update Treatment
```bash
curl -X PATCH http://localhost:8000/prototype/visits/{visit_id}/treatments/{treatment_id}/update \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 45, "notes": "Extended session"}'
```

### Delete Treatment
```bash
curl -X DELETE http://localhost:8000/prototype/visits/{visit_id}/treatments/{treatment_id}/delete
# Returns: {"deleted": true, "treatment_id": "uuid"}
```

---

## 📚 References

- **PRD:** [docs/PRD/005-multiple-treatments-per-visit.md](/Users/zw/workspace/ClinicOS/docs/PRD/005-multiple-treatments-per-visit.md)
- **Implementation Guide:** [docs/IMPLEMENTATION-MULTIPLE-TREATMENTS.md](/Users/zw/workspace/ClinicOS/docs/IMPLEMENTATION-MULTIPLE-TREATMENTS.md)
- **Test Report:** [TEST-REPORT-PRD005.md](/Users/zw/workspace/ClinicOS/TEST-REPORT-PRD005.md)
- **Tests:** [backend/tests/test_treatments.py](/Users/zw/workspace/ClinicOS/backend/tests/test_treatments.py)
- **Features Tracker:** [tasks/features.json](/Users/zw/workspace/ClinicOS/tasks/features.json) (PRD005-BE-01 through PRD005-FE-04)

---

**Summary:** Backend fully functional and tested. Frontend implementation is the next critical priority to make this feature usable in production.
