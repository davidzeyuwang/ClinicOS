# Implementation Plan: Multiple Treatments + Enhanced PDF Workflow

## 🎯 Overview

This document outlines the complete implementation for:
1. Multiple treatments per visit
2. PDF generation at checkout
3. Selective PDF generation
4. Treatment records page with filters

---

## 📊 Phase 1: Database & Backend (FOUNDATION)

### 1.1 New Table: `visit_treatments`

**Already added to** `backend/app/models/tables.py`:

```python
class VisitTreatment(Base):
    treatment_id: str         # UUID
    visit_id: str             # FK to visits
    modality: str             # "PT", "E-stim", "Massage", "Cupping"
    therapist_id: str         # FK to staff (can differ per treatment)
    duration_minutes: int     # e.g., 30, 45, 60
    started_at: datetime
    completed_at: datetime
    notes: str
```

### 1.2 New API Endpoints Needed

#### `/prototype/visits/{visit_id}/treatments` - List treatments
```python
GET /prototype/visits/{visit_id}/treatments
Response: {"treatments": [...]}
```

#### `/prototype/visits/{visit_id}/treatments/add` - Add treatment
```python
POST /prototype/visits/{visit_id}/treatments/add
Body: {
  "modality": "E-stim",
  "therapist_id": "staff-uuid",
  "duration_minutes": 15,
  "actor_id": "staff-uuid"
}
```

#### `/prototype/visits/{visit_id}/treatments/{treatment_id}/update` - Edit treatment
```python
PATCH /prototype/visits/{visit_id}/treatments/{treatment_id}/update
Body: {
  "duration_minutes": 20,
  "notes": "Patient responded well"
}
```

#### `/prototype/visits/{visit_id}/treatments/{treatment_id}/delete` - Remove treatment
```python
DELETE /prototype/visits/{visit_id}/treatments/{treatment_id}/delete
```

#### `/prototype/treatment-records` - All treatments with filters
```python
GET /prototype/treatment-records?date_from=2026-03-01&date_to=2026-03-31&patient_id=uuid&staff_id=uuid
Response: {
  "treatments": [
    {
      "treatment_id": "...",
      "visit_id": "...",
      "patient_name": "John Doe",
      "therapist_name": "Dr. Chen",
      "room_name": "R201",
      "modality": "PT",
      "duration_minutes": 45,
      "started_at": "2026-03-27T10:00:00Z",
      "completed_at": "2026-03-27T10:45:00Z"
    }
  ]
}
```

#### `/prototype/patients/{patient_id}/sign-sheet.pdf` - Enhanced PDF with filters
```python
GET /prototype/patients/{patient_id}/sign-sheet.pdf?visit_ids=uuid1,uuid2,uuid3&date_from=2026-03-01
# Generates PDF for selected visits only
```

---

## 🎨 Phase 2: UI Updates

### 2.1 Checkout Modal Enhancement

**Location:** `frontend/index.html` - checkout modal

**Add:**
```html
<!-- Treatment Summary (Read-only review) -->
<div class="treatments-summary mb-3">
  <h5 class="text-sm font-semibold mb-2">Treatments Provided:</h5>
  <div id="checkout-treatments-list"></div>
  <!-- Shows: PT (45min by Dr. Chen), E-stim (15min by Dr. Chen) -->
</div>

<!-- PDF Generation Option -->
<div class="flex items-center gap-2 mb-3">
  <input type="checkbox" id="co-generate-pdf" checked>
  <label for="co-generate-pdf">Generate sign sheet PDF for patient signature</label>
</div>

<!-- Existing checkout fields -->
<input id="co-cc" type="number" placeholder="Copay $">
<!-- ... -->
```

**Checkout flow:**
1. Review all treatments (read-only)
2. Enter copay/WD/signed
3. If "Generate PDF" checked → Open PDF in new tab after successful checkout
4. Patient signs PDF on tablet/printout

### 2.2 Active Visit Detail Card - Add Treatments

**Location:** `frontend/index.html` - active visits section

**Add button to each active visit card:**
```html
<div class="visit-card">
  <div class="flex justify-between">
    <span>John Doe - Room R201</span>
    <div class="flex gap-1">
      <button onclick="openAddTreatment('visit-uuid')" class="btn btn-xs">
        + Add Treatment
      </button>
      <button onclick="openCheckout('visit-uuid')" class="btn btn-xs btn-green">
        Check Out
      </button>
    </div>
  </div>
  
  <!-- Treatments list (editable) -->
  <div class="treatments-list mt-2">
    <div class="treatment-item">
      <span>PT - 45min - Dr. Chen</span>
      <button onclick="editTreatment('treatment-uuid')">✏️</button>
      <button onclick="deleteTreatment('treatment-uuid')">🗑️</button>
    </div>
    <div class="treatment-item">
      <span>E-stim - 15min - Dr. Chen</span>
      <button onclick="editTreatment('treatment-uuid2')">✏️</button>
      <button onclick="deleteTreatment('treatment-uuid2')">🗑️</button>
    </div>
  </div>
</div>
```

