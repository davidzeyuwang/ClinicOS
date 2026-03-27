# PRD-005: Multiple Treatments Per Visit + Enhanced Workflow

**Status:** Approved v1  
**Date:** 2026-03-27  
**Owner:** Product  
**Related:** PRD-001 (Daily Sign Sheet), PRD-004 (Form Gap Analysis)

---

## 1. Problem Statement

**Current limitation:** Each visit records only ONE `service_type` (e.g., "PT"). Real clinic sessions involve multiple concurrent modalities:
- Physical Therapy (30 min) + E-stim (15 min) + Massage (20 min)
- Multiple therapists may work on same patient
- Each modality has different duration, start/end times

**Business impact:**
- Cannot accurately bill insurance for multiple CPT codes per visit
- Cannot track individual therapist productivity per modality
- Sign-off sheets lack treatment detail granularity
- Cannot generate itemized patient records for compliance

---

## 2. User Stories

### US-1: Add Multiple Treatments to Visit
**As a** front desk staff  
**I want to** add multiple treatment modalities to an active visit  
**So that** I can record all therapies the patient receives in one session

**Acceptance Criteria:**
- Active visit card shows "+ Add Treatment" button
- Can add multiple treatments with different modalities
- Each treatment specifies: modality, therapist, duration (editable)
- Treatments display as list under visit card

### US-2: Review Treatments at Checkout
**As a** front desk staff  
**I want to** see all treatments performed before checkout  
**So that** I can verify copay and generate accurate sign sheet

**Acceptance Criteria:**
- Checkout modal shows read-only treatment summary table
- Columns: Modality, Therapist, Duration (min), Time
- Option to "Generate PDF for patient signature" (checkbox)
- PDF includes all treatments in visit history table

