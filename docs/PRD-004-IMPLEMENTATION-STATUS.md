# PRD-004 Implementation Status — What's Fixed vs What's Missing

**Last Updated:** 2026-03-27

---

## ✅ IMPLEMENTED (Prior Session — 2026-03-26)

### 1. Visit Checkout Fields (§2.2 from PRD-004)

| Field | Database | API | UI | Status |
|-------|----------|-----|----|----|
| `copay_collected` | ✅ Visit.copay_collected | ✅ /portal/checkout | ✅ Checkout modal | **DONE** |
| `wd_verified` | ✅ Visit.wd_verified | ✅ /portal/checkout | ✅ Checkout modal | **DONE** |
| `patient_signed` | ✅ Visit.patient_signed | ✅ /portal/checkout | ✅ Checkout modal | **DONE** |

**Files Changed:**
- [backend/app/models/tables.py](backend/app/models/tables.py#L138-L140)
- [backend/app/services/db_service.py](backend/app/services/db_service.py#L285-L310)
- [frontend/index.html](frontend/index.html#L455-L467)

**Test Coverage:**
- ✅ [backend/tests/test_prototype_e2e.py](backend/tests/test_prototype_e2e.py#L210-L227) — Tests checkout with all 3 fields
- ✅ [frontend/tests/e2e/ops-board.spec.ts](frontend/tests/e2e/ops-board.spec.ts) — Tests #3, #4, #5, #7

---

### 2. Patient Visit History (§2.2 from PRD-004)

**Endpoint:** `GET /prototype/patients/{patient_id}/visits`

**Response:**
```json
{
  "visits": [
    {
      "visit_id": "...",
      "check_in_time": "...",
      "check_out_time": "...",
      "status": "checked_out",
      "copay_collected": 25.0,    // ✅ NEW
      "wd_verified": true,        // ✅ NEW
      "patient_signed": true      // ✅ NEW
    }
  ]
}
```

**UI Integration:**
- Patient detail modal → Visit History section
- Shows total copay collected across all visits
- Displays ✓ checkmarks for WD/Signed columns

**Files:**
- [backend/app/services/db_service.py](backend/app/services/db_service.py#L416-L425)
- [frontend/index.html](frontend/index.html#L604-L611)

---

### 3. Daily Summary with Copay Totals (§2.3 from PRD-004)

**Endpoint:** `GET /prototype/projections/daily-summary?date=YYYY-MM-DD`

**Response:**
```json
{
  "date": "2026-03-27",
  "total_check_ins": 12,
  "total_checked_out": 10,
  "copay_total": 275.50,        // ✅ NEW — Sum of all copay_collected
  "active_visits": 2,
  "visits": [...]
}
```

**Files:**
- [backend/app/services/db_service.py](backend/app/services/db_service.py#L428-L460)
- [frontend/index.html](frontend/index.html#L224) — Shows copay total in report tab

---

### 4. PDF Sign-Sheet Generation (§2.2 from PRD-004)

**Endpoint:** `GET /prototype/patients/{patient_id}/sign-sheet.pdf`

**Features:**
- Individual patient sign sheet (個人簽字表)
- Patient demographics + insurance summary
- Visit history table with columns:
  - Date | Service Type | Copay CC | WD | Signed
- Patient signature line (for print workflow)

**PDF Library:** fpdf2 (pure Python, ASCII-safe)

**Files:**
- [backend/app/services/pdf_service.py](backend/app/services/pdf_service.py#L38-L171)
- [backend/app/routers/db_routes.py](backend/app/routers/db_routes.py#L266-L279)

**UI Access:**
- Patient detail modal → "📄 Download Sign Sheet PDF" button

---

### 5. Room Board — Active Visits Logic (§2.5 from PRD-004)

**Behavior:** "Active Visits" = Visits IN PROGRESS

**Query Logic:**
```python
Visit.status.in_(["checked_in", "in_service", "service_completed"])
```

**After Checkout:**
```python
visit.status = "checked_out"  # → NO LONGER ACTIVE ✅
```

**This is CORRECT behavior:**
- Active visits = currently in progress
- Checked-out visits appear in:
  - Patient visit history
  - Daily summary
  - Reports

---

## ❌ NOT IMPLEMENTED (PRD-004 Backlog)

### Phase 2 — Insurance Information Expansion (§2.1 from PRD-004)

**Current State:**
- ✅ Basic insurance: carrier_name, member_id, group_number, copay_amount
- ❌ **Missing:** Full insurance verification fields

**Missing Fields (from paper form analysis):**

| Field | Priority | Database Column | Notes |
|-------|----------|----------------|-------|
| Plan Type (PPO/HMO/EPO) | **P0** | `plan_type` | Critical for billing |
| Office Visit Copay | P0 | Already have `copay_amount` | ✅ Exists |
| Effective Date Range | P0 | `effective_date_start`, `effective_date_end` | Validate coverage |
| Referral Required (Y/N) | P0 | `referral_required` | Pre-visit check |
| Pre-Authorization Required | P0 | `preauth_required` | Critical for services |
| Allow Visits (annual) | P0 | `allow_visits` | Visit limit tracking |
| Used Visits | P0 | `used_visits` | Auto-increment on checkout |
| Deductible Individual | P0 | `deductible_individual` | Patient cost calc |
| Deductible Met (IND) | P0 | `deductible_individual_met` | Real-time tracking |
| Deductible Family | P1 | `deductible_family` | Optional |
| Family Deductible Met | P1 | `deductible_family_met` | Optional |
| OOP Max Individual | P0 | `oop_max_individual` | Required for billing |
| OOP Met | P0 | `oop_met_individual` | Track annually |
| Coverage % | P0 | `coverage_pct` | E.g., 90% |
| Patient Pay (calculated) | P0 | `patient_pay` | Derived field |
| Checked By (staff) | P1 | `checked_by` | Audit trail |

**Dual Insurance Support:**
- ❌ Primary vs Secondary insurance columns
- ❌ Two-policy comparison view
- ❌ `is_primary` boolean flag

**Required Changes:**
```sql
ALTER TABLE insurance_policies ADD COLUMN plan_type VARCHAR(20);
ALTER TABLE insurance_policies ADD COLUMN effective_date_start DATE;
ALTER TABLE insurance_policies ADD COLUMN effective_date_end DATE;
ALTER TABLE insurance_policies ADD COLUMN referral_required BOOLEAN DEFAULT FALSE;
ALTER TABLE insurance_policies ADD COLUMN preauth_required BOOLEAN DEFAULT FALSE;
ALTER TABLE insurance_policies ADD COLUMN allow_visits INTEGER;
ALTER TABLE insurance_policies ADD COLUMN used_visits INTEGER DEFAULT 0;
ALTER TABLE insurance_policies ADD COLUMN deductible_individual NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN deductible_individual_met NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN oop_max_individual NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN oop_met_individual NUMERIC(10,2);
ALTER TABLE insurance_policies ADD COLUMN coverage_pct NUMERIC(5,2);
ALTER TABLE insurance_policies ADD COLUMN is_primary BOOLEAN DEFAULT TRUE;
```

---

### Phase 2 — Visit Treatments Table (§2.4 from PRD-004)

**Current State:**
- ✅ Single `service_type` field on Visit table
- ❌ **Missing:** Multiple concurrent treatments per visit

**Problem:**
- Real clinic sessions use **multiple modalities simultaneously**
- E.g., one visit = PT + E-stim + Massage + Cupping
- Current system: only 1 service_type string

**Required:**
```sql
CREATE TABLE visit_treatments (
    treatment_id   UUID PRIMARY KEY,
    visit_id       UUID NOT NULL REFERENCES visits(visit_id),
    modality       VARCHAR(50) NOT NULL,  -- PT/OT/Eval/E-stim/Massage/Cupping/Acupuncture
    therapist_id   UUID REFERENCES staff(staff_id),
    duration_min   INTEGER,
    notes          TEXT,
    recorded_at    TIMESTAMPTZ DEFAULT NOW()
);
```

**UI Changes:**
- Visit detail modal → Treatment list (add/remove multiple)
- Modality dropdown: PT, OT, Eval, Re-eval, E-stim, Massage, Cupping, Acupuncture, Taping
- Per-treatment therapist assignment

---

### Phase 2 — Room Board Enhancements (§2.5 from PRD-004)

**Current State:**
- ✅ Room status (available/occupied/cleaning/OOS)
- ✅ Current patient + service type display
- ❌ **Missing:** Floor grouping in UI

**Required:**
- `floor` field exists in Room table (16F/18F)
- **UI not grouped by floor** — currently flat list

**Changes:**
```javascript
// Group rooms by floor in UI
const roomsByFloor = rooms.reduce((acc, room) => {
  const floor = room.floor || '1F';
  if (!acc[floor]) acc[floor] = [];
  acc[floor].push(room);
  return acc;
}, {});

// Render separate sections for each floor
Object.keys(roomsByFloor).sort().forEach(floor => {
  html += `<h3>${floor}</h3>`;
  html += renderRoomCards(roomsByFloor[floor]);
});
```

---

### Phase 3 — Eligibility Verification Workflow (§2.7 from PRD-004)

**Current State:**
- ❌ **No eligibility verification workflow** (currently done in Asana)

**Required Tables:**
```sql
CREATE TABLE eligibility_cases (
    case_id         UUID PRIMARY KEY,
    patient_id      UUID REFERENCES patients(patient_id),
    insurance_id    UUID REFERENCES insurance_policies(policy_id),
    carrier         VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'pending',  -- pending/in_progress/verified/failed
    verified_by     UUID REFERENCES staff(staff_id),
    verified_at     TIMESTAMPTZ,
    notes           TEXT,
    year            INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE eligibility_checklist_items (
    item_id     UUID PRIMARY KEY,
    case_id     UUID REFERENCES eligibility_cases(case_id),
    question    TEXT NOT NULL,   -- "Is PT covered?", "What's the copay?", etc.
    answered    BOOLEAN DEFAULT FALSE,
    answer      TEXT,
    order_num   INTEGER
);
```

**UI Module:**
- New "Eligibility" tab in main nav
- Task list view (replace Asana)
- Task detail form with 5-question SOP checklist
- Auto-populate insurance fields after verification

**5 Standard Questions (from Asana workflow):**
1. Is Physical Therapy covered under this plan?
2. What is the copay amount per visit?
3. How many visits are authorized annually?
4. Is a referral required?
5. Is pre-authorization required?

---

### Phase 3 — Patient Archive Features (§2.6 from PRD-004)

**Current State:**
- ✅ Patient list with search
- ✅ Patient detail with visit history
- ❌ **Missing:** Digital signature archive (currently use Notability)

**Required:**
- In-network / out-of-network flag on Patient table
- Digital signature capture (canvas-based or upload)
- Archived sign sheets per patient (versioned)
- Year-based archive grouping

**Changes:**
```sql
ALTER TABLE patients ADD COLUMN network_status VARCHAR(20) DEFAULT 'in_network';
ALTER TABLE patients ADD COLUMN primary_insurance_id UUID;
ALTER TABLE patients ADD COLUMN secondary_insurance_id UUID;

CREATE TABLE patient_signatures (
    signature_id   UUID PRIMARY KEY,
    patient_id     UUID REFERENCES patients(patient_id),
    visit_id       UUID REFERENCES visits(visit_id),
    signature_data TEXT,  -- Base64 canvas data OR file path
    signed_at      TIMESTAMPTZ DEFAULT NOW(),
    signature_type VARCHAR(20)  -- digital/uploaded/printed
);
```

---

## Summary Table: PRD-004 Implementation Status

| Feature | Priority | Status | Phase |
|---------|----------|--------|-------|
| Copay collected field | P0 | ✅ **DONE** | M1 |
| WD verified field | P0 | ✅ **DONE** | M1 |
| Patient signed field | P0 | ✅ **DONE** | M1 |
| Visit history with copay | P0 | ✅ **DONE** | M1 |
| Daily copay totals | P0 | ✅ **DONE** | M1 |
| PDF sign-sheet generation | P0 | ✅ **DONE** | M1 |
| Active visits logic | P0 | ✅ **DONE** | M1 |
| **Full insurance fields** | **P0** | ❌ **TODO** | Phase 2 |
| Dual insurance support | P0 | ❌ TODO | Phase 2 |
| Visit treatments table | P1 | ❌ TODO | Phase 2 |
| Room floor grouping UI | P1 | ❌ TODO | Phase 2 |
| Eligibility workflow | P1 | ❌ TODO | Phase 3 |
| Digital signatures | P2 | ❌ TODO | Phase 3 |
| Patient network status | P1 | ❌ TODO | Phase 2 |

---

## How to Verify What's Implemented

### 1. Run Existing E2E Test

```bash
cd backend
/usr/bin/python3 -m pytest tests/test_prototype_e2e.py::test_prd_v2_e2e_domain_flow -v
```

**What it validates:**
- ✅ Copay collected: L224 `assert co["copay_collected"] == 25.0`
- ✅ WD verified: L225 `assert co["wd_verified"] is True`
- ✅ Patient signed: L226 `assert co["patient_signed"] is True`
- ✅ Visit history: L283-290
- ✅ Daily copay total: L293-297

### 2. Manual UI Test

1. Start server: `uvicorn app.main:app --reload --port 8000`
2. Open http://localhost:8000/ui/index.html
3. Create room, staff, patient
4. Check in patient
5. End service
6. **Click Checkout:**
   - Enter copay amount
   - Check WD Verified
   - Check Patient Signed
7. Open patient detail → verify visit history shows all 3 fields
8. Click PDF download → verify sign sheet PDF generates

### 3. Check Production Deployment

**URL:** https://clinicos-psi.vercel.app

All features live and working ✅

---

## Next Steps (Your Choice)

### Option 1: Implement Phase 2 Features (Insurance Expansion)

**Priority Order:**
1. Full insurance fields (deductible, OOP, plan type) — HIGH IMPACT
2. Visit treatments table (multiple modalities) — MEDIUM IMPACT
3. Room floor grouping UI — LOW IMPACT

**Estimated:** 1-2 sessions for full insurance fields

### Option 2: Continue with New Features (Beyond PRD-004)

If PRD-004 gaps are acceptable, move to next milestone features:
- Billing/claims module
- Staff scheduling
- Patient portal
- Clinical note templates

---

**Report Generated:** 2026-03-27  
**Total PRD-004 Features:** 14  
**Implemented:** 7 (50%)  
**Remaining:** 7 (50%)  
**P0 Features Remaining:** 2 (insurance fields, dual insurance)