### 2.3 Add Treatment Modal

```html
<div id="add-treatment-modal" class="modal">
  <h3>Add Treatment to Visit</h3>
  <form onsubmit="addTreatment(event)">
    <label>Treatment Modality</label>
    <select id="at-modality" required>
      <option value="PT">Physical Therapy</option>
      <option value="OT">Occupational Therapy</option>
      <option value="PT-Eval">PT Evaluation</option>
      <option value="OT-Eval">OT Evaluation</option>
      <option value="E-stim">Electrical Stimulation</option>
      <option value="Massage">Therapeutic Massage</option>
      <option value="Cupping">Cupping Therapy</option>
      <option value="Acupuncture">Acupuncture</option>
      <option value="Taping">Kinesio Taping</option>
      <option value="Ultrasound">Ultrasound Therapy</option>
      <option value="Heat/Cold">Heat/Cold Therapy</option>
      <option value="Exercise">Therapeutic Exercise</option>
    </select>
    
    <label>Therapist</label>
    <select id="at-therapist" required>
      <!-- Populated from staff list -->
    </select>
    
    <label>Duration (minutes)</label>
    <input id="at-duration" type="number" value="30" min="5" max="180" step="5">
    
    <label>Notes (optional)</label>
    <textarea id="at-notes" rows="2"></textarea>
    
    <div class="flex gap-2 mt-3">
      <button type="submit" class="btn btn-blue">Add Treatment</button>
      <button type="button" onclick="closeModal()" class="btn btn-outline">Cancel</button>
    </div>
  </form>
</div>
```

### 2.4 Patient Page - Selective PDF Generation

**Location:** Patient detail modal

**Replace current PDF button with:**
```html
<div class="flex items-center justify-between mb-2">
  <h4 class="font-semibold">📋 Visit History (${visList.length})</h4>
  <div class="flex gap-2">
    <button onclick="generateSelectivePDF('${pid}')" class="btn btn-xs btn-outline">
      📄 Select Visits for PDF
    </button>
    <a href="${API}/patients/${pid}/sign-sheet.pdf" target="_blank" class="btn btn-xs btn-blue">
      📄 Download Full Sign Sheet
    </a>
  </div>
</div>

<!-- In visit history table, add checkboxes -->
<table>
  <thead>
    <tr>
      <th><input type="checkbox" id="select-all-visits"></th>
      <th>Date</th>
      <th>Service</th>
      <!-- ... -->
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><input type="checkbox" class="visit-select" data-visit-id="${v.visit_id}"></td>
      <td>${dt}</td>
      <!-- ... -->
    </tr>
  </tbody>
</table>
```

**Function:**
```javascript
function generateSelectivePDF(patientId) {
  const selected = Array.from(document.querySelectorAll('.visit-select:checked'))
    .map(cb => cb.dataset.visitId)
    .join(',');
  
  if (!selected) {
    toast('Please select at least one visit', 'error');
    return;
  }
  
  const url = `${API}/patients/${patientId}/sign-sheet.pdf?visit_ids=${selected}`;
  window.open(url, '_blank');
}
```

### 2.5 NEW PAGE: Treatment Records

**Add new tab in main navigation:**
```html
<nav>
  <button onclick="showTab('ops')">Ops Board</button>
  <button onclick="showTab('patients')">Patients</button>
  <button onclick="showTab('treatments')">📊 Treatment Records</button> <!-- NEW -->
  <button onclick="showTab('appointments')">Appointments</button>
  <button onclick="showTab('reports')">Reports</button>
  <button onclick="showTab('admin')">Admin</button>
</nav>
```