### US-3: Selective PDF Generation
**As a** billing staff  
**I want to** select specific visits to include in sign sheet PDF  
**So that** I can generate partial records (e.g., only this month's visits)

**Acceptance Criteria:**
- Patient detail modal shows checkboxes next to each visit
- "Download Selected Visits PDF" button (only enabled when ≥1 selected)
- Generated PDF includes only checked visits

### US-4: Treatment Records Reporting
**As a** clinic manager  
**I want to** view all treatments across patients with filters  
**So that** I can analyze therapist productivity and modality distribution

**Acceptance Criteria:**
- New "Treatment Records" page/tab
- Filters: Date range, Patient, Staff (therapist), Modality
- Table shows: Patient | Visit Date | Modality | Therapist | Duration | Room
- Export to CSV capability

---

## 3. Technical Requirements

### 3.1 Database Schema

**New table:** `visit_treatments`

```sql
CREATE TABLE visit_treatments (
    treatment_id TEXT PRIMARY KEY,
    visit_id TEXT NOT NULL REFERENCES visits(visit_id),
    modality TEXT NOT NULL,  -- PT, OT, E-stim, Massage, Cupping, etc.
    therapist_id TEXT REFERENCES staff(staff_id),
    duration_minutes INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_visit_treatments_visit ON visit_treatments(visit_id);
CREATE INDEX idx_visit_treatments_therapist ON visit_treatments(therapist_id);
```

**Migration strategy:**
- Keep `visits.service_type` for backward compatibility (mark as "Legacy")
- New visits with treatments leave `service_type` as empty or "Multiple"

### 3.2 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/prototype/visits/{visit_id}/treatments` | List treatments for visit |
| POST | `/prototype/visits/{visit_id}/treatments/add` | Add new treatment |
| PATCH | `/prototype/visits/{visit_id}/treatments/{treatment_id}/update` | Edit duration/notes |
| DELETE | `/prototype/visits/{visit_id}/treatments/{treatment_id}/delete` | Remove treatment |
| GET | `/prototype/treatment-records` | Query all treatments with filters |
| GET | `/prototype/patients/{patient_id}/sign-sheet.pdf?visit_ids=x,y,z` | Generate PDF for selected visits |

### 3.3 Event Sourcing

**New event types:**
- `TREATMENT_ADDED` — treatment created in visit
- `TREATMENT_UPDATED` — duration/notes changed
- `TREATMENT_DELETED` — treatment removed (soft delete)

All events logged to `event_log` table per ADR-001.

---

## 4. UI Design

### 4.1 Active Visits Card (Enhanced)

```
┌─────────────────────────────────────────┐
│ John Doe | R201 | Checked In            │
│ Service: Multiple Treatments            │
│                                         │
│ Treatments:                             │
│  • PT (Dr. Chen) - 30min                │
│  • E-stim (Dr. Chen) - 15min [Edit]    │
│  • Massage (Lisa Wu) - 20min [Edit]    │
│                                         │
│ [+ Add Treatment] [Start] [Checkout]   │
└─────────────────────────────────────────┘
```

### 4.2 Add Treatment Modal

```
┌─────────────────────────────────────────┐
│         Add Treatment                   │
├─────────────────────────────────────────┤
│ Modality:  [Dropdown: PT, E-stim, ...]│
│ Therapist: [Dropdown: Staff list]      │
│ Duration:  [30] minutes                 │
│ Notes:     [___________]                │
│                                         │
│          [Cancel]  [Add Treatment]      │
└─────────────────────────────────────────┘
```

### 4.3 Checkout Modal (Enhanced)

```
┌─────────────────────────────────────────┐
│      Checkout: John Doe                 │
├─────────────────────────────────────────┤
│ Treatments Performed:                   │
│ ┌─────────────────────────────────────┐ │
│ │ Modality  Therapist    Duration Time││
│ │ PT        Dr. Chen     30min    10:00││
│ │ E-stim    Dr. Chen     15min    10:30││
│ │ Massage   Lisa Wu      20min    10:45││
│ └─────────────────────────────────────┘ │
│                                         │
│ Copay Collected: [$25] ✓                │
│ Walk & Dance:    [✓] Verified           │
│ Patient Signed:  [✓] Completed          │
│                                         │
│ [✓] Generate sign sheet PDF             │
│                                         │
│         [Cancel]  [Complete Checkout]   │
└─────────────────────────────────────────┘
```

### 4.4 Patient Detail Modal (Enhanced)

```
┌─────────────────────────────────────────┐
│  John Doe | DOB: 1980-05-15             │
├─────────────────────────────────────────┤
│ Visit History:                          │
│ [✓] 2026-03-27 | PT+E-stim | $25 | ✓  │
│ [✓] 2026-03-20 | Massage | $25 | ✓     │
│ [ ] 2026-03-13 | PT | $25 | ✓          │
│                                         │
│ [Download Selected Visits PDF (2)]      │
│ [Download All History PDF]              │
└─────────────────────────────────────────┘
```

### 4.5 Treatment Records Page (NEW)

```
┌─────────────────────────────────────────┐
│        Treatment Records                │
├─────────────────────────────────────────┤
│ Filters:                                │
│ Date: [2026-03-01] to [2026-03-31]      │
│ Patient: [All ▼]  Staff: [All ▼]        │
│ Modality: [All ▼]                       │
│           [Apply Filters] [Export CSV]  │
├─────────────────────────────────────────┤
│ Patient    Date       Modality  Therapist│
│ John Doe   03-27 10:00 PT      Dr. Chen  │
│ John Doe   03-27 10:30 E-stim  Dr. Chen  │
│ Jane Smith 03-27 11:00 Massage Lisa Wu   │
│ ...                                     │
└─────────────────────────────────────────┘
```

---

## 5. Implementation Phases

### Phase 1: Database + Backend APIs (P0)
- Create `visit_treatments` table (migration)
- Implement 6 new API endpoints
- Add event logging for treatments
- **Estimate:** 8 hours

### Phase 2: Core UX (P0)
- Add treatment management to active visits
- Enhance checkout modal with treatment review
- **Estimate:** 6 hours

### Phase 3: PDF Enhancements (P1)
- Add "Generate PDF at checkout" checkbox
- Implement selective PDF generation with visit checkboxes
- Update PDF template to show all treatments per visit
- **Estimate:** 4 hours

### Phase 4: Treatment Records Page (P2)
- New page/tab for treatment records
- Filters + export to CSV
- **Estimate:** 5 hours

**Total Estimate:** 23 hours (~3 days)

---

## 6. Success Metrics

- **Adoption:** ≥80% of visits use multiple treatments within 2 weeks
- **Accuracy:** Zero billing disputes due to missing treatment records
- **Efficiency:** Checkout time reduced by 30% (pre-filled treatments)
- **Compliance:** 100% of PDFs include complete treatment breakdown

---

## 7. Out of Scope (Future)

- Integration with billing system CPT code mapping
- Automated insurance claim generation
- Real-time treatment duration tracking (timer)
- Treatment templates/favorites

---

## 8. Dependencies

- Requires: Event sourcing framework (ADR-001)
- Requires: PDF generation service (fpdf2)
- Requires: Staff table with therapist roles

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Legacy `service_type` confusion | Medium | Keep field but mark "LEGACY" in code comments |
| PDF generation performance with 100+ visits | Medium | Add pagination/date range constraints |
| Multiple therapists per visit complicates billing | High | Add CSV export for manual billing review |

---

## 10. Compliance Notes

- All treatment records stored in `event_log` (immutable audit trail)
- No PII in treatment notes visible to non-providers
- Patient signature required before PDF generation (checkout)
- Retention: 7 years per HIPAA (event_log never deleted)

---

**Approval:**
- [x] Product Manager: Approved 2026-03-27
- [x] Engineering Lead: Feasible, 3-day estimate
- [x] Compliance: HIPAA-compliant if event logging enforced
