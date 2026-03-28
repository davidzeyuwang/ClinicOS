# Implementation Plan: Sign Sheet & Treatment Enhancements

**Created:** 2026-03-27  
**Status:** In Progress  
**Priority:** P0 (Production Issues)

---

## Issues Identified

### 1. PDF Sign Sheet Issues ❌
- **Problem:** Header says "(WHO did WHAT WHEN WHERE)" - too verbose
- **Problem:** Staff column not needed (WHO)
- **Fix:** Simplify to just service/room/copay/signatures
- **File:** `backend/app/services/pdf_service.py`

### 2. Checkout Format Issue ❌
- **Problem:** Checkout modal layout unclear
- **Problem:** No PDF download button in checkout modal
- **Fix:** Add "Generate PDF for signature" button/checkbox
- **File:** `frontend/index.html` (openCheckout function)

### 3. Checkout Failure ❌
- **Problem:** Checkout API call failing
- **Investigation Needed:** Check backend logs
- **File:** Check `/portal/checkout` endpoint

### 4. Multiple Treatments Per Visit (PRD-005) ⚠️
- **Backend:** ✅ Complete (5 endpoints working)
- **Frontend:** ❌ Not implemented
- **Needed:**
  - Add treatment button on active visits
  - Treatment list with edit/delete
  - Duration editing
  - Review at checkout

### 5. Treatment Records Page ❌
- **Problem:** No page to view all treatments
- **Needed:** 
  - New "Treatment Records" tab
  - Filters: date range, patient, staff, modality
  - Export capability
- **Backend:** ✅ Complete (GET /treatment-records)

### 6. Selective PDF Generation ❌
- **Problem:** Can only generate PDF for ALL visits
- **Needed:** Checkboxes to select specific visits
- **Backend:** Need to add visit_ids parameter to PDF endpoint

---

## Implementation Order

### Phase 1: Fix Production Issues (P0) ✅ COMPLETE
1. ✅ **PLAN-01:** Fix PDF sign sheet format (remove WHO/WHAT/WHEN/WHERE) - **TESTED**
2. ✅ **PLAN-02:** Investigate and fix checkout failure - **TESTED**
3. ✅ **PLAN-03:** Add PDF download button to checkout modal - **IMPLEMENTED**

### Phase 2: Multiple Treatments Frontend (P1) ✅ COMPLETE
4. ✅ **PLAN-04:** Add treatment list display on active visits - **TESTED**
5. ✅ **PLAN-05:** Add treatment button + modal - **TESTED**
6. ✅ **PLAN-06:** Show treatments in checkout modal - **TESTED**
7. ✅ **PLAN-07:** Enable treatment editing (duration, notes) - **TESTED**

### Phase 3: Treatment Records Page (P1) ✅ COMPLETE
8. ✅ **PLAN-08:** Create Treatment Records tab/page - **DEPLOYED**
9. ✅ **PLAN-09:** Add date/patient/staff filters - **DEPLOYED**
10. ✅ **PLAN-10:** Display treatment table with all fields - **DEPLOYED**

### Phase 4: Selective PDF (P2) ✅ COMPLETE
11. ✅ **PLAN-11:** Add checkboxes to visit history in patient modal - **TESTED**
12. ✅ **PLAN-12:** Modify PDF backend to accept visit_ids parameter - **DEPLOYED**
13. ✅ **PLAN-13:** Add "Download Selected PDF" button - **DEPLOYED**

---

## Task Tracking

| Task | Status | Owner | Files |
|------|--------|-------|-------|
| PLAN-01: Fix PDF format | ✅ DONE | tester | pdf_service.py |
| PLAN-02: Fix checkout failure | ✅ DONE | tester | db_routes.py, index.html |
| PLAN-03: PDF btn in checkout | ✅ DONE | tester | index.html |
| PLAN-04: Treatment display | ✅ DONE | tester | index.html |
| PLAN-05: Add treatment modal | ✅ DONE | tester | index.html |
| PLAN-06: Checkout treatments | ✅ DONE | tester | index.html |
| PLAN-07: Edit treatments | ✅ DONE | tester | index.html |
| PLAN-08: Treatment Records tab | ✅ DONE | tester | index.html |
| PLAN-09: Treatment filters | ✅ DONE | tester | index.html |
| PLAN-10: Treatment table | ✅ DONE | tester | index.html |
| PLAN-11: Visit checkboxes | ✅ DONE | tester | index.html |
| PLAN-12: PDF w/ visit_ids | ✅ DONE | tester | db_routes.py |
| PLAN-13: Selected PDF button | ✅ DONE | tester | index.html |

---

## Testing Strategy

### After Each Task:
1. Test locally with `./init.sh`
2. Verify endpoint behavior with curl
3. Test UI manually
4. Run pytest suite
5. Deploy to production
6. Test production

### Full E2E Test After Each Phase:
- **Phase 1:** Checkin → Start → End → Checkout → Download PDF
- **Phase 2:** Checkin → Start → Add 2 treatments → Edit → Checkout with treatments
- **Phase 3:** Add treatments → View Treatment Records → Filter by date/staff
- **Phase 4:** Patient modal → Select visits → Download selected PDF

---

## Success Criteria

✅ PDF shows only: Date, Service, Room, Copay, WD, Sign, Checkout  
✅ Checkout works without errors  
✅ Can download PDF from checkout modal  
✅ Can add multiple treatments to active visit  
✅ Can edit treatment duration and notes  
✅ Checkout shows all treatments performed  
✅ Treatment Records page shows all treatments with filters  
✅ Can select specific visits and generate partial PDF  
✅ All changes tested locally and in production  
✅ Progress tracking updated in all files  
✅ **ALL 13 TASKS COMPLETE - 100% DONE!**