**Treatment Records Page Content:**
```html
<div id="tab-treatments" class="tab-content">
  <h2>📊 Treatment Records</h2>
  
  <!-- Filters -->
  <div class="filters-bar flex gap-3 mb-4">
    <div>
      <label class="text-xs">Date From</label>
      <input type="date" id="filter-date-from" class="input input-sm">
    </div>
    <div>
      <label class="text-xs">Date To</label>
      <input type="date" id="filter-date-to" class="input input-sm">
    </div>
    <div>
      <label class="text-xs">Patient</label>
      <select id="filter-patient" class="input input-sm">
        <option value="">All Patients</option>
        <!-- Populated dynamically -->
      </select>
    </div>
    <div>
      <label class="text-xs">Staff</label>
      <select id="filter-staff" class="input input-sm">
        <option value="">All Staff</option>
        <!-- Populated dynamically -->
      </select>
    </div>
    <div class="flex items-end">
      <button onclick="applyTreatmentFilters()" class="btn btn-sm btn-blue">
        🔍 Filter
      </button>
      <button onclick="resetTreatmentFilters()" class="btn btn-sm btn-outline ml-2">
        Clear
      </button>
    </div>
  </div>
  
  <!-- Results Summary -->
  <div class="bg-gray-50 rounded p-3 mb-3">
    <div class="flex gap-6 text-sm">
      <div><strong id="tr-total-treatments">0</strong> treatments</div>
      <div><strong id="tr-total-duration">0</strong> total minutes</div>
      <div><strong id="tr-unique-patients">0</strong> patients</div>
    </div>
  </div>
  
  <!-- Treatment Records Table -->
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="bg-gray-100">
          <th class="text-left p-2">Date/Time</th>
          <th class="text-left p-2">Patient</th>
          <th class="text-left p-2">Treatment</th>
          <th class="text-left p-2">Therapist (WHO)</th>
          <th class="text-left p-2">Room (WHERE)</th>
          <th class="text-right p-2">Duration</th>
          <th class="text-left p-2">Visit Status</th>
          <th class="text-left p-2">Notes</th>
        </tr>
      </thead>
      <tbody id="treatment-records-tbody">
        <!-- Populated via loadTreatmentRecords() -->
      </tbody>
    </table>
  </div>
  
  <!-- Export Options -->
  <div class="mt-4 flex gap-2">
    <button onclick="exportTreatmentsCSV()" class="btn btn-sm btn-outline">
      📊 Export to CSV
    </button>
    <button onclick="exportTreatmentsPDF()" class="btn btn-sm btn-outline">
      📄 Export to PDF
    </button>
  </div>
</div>
```

---

## 🔧 Phase 3: Backend Implementation

### File: `backend/app/services/db_service.py`

Add these new functions:

