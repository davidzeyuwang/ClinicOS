# Business Owner Questions — Unresolved Domain Assumptions

**Date:** 2026-03-29
**Purpose:** Capture business meanings that are currently ambiguous, guessed, or inconsistently implemented in ClinicOS so they can be confirmed by business owners before further product changes.

---

## Summary

The most important unresolved issue is that the paper sign sheet appears to have separate `W` and `D` columns, but the current system stores only one boolean field: `wd_verified`.

There are also several other form-derived abbreviations, status vocabularies, and workflow meanings that were implemented without a confirmed glossary.

---

## Priority 0 Questions

### 1. What do `W`, `D`, and `CC` mean on the personal sign sheet?

**Why this matters:**
- The paper form shows separate `W` and `D` columns.
- The current system merged them into one field: `wd_verified`.
- The PDF renders both `W` and `D` columns, but only `W` is ever populated.

**Questions for BO:**
- What does `W` stand for?
- What does `D` stand for?
- Is `CC` definitely `Copay Collected`?
- Are `W` and `D` separate fields that must be stored independently?
- Should `W` and `D` be checkmarks, initials, dates, free text, or something else?
- At what point in the workflow are `W` and `D` filled in: insurance verification, check-in, service start, or checkout?
- If only one of `W` or `D` is completed, should checkout still be allowed?

**Current references:**
- `Files/个人签字表.png`
- `backend/app/models/tables.py`
- `backend/app/services/pdf_service.py`
- `frontend/index.html`
- `docs/PRD/004-form-field-gap-analysis.md`

### 2. What is the intended relationship between `CC`, `payment_amount`, `payment_status`, and `payment_method`?

**Why this matters:**
- The UI has both `Copay Collected (CC)` and `Additional Amount`.
- Daily summary currently adds `copay_collected + payment_amount`.
- It is not clear whether `payment_amount` includes copay or is always separate from copay.

**Questions for BO:**
- Is `CC` always the actual copay collected at the front desk?
- What is `payment_amount` supposed to represent?
- Is `payment_amount` additional money beyond copay, or total money collected?
- Can a visit have both `copay_collected` and `payment_amount` at the same time?
- When `payment_status = paid`, does that mean paid in full including copay?
- When `payment_status = insurance_only`, should `CC` always be zero or blank?
- Can a payment be split across multiple methods for one visit?
- Should negative amounts ever be allowed?
- Should zero-dollar copay still be explicitly recorded?

**Current references:**
- `frontend/index.html`
- `backend/app/models/tables.py`
- `backend/app/services/db_service.py`
- `backend/tests/test_prd004_features.py`

### 3. What counts as “patient signed”?

**Why this matters:**
- The current system stores a boolean `patient_signed`.
- The paper form has an actual signature field.
- PRD documents also describe future digital signature capture.

**Questions for BO:**
- Does “patient signed” mean a real handwritten signature is required?
- Is a front-desk checkbox enough for now, or is that only a temporary workaround?
- If a real signature is required, should it be captured on iPad, uploaded, or only printed on paper?
- Should the system store the signature image per visit?
- Is the current boolean acceptable for checkout, or should it be replaced later with structured signature data?

**Current references:**
- `Files/个人签字表.png`
- `frontend/index.html`
- `backend/app/models/tables.py`
- `docs/PRD/001-daily-sign-sheet.md`

---

## Priority 1 Questions

### 4. What is the official glossary for treatment-record abbreviations?

**Why this matters:**
- The treatment UI uses `A`, `PT`, `CP`, `TN`, and `生诊医生`.
- The form-gap analysis also mentions `OUT`, `WW`, `CAST/GAS`, and `Sig`.
- The backend maps modalities into columns using string heuristics.

**Questions for BO:**
- What does each treatment-record column mean exactly?
- What do `A`, `PT`, `CP`, and `TN` stand for?
- What do `OUT`, `WW`, `CAST/GAS`, and `Sig` mean on the paper treatment record?
- Which service types should map into each column?
- Are `Eval`, `Re-eval`, `OT`, `Speech`, `E-stim`, `Heat`, and `Cold` separate columns, or should they roll up into existing columns?
- Should “other modalities” appear in their own dedicated column instead of free text notes?
- Is `生诊医生` the supervising doctor, attending physician, ordering provider, or something else?

**Current references:**
- `Files/个人诊疗记录表.png`
- `frontend/index.html`
- `backend/app/services/db_service.py`
- `docs/PRD/004-form-field-gap-analysis.md`

### 5. What are the canonical service types and modality names?

**Why this matters:**
- Service type lists are hard-coded in multiple places.
- Modality-to-column mapping currently uses inferred string matching.

**Questions for BO:**
- What is the master list of service types?
- What is the master list of treatment modalities?
- Are “service type” and “treatment modality” the same concept or different concepts?
- Which terms are synonyms and should be normalized?
- Which labels should appear in the UI versus only in reports?

