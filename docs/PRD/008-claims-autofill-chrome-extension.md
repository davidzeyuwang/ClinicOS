# PRD-008: Claims Auto-Fill Chrome Extension

**Status:** Draft v1
**Date:** 2026-04-04
**Owner:** Product / Billing
**Related:** `docs/PRD/007-insurance-intake-eligibility-auto-inquiry.md`, `docs/RFC/004-claims-autofill-chrome-extension.md`

---

## 1. Background

ClinicOS is expanding from visit operations into insurance-ready billing workflows. The current product can capture patient, visit, treatment, and insurance data, and the roadmap already includes draft claims and remittance handling. What is still missing is the last-mile workflow staff perform on payer portals: manually retyping CMS-1500 data into web claim forms.

The clinic wants a Chrome extension that:

- authenticates against ClinicOS
- lets billing staff select a patient visit
- assembles a CMS-1500 claim payload from ClinicOS data
- maps that payload onto payer portal fields
- auto-fills the portal form while preserving an audit trail

This PRD defines the product requirements for that extension and the supporting backend APIs.

---

## 2. Goals

- Eliminate manual re-entry of CMS-1500 claim data into payer portals
- Standardize claim assembly from ClinicOS records before portal submission
- Support generic CMS-1500 mapping so the same extension can adapt to multiple payer portals
- Reduce billing errors caused by manual typing
- Preserve a traceable audit log of what data was assembled and filled

## 3. Non-Goals

- Direct EDI claim submission to clearinghouses
- Automated payment posting or denial adjudication
- OCR extraction from scanned CMS-1500 paper forms
- Fully autonomous claim submission without user review
- Support for UB-04 or dental claim formats in this phase

---

## 4. CMS-1500 Data Scope

The extension targets the standard CMS-1500 field set and fills only what ClinicOS can source reliably. Representative mappings:

| CMS-1500 Box | Meaning | ClinicOS Source |
|---|---|---|
| 1, 1a | Insurance type, insured ID | insurance policy + payer config |
| 2, 3, 5 | Patient name, DOB, address | patient demographic record |
| 11, 11a-c | Policy/group/employment metadata | insurance policy |
| 17, 17b | Referring provider / NPI | provider/staff + billing config |
| 21 | Diagnosis codes | visit diagnoses |
| 24A-J | DOS, place of service, CPT, modifier, diagnosis pointer, charges, units, rendering provider | visit + visit_treatments + billing config |
| 25, 26, 28, 31, 33 | tax ID, account number, total charge, signature, billing provider info | clinic billing config + visit |

Fields without a trusted source must remain blank and be highlighted for manual review.

---

## 5. Features

| ID | Title | Priority | Description |
|---|---|---|---|
| EXT-01 | Clinic Billing Configuration | P0 | Store clinic billing identity, payer IDs, NPI, taxonomy, tax ID, addresses |
| EXT-02 | Diagnosis Capture for Claims | P0 | Structured ICD-10 diagnosis codes linked to visits |
| EXT-03 | Procedure Coding for Treatments | P0 | CPT/HCPCS codes, modifiers, units, and charges on visit treatments |
| EXT-04 | CMS-1500 Assembly API | P0 | Backend endpoint that assembles a normalized claim payload |
| EXT-05 | Chrome Extension Shell | P0 | Manifest V3 extension with popup, service worker, and content script |
| EXT-06 | Extension Authentication | P0 | Secure login/session model between extension and ClinicOS |
| EXT-07 | Patient / Visit Claim Selector | P1 | Search and choose eligible visits to fill |
| EXT-08 | Portal Field Mapping Registry | P1 | Admin-managed DOM selectors and transform rules per payer portal |
| EXT-09 | Auto-Fill Execution Engine | P1 | Content script fills mapped fields with review + retry behavior |
| EXT-10 | Fill Audit Trail | P1 | Log assembled payload version, fill attempt, user, portal, and outcome |

### EXT-01: Clinic Billing Configuration

**Problem:** Claim submission needs clinic-level billing identifiers that are not part of the current operations model.

**Requirement:**
- Add a clinic-scoped billing configuration record for:
  - legal billing name
  - billing address
  - billing phone
  - tax ID / EIN
  - billing NPI
  - taxonomy code
  - default place of service
  - payer-specific submitter IDs when required

**Acceptance Criteria:**
1. Admin can create and update billing configuration
2. One active billing config exists per clinic
3. Sensitive identifiers are excluded from non-admin responses
4. CMS-1500 assembly fails with explicit missing-field validation when required billing config is incomplete

### EXT-02: Diagnosis Capture for Claims

**Problem:** Current visit records do not yet guarantee structured diagnosis data suitable for claim assembly.

**Requirement:**
- Support ICD-10 diagnosis codes per visit
- Track ordering/position for diagnosis pointers used in CMS-1500 box 21 and box 24E

**Acceptance Criteria:**
1. Each visit can store 1-12 diagnosis codes
2. Diagnosis order is preserved
3. Claim assembly returns diagnosis codes in CMS-1500 order
4. Invalid ICD-10 format is rejected by validation

### EXT-03: Procedure Coding for Treatments

**Problem:** The extension cannot fill claim service lines without procedure codes, modifiers, units, and charges.

**Requirement:**
- Extend visit treatment records to include:
  - CPT/HCPCS code
  - up to four modifiers
  - units
  - line charge
  - rendering provider

**Acceptance Criteria:**
1. Each treatment line can carry billing codes and units
2. Claim assembly generates one CMS-1500 service line per billable treatment
3. Empty procedure codes block claim assembly
4. Total claim charge is computed from line items

### EXT-04: CMS-1500 Assembly API