```python
# ==================== VISIT TREATMENTS ====================

async def add_treatment_to_visit(db: AsyncSession, visit_id: str, modality: str, 
                                  therapist_id: str, duration_minutes: int,
                                  actor_id: str, notes: Optional[str] = None) -> dict:
    """Add a treatment modality to an active visit."""
    from app.models.tables import VisitTreatment
    
    # Verify visit exists and is active
    visit = await db.get(Visit, visit_id)
    if not visit or visit.status not in ("checked_in", "in_service", "service_completed"):
        raise ValueError("Visit not found or not active")
    
    treatment = VisitTreatment(
        treatment_id=_new_id(),
        visit_id=visit_id,
        modality=modality,
        therapist_id=therapist_id,
        duration_minutes=duration_minutes,
        started_at=_utc_now(),
        notes=notes,
    )
    db.add(treatment)
    
    await _append_event(db, "TREATMENT_ADDED", actor_id, {
        "visit_id": visit_id,
        "treatment_id": treatment.treatment_id,
        "modality": modality,
        "therapist_id": therapist_id,
        "duration_minutes": duration_minutes,
    })
    
    await db.commit()
    return _treatment_to_dict(treatment)


async def update_treatment(db: AsyncSession, treatment_id: str, 
                           duration_minutes: Optional[int] = None,
                           notes: Optional[str] = None,
                           actor_id: str = None) -> dict:
    """Update treatment details."""
    from app.models.tables import VisitTreatment
    
    treatment = await db.get(VisitTreatment, treatment_id)
    if not treatment:
        raise ValueError("Treatment not found")
    
    if duration_minutes is not None:
        treatment.duration_minutes = duration_minutes
    if notes is not None:
        treatment.notes = notes
    
    treatment.updated_at = _utc_now()
    
    await _append_event(db, "TREATMENT_UPDATED", actor_id, {
        "treatment_id": treatment_id,
        "duration_minutes": duration_minutes,
        "notes": notes,
    })
    
    await db.commit()
    return _treatment_to_dict(treatment)


async def delete_treatment(db: AsyncSession, treatment_id: str, actor_id: str) -> bool:
    """Remove a treatment from a visit."""
    from app.models.tables import VisitTreatment
    
    treatment = await db.get(VisitTreatment, treatment_id)
    if not treatment:
        return False
    
    await _append_event(db, "TREATMENT_DELETED", actor_id, {
        "treatment_id": treatment_id,
        "visit_id": treatment.visit_id,
        "modality": treatment.modality,
    })
    
    await db.delete(treatment)
    await db.commit()
    return True


async def get_visit_treatments(db: AsyncSession, visit_id: str) -> list:
    """Get all treatments for a visit with therapist names."""
    from app.models.tables import VisitTreatment
    
    result = await db.execute(
        select(VisitTreatment).where(VisitTreatment.visit_id == visit_id)
        .order_by(VisitTreatment.started_at)
    )
    treatments = result.scalars().all()
    
    enriched = []
    for t in treatments:
        treatment_dict = _treatment_to_dict(t)
        if t.therapist_id:
            therapist = await db.get(Staff, t.therapist_id)
            if therapist:
                treatment_dict["therapist_name"] = therapist.name
        enriched.append(treatment_dict)
    
    return enriched


async def get_treatment_records(db: AsyncSession,
                                date_from: Optional[str] = None,
                                date_to: Optional[str] = None,
                                patient_id: Optional[str] = None,
                                staff_id: Optional[str] = None) -> list:
    """Get all treatment records with filters for the Treatment Records page."""
    from app.models.tables import VisitTreatment
    
    # Complex query joining treatments + visits + patients + staff + rooms
    query = select(VisitTreatment).join(Visit, VisitTreatment.visit_id == Visit.visit_id)
    
    # Apply filters
    if date_from:
        query = query.where(Visit.check_in_time >= date_from)
    if date_to:
        query = query.where(Visit.check_in_time <= date_to)
    if patient_id:
        query = query.where(Visit.patient_id == patient_id)
    if staff_id:
        query = query.where(VisitTreatment.therapist_id == staff_id)
    
    result = await db.execute(query.order_by(VisitTreatment.started_at.desc()))
    treatments = result.scalars().all()
    
    # Enrich with related data
    enriched = []
    for t in treatments:
        treatment_dict = _treatment_to_dict(t)
        
        # Get visit data
        visit = await db.get(Visit, t.visit_id)
        if visit:
            treatment_dict["patient_name"] = visit.patient_name
            treatment_dict["visit_status"] = visit.status
            treatment_dict["check_in_time"] = visit.check_in_time.isoformat() if visit.check_in_time else None
            
            # Get room name
            if visit.room_id:
                room = await db.get(Room, visit.room_id)
                if room:
                    treatment_dict["room_name"] = room.name
                    treatment_dict["room_code"] = room.code
        
        # Get therapist name
        if t.therapist_id:
            therapist = await db.get(Staff, t.therapist_id)
            if therapist:
                treatment_dict["therapist_name"] = therapist.name
        
        enriched.append(treatment_dict)
    
    return enriched


def _treatment_to_dict(treatment: VisitTreatment) -> dict:
    """Convert VisitTreatment ORM object to dict."""
    return {
        "treatment_id": treatment.treatment_id,
        "visit_id": treatment.visit_id,
        "modality": treatment.modality,
        "therapist_id": treatment.therapist_id,
        "duration_minutes": treatment.duration_minutes,
        "started_at": treatment.started_at.isoformat() if treatment.started_at else None,
        "completed_at": treatment.completed_at.isoformat() if treatment.completed_at else None,
        "notes": treatment.notes,
        "created_at": treatment.created_at.isoformat(),
        "updated_at": treatment.updated_at.isoformat(),
    }
```

---

## 📝 Summary of Changes

### Backend Files to Modify:
1. ✅ `backend/app/models/tables.py` — Add `VisitTreatment` class
2. 🔲 `backend/app/services/db_service.py` — Add treatment functions
3. 🔲 `backend/app/routers/db_routes.py` — Add treatment endpoints
4. 🔲 `backend/app/services/pdf_service.py` — Update to show multiple treatments

### Frontend Files to Modify:
1. 🔲 `frontend/index.html` — Add treatments UI to:
   - Active visits section (add/edit/delete treatments)
   - Checkout modal (review treatments + generate PDF option)
   - Patient detail modal (selective PDF generation)
   - New "Treatment Records" tab with filters

### Database Migration Need:
```sql
CREATE TABLE visit_treatments (
    treatment_id TEXT PRIMARY KEY,
    visit_id TEXT NOT NULL,
    modality TEXT NOT NULL,
    therapist_id TEXT,
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

---

## 🎯 Implementation Priority

1. **P0 - FOUNDATION**: Visit treatments table + API endpoints (enables everything else)
2. **P1 - CORE UX**: Add treatments to active visits UI
3. **P1 - WORKFLOW**: Review treatments at checkout
4. **P2 - ENHANCED PDF**: PDF generation at checkout + selective generation
5. **P3 - ANALYTICS**: Treatment records page with filters

---

## 🚀 Next Steps

Should I proceed with implementing:
1. The treatment API endpoints first?
2. The UI for adding treatments to active visits?
3. Both in parallel?

Which would you like me to build first?