**Current references:**
- `frontend/index.html`
- `backend/app/services/db_service.py`
- `docs/PRD-004-IMPLEMENTATION-STATUS.md`
- `tasks/features.json`

### 6. What is the correct meaning of room-board status codes from the original sheet?

**Why this matters:**
- The original room sheet reportedly uses codes like `BA`, `RA`, `MA`, `NA`.
- ClinicOS currently uses only `available`, `occupied`, `cleaning`, and `OOS`.

**Questions for BO:**
- What does each original room status code mean?
- Do those original codes need to be preserved in ClinicOS?
- Are the current 4 room states enough, or do we need more specific statuses?
- If we keep user-friendly labels, do we also need the original abbreviations in reports or printouts?

**Current references:**
- `Files/房间排班表.png`
- `docs/PRD/004-form-field-gap-analysis.md`
- `backend/app/models/tables.py`

### 7. What is the official eligibility workflow status vocabulary?

**Why this matters:**
- Existing code uses insurance `eligibility_status` values: `unknown | verified | denied | expired`.
- PRD backlog proposes eligibility case statuses: `pending | in_progress | verified | failed`.
- These are related but not aligned.

**Questions for BO:**
- What statuses should insurance eligibility use?
- Are policy eligibility status and eligibility task/case status the same thing or different things?
- Is `unknown` a valid business status or just a system default?
- Should `denied` and `failed` be treated differently?
- Do we need `pending`, `in_progress`, `verified`, `denied`, `expired`, `failed`, or some other set?

**Current references:**
- `backend/app/models/tables.py`
- `backend/app/schemas/prototype.py`
- `docs/PRD-004-IMPLEMENTATION-STATUS.md`
- `docs/PRD/004-form-field-gap-analysis.md`

### 8. Should network status live on the patient, the insurance policy, or both?

**Why this matters:**
- One doc proposes `patients.network_status`.
- Another proposed schema includes `insurance_policies.is_in_network`.
- In-network often depends on the specific policy, not only the patient.

**Questions for BO:**
- Is “in-network / out-of-network” a patient-level attribute or policy-level attribute?
- If a patient has primary and secondary insurance, can one be in-network and the other out-of-network?
- Should network status be captured per visit, per patient, per policy, or multiple levels?

**Current references:**
- `docs/PRD/004-form-field-gap-analysis.md`
- `docs/PRD-004-IMPLEMENTATION-STATUS.md`

### 9. How should primary vs secondary insurance be modeled operationally?

**Why this matters:**
- The forms clearly support primary and secondary insurance.
- The current schema has a simple `priority` field, but workflow rules are not defined.

**Questions for BO:**
- Can a patient have more than two policies?
- Should exactly one policy always be primary?
- Does priority affect copay collection rules or just reporting?
- When coverage changes, do we keep historical policies or overwrite the current one?

**Current references:**
- `Files/个人签字表表头.png`
- `backend/app/models/tables.py`
- `docs/PRD/004-form-field-gap-analysis.md`

---

## Priority 2 Questions

### 10. What role types should staff have, and who can be selected as supervising doctor?

**Why this matters:**
- Staff role is currently free-form text.
- Tests add a supervising physician using the `therapist` role.
- The system has no formal distinction between therapist, doctor, and supervising provider.

**Questions for BO:**
- What are the allowed staff roles?
- Which roles can provide treatment?
- Which roles can appear as `生诊医生` / supervising doctor?
- Can the same person be both treating therapist and supervising doctor on the same visit?

**Current references:**
- `frontend/index.html`
- `backend/app/models/tables.py`
- `frontend/tests/e2e/ops-board.spec.ts`

### 11. What should happen to unresolved or future paper-form fields that are not yet modeled?

**Why this matters:**
- Some paper-form columns are visible but not yet fully understood.
- The repo currently mixes direct modeling with inferred simplifications.

**Questions for BO:**
- Do you want an official field glossary for every paper form abbreviation?
- For unknown fields, should we keep them out of ClinicOS until defined, or store them as generic notes/attachments first?
- Is there a designated staff member who can confirm the meaning of legacy paper-form abbreviations?

**Current references:**
- `Files/个人签字表.png`
- `Files/个人诊疗记录表.png`
- `Files/房间排班表.png`

---

## Implementation Risks To Pause Until Clarified

- Do not expand `wd_verified` into more features until `W` and `D` are confirmed.
- Do not treat the current PDF `W` and `D` columns as correct business behavior.
- Do not finalize service-type filtering rules until the canonical service/modality glossary is approved.
- Do not finalize eligibility workflow statuses until one shared vocabulary is approved.
- Do not finalize network-status schema until BO confirms whether it belongs to patient, policy, or visit.