**Problem:** The extension needs a single canonical claim payload rather than many ad hoc API calls.

**Requirement:**
- Add `GET /prototype/billing/visits/{visit_id}/cms1500`
- Response includes:
  - normalized patient block
  - insured block
  - provider block
  - diagnosis block
  - service lines
  - validation warnings/errors

**Acceptance Criteria:**
1. Endpoint returns a stable JSON contract
2. Missing data is surfaced as warnings/errors, not silently dropped
3. Response includes source version metadata for auditability
4. Only authorized billing roles can access claim assembly

### EXT-05: Chrome Extension Shell

**Problem:** No browser-side application exists to run portal autofill.

**Requirement:**
- Build a Manifest V3 extension with:
  - popup UI
  - background service worker
  - content script
  - settings page if needed for debug/mapping inspection

**Acceptance Criteria:**
1. Extension installs in Chrome without unpacked errors
2. Popup can detect whether the current page is a mapped payer portal
3. Content script can message the background worker
4. Extension contains no hardcoded PHI or secrets

### EXT-06: Extension Authentication

**Problem:** The extension needs a secure way to fetch claim data from ClinicOS.

**Requirement:**
- Extension authenticates using ClinicOS auth, with short-lived tokens and explicit logout
- Clinic and role context must be preserved

**Acceptance Criteria:**
1. User can log in from extension popup
2. Extension session expires consistently with backend auth policy
3. Unauthorized requests are blocked and prompt re-login
4. Tokens are not exposed into page DOM or portal forms

### EXT-07: Patient / Visit Claim Selector

**Problem:** Billing staff need a focused way to find the visit being filled.

**Requirement:**
- Search recent claim-eligible visits by patient, DOS, payer, provider, or visit ID
- Show claim completeness warnings before fill

**Acceptance Criteria:**
1. Selector lists only visits eligible for claim fill
2. Search supports patient name, visit date, and payer
3. Selecting a visit previews claim warnings
4. Staff can refresh claim data before fill

### EXT-08: Portal Field Mapping Registry

**Problem:** Every payer portal uses different DOM structures and field names.

**Requirement:**
- Store per-portal mapping definitions:
  - domain match
  - page match
  - CSS/XPath selectors
  - field transforms
  - required/optional markers

**Acceptance Criteria:**
1. Admin/developer can define mappings without editing extension code for each payer
2. Mapping version is attached to each fill attempt
3. Unmapped required fields are flagged before fill starts
4. Registry supports multiple versions per portal

### EXT-09: Auto-Fill Execution Engine

**Problem:** Populating claim forms is currently manual and error-prone.

**Requirement:**
- Content script fills mapped fields with:
  - preview mode
  - fill mode
  - retry logic
  - post-fill validation

**Acceptance Criteria:**
1. Fill engine writes values only to mapped inputs
2. User can review before submission
3. Failed fields are highlighted with reasons
4. Extension never clicks final submit in v1; human review remains required

### EXT-10: Fill Audit Trail

**Problem:** The clinic needs to know what data was assembled and when an autofill attempt was made.

**Requirement:**
- Log each assembly + fill attempt with:
  - actor user
  - clinic
  - visit
  - portal domain
  - mapping version
  - outcome
  - changed/failed field counts

**Acceptance Criteria:**
1. Every fill attempt creates an audit record
2. Audit records exclude raw PHI values in event payloads
3. Staff can review prior fill attempts by visit
4. Failed fills include structured error categories

---

## 6. User Stories

1. As a billing staff user, I want to select a checked-out visit and auto-fill a CMS-1500 form so I do not have to retype patient and insurance data.
2. As a clinic admin, I want to configure billing identity and payer mappings so the extension works across the portals we use.
3. As a biller, I want to see missing diagnosis or CPT fields before fill starts so I can correct the chart first.
4. As an auditor, I want to know which user assembled and filled claim data for a visit so we can investigate billing issues later.

---

## 7. Security & HIPAA Considerations

- Extension must never persist PHI longer than necessary in browser storage
- Tokens must be stored in extension-scoped storage only, not in page context
- Audit events must use entity IDs, not raw patient demographics
- Portal mappings must not include hardcoded PHI samples
- Autofill remains user-initiated; automatic background submission is out of scope

---

## 8. Edge Cases

1. Portal DOM changed after a payer update: extension flags unmapped fields and aborts fill safely.
2. Visit missing diagnosis codes: selector blocks fill until visit data is corrected.
3. Secondary insurance claim: assembly API returns the selected insurance priority and payer-specific warnings.
4. Multi-line treatment visit exceeds payer portal visible rows: extension paginates or stops with manual instructions.
5. Session expires mid-fill: extension pauses and asks user to re-authenticate, then reloads claim data.

---

## 9. Success Metrics

| Metric | Target |
|---|---|
| Average manual claim-entry time reduction | >60% |
| Claim fill completion without manual re-entry | >75% of mapped portals |
| Fill audit coverage | 100% of extension-initiated fills |
| Claim assembly validation catch rate | >90% of missing required data surfaced before fill |

---

## 10. Release Plan

### Phase 1
- EXT-01 through EXT-06
- backend claim assembly contract
- extension shell + auth

### Phase 2
- EXT-07 through EXT-09
- first mapped payer portals
- end-to-end staff pilot

### Phase 3
- EXT-10
- admin mapping tools
- broader rollout to additional portals

---

## 11. Open Questions

1. Which payer portals are first-wave targets for production rollout?
2. Should claim fill be available to `frontdesk`, `admin`, or a new `billing` role?
3. Which CMS-1500 boxes may stay manual in v1 when source data is not yet structured?
4. Does the clinic want extension-assisted submission later, or permanently keep manual submit review?
