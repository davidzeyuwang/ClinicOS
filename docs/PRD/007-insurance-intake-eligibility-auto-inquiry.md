# PRD-007: Insurance Intake & Eligibility Auto-Inquiry

**Status:** Draft v1
**Date:** 2026-04-04
**Owner:** Product
**Related:** PRD-003 §11.7, PRD-004 (Gap Analysis), RFC-003

---

## 1. Background

ClinicOS currently stores basic insurance policy info (carrier_name, member_id, group_number, plan_type, copay_amount, deductible, priority, eligibility_status) but lacks the full field set required by the clinic's paper sign-in sheet (PRD-004 GAP-INS-01 through GAP-INS-12). Eligibility verification is managed manually via Asana task lists — staff must log into each payer portal, look up patient details, and transcribe results back into paper forms.

This PRD defines requirements for:
1. A comprehensive insurance intake form closing all PRD-004 gaps
2. An automated eligibility inquiry engine that scrapes payer portals via headless browser
3. Immutable inquiry snapshots that preserve every verification result for audit

---

## 2. Goals

- **G1:** Close 100% of insurance field gaps identified in PRD-004 (GAP-INS-01 through GAP-INS-12)
- **G2:** Eliminate manual payer portal lookups — automate eligibility verification
- **G3:** Create an auditable, immutable record of every eligibility inquiry result
- **G4:** Support periodic re-verification (e.g., weekly, pre-visit) without staff intervention
- **G5:** Replace the Asana-based eligibility workflow entirely

---

## 3. Non-Goals

- EDI/X12 270/271 clearinghouse integration (future phase)
- Real-time eligibility check at point of care (future phase)
- Automated prior authorization submission
- Patient-facing insurance card upload via mobile app
- Claims submission or billing (see PRD-008)

---

## 4. Features

| ID | Title | Priority | Description |
|----|-------|----------|-------------|
| INS-01 | Enhanced Insurance Intake Form | P0 | Full insurance form with all PRD-004 fields |
| INS-02 | Dual Insurance Support | P0 | Primary + Secondary policies per patient |
| INS-03 | Payer Configuration Registry | P0 | Admin-managed list of supported payers with portal URLs and credential storage |
| INS-04 | Manual Eligibility Inquiry | P0 | Staff-triggered single-patient eligibility check |
| INS-05 | Immutable Inquiry Snapshots | P0 | Append-only record of each verification result |
| INS-06 | Automated Periodic Re-Inquiry | P1 | Scheduler re-verifies eligibility on configurable intervals |
| INS-07 | Pre-Visit Inquiry Trigger | P1 | Auto-verify eligibility 48h before scheduled visit |
| INS-08 | Payer Adapter Library | P1 | Pluggable scrapers for UHC, Aetna, BCBS, Cigna |
| INS-09 | Inquiry Dashboard | P1 | Staff view of pending/completed/failed inquiries |
| INS-10 | Eligibility Alerts | P1 | Notify staff when eligibility changes (denied/expired) |
| INS-11 | Inquiry History per Patient | P1 | Timeline of all eligibility checks for a patient |
| INS-12 | Pharmacy Benefit Fields | P2 | RxBIN, RxPCN, RxGRP fields on insurance policy |

### INS-01: Enhanced Insurance Intake Form

**Problem:** Current insurance_policies table has 15 fields. The paper sign-in sheet requires 30+ fields including deductible breakdowns, OOP maximums, coverage percentages, referral/preauth flags, and verification metadata.

**Requirement:** Expand the insurance policy data model and UI form to capture all fields from PRD-004 §2.1:

- Plan code, effective dates (start/end)
- Referral required (Y/N), Pre-authorization required (Y/N)
- Deductible: individual amount, individual met, family amount, family met
- Out-of-pocket max: individual amount, individual met
- Coverage percentage
- Copay per visit, coinsurance
- In-network flag
- Checked by (staff who verified)
- Visits authorized, visits used

**Acceptance Criteria:**
1. Insurance policy create/edit form includes all fields listed above
2. All fields persist to database and appear on patient detail view
3. Fields render in the same layout as the paper sign-in sheet header
4. Existing policies with partial data continue to work (new fields nullable)

### INS-02: Dual Insurance Support

**Problem:** Many patients carry primary and secondary insurance. The current model supports a `priority` field but the UI doesn't present side-by-side comparison.

**Requirement:** Patient insurance tab shows Primary and Secondary policies in two columns, mirroring the paper form layout.

**Acceptance Criteria:**
1. Patient detail page shows Primary and Secondary insurance side-by-side
2. Each policy independently editable
3. Priority field enforced: exactly 0-1 primary and 0-1 secondary per patient
4. Eligibility inquiries run for both policies

### INS-03: Payer Configuration Registry

**Problem:** Each insurance carrier has a different portal URL, login flow, and page structure. The system needs a registry of supported payers with encrypted credentials.

**Requirement:** Admin can manage payer configurations including portal URL, adapter type, and credentials (encrypted at rest with Fernet).

**Acceptance Criteria:**
1. Admin can CRUD payer configurations
2. Credentials stored encrypted (Fernet) — never returned in API responses
3. Each payer config specifies: payer_name, portal_url, adapter_type, login fields
4. Payer configs scoped to clinic_id
5. Adapter_type maps to a scraping adapter (e.g., "uhc", "aetna", "bcbs", "cigna", "generic")

### INS-04: Manual Eligibility Inquiry

**Problem:** Staff currently log into payer portals manually to verify eligibility.

**Requirement:** Staff can trigger a one-click eligibility check for a patient's insurance policy. The system uses a headless browser (Playwright) to scrape the payer portal and extract eligibility data.

**Acceptance Criteria:**
1. "Check Eligibility" button on patient insurance card
2. System creates an inquiry record with status: pending → running → completed/failed
3. On completion, extracted data auto-populates insurance policy fields
4. An immutable snapshot of the raw inquiry result is saved
5. Policy eligibility_status updated (verified/denied/expired)
6. eligibility_verified_at timestamp updated

### INS-05: Immutable Inquiry Snapshots

**Problem:** Eligibility status changes over time. The clinic needs a permanent record of what each payer portal returned at each point in time for audit and dispute resolution.

**Requirement:** Every eligibility inquiry produces an append-only snapshot containing the raw and parsed response data.

**Acceptance Criteria:**
1. Snapshots are INSERT-only — no UPDATE or DELETE permitted
2. Each snapshot links to inquiry_id, policy_id, patient_id
3. Snapshot stores: raw_html (or raw_data), parsed fields, payer response timestamp
4. Snapshots viewable in patient eligibility history
5. Event ELIGIBILITY_SNAPSHOT_CREATED emitted (entity IDs only, no PHI)

### INS-06: Automated Periodic Re-Inquiry

**Problem:** Insurance eligibility can change at any time. Staff shouldn't need to manually re-check every patient.

**Requirement:** A configurable scheduler re-runs eligibility checks at defined intervals (e.g., weekly, bi-weekly).

**Acceptance Criteria:**
1. Admin configures re-inquiry interval per clinic (default: 7 days)
2. Scheduler queues re-inquiries for all active policies past their interval
3. Re-inquiries run during configurable off-hours window
4. Failed re-inquiries are retried with exponential backoff (max 3 retries)
5. Staff notified of eligibility changes detected during re-inquiry

### INS-07: Pre-Visit Inquiry Trigger

**Problem:** Patient arrives for a visit and eligibility has lapsed — causes billing issues.

**Requirement:** System automatically triggers eligibility verification 48 hours before any scheduled visit if last verification is older than configured threshold.

**Acceptance Criteria:**
1. Pre-visit check triggers 48h before visit (configurable)
2. Only runs if last verification older than threshold (default: 7 days)
3. Alert generated if eligibility denied or expired
4. Pre-visit check results visible on visit detail before check-in

### INS-08: Payer Adapter Library

**Problem:** Each payer portal has unique login flow, navigation, and data layout.

**Requirement:** Pluggable adapter pattern where each payer has a dedicated scraping adapter that knows how to navigate that portal.

**Acceptance Criteria:**
1. Base adapter interface: login(), search_member(), extract_eligibility()
2. Adapters for: UHC, Aetna, BCBS, Cigna (P1), Generic fallback (P0)
3. Each adapter handles: portal login, member search, eligibility data extraction
4. Adapters return standardized EligibilityResult schema
5. New adapters addable without modifying core engine code
6. Adapter errors are caught and logged without exposing PHI

### INS-09: Inquiry Dashboard

**Problem:** No visibility into which patients need verification, which are pending, which failed.

**Requirement:** Dashboard showing all eligibility inquiries with filters by status, payer, date.

**Acceptance Criteria:**
1. List view of all inquiries with columns: patient (ID), payer, status, last checked, next scheduled
2. Filter by: status (pending/running/completed/failed), payer, date range
3. Bulk action: re-run failed inquiries
4. Click-through to patient eligibility history

### INS-10: Eligibility Alerts

**Problem:** Staff may not notice when a patient's eligibility changes between visits.

**Requirement:** System generates alerts when eligibility status changes to denied or expired during automated re-inquiry.

**Acceptance Criteria:**
1. Alert created when eligibility_status changes from verified to denied/expired
2. Alerts visible on inquiry dashboard and patient detail
3. Alert includes: patient_id, policy_id, old_status, new_status, checked_at
4. Alerts dismissible by staff after acknowledgment

### INS-11: Inquiry History per Patient

**Problem:** No timeline of past eligibility checks for a patient.

**Requirement:** Patient detail page shows chronological list of all eligibility inquiries and snapshots.

**Acceptance Criteria:**
1. Timeline view on patient insurance tab
2. Each entry shows: date, payer, status, key fields (coverage%, deductible, copay)
3. Click to expand shows full snapshot data
4. Entries are read-only (immutable)

### INS-12: Pharmacy Benefit Fields

**Problem:** Paper form includes RxBIN, RxPCN, RxGRP for pharmacy benefits. Currently missing from data model.

**Requirement:** Add pharmacy benefit fields to insurance policy.

**Acceptance Criteria:**
1. RxBIN, RxPCN, RxGRP fields on insurance policy form
2. Fields captured during eligibility inquiry if available from payer portal
3. Fields visible on patient insurance card

---

## 5. User Stories

1. **As a front desk staff**, I want to enter complete insurance information including deductibles, OOP max, and coverage percentage so that I can stop maintaining paper sign-in sheets.
2. **As a front desk staff**, I want to click one button to verify a patient's eligibility instead of logging into each payer portal manually.
3. **As a clinic admin**, I want eligibility to be re-checked automatically every week so that we catch coverage changes before patients arrive.
4. **As a billing coordinator**, I want to see the full history of eligibility checks for each patient so that I can resolve claim disputes with payers.
5. **As a clinic admin**, I want to configure payer portal credentials securely so that automated inquiries can run without staff intervention.
6. **As a front desk staff**, I want to be alerted when a patient's eligibility status changes to denied so that I can inform the patient before their next visit.

---

## 6. Security & HIPAA Considerations

- **Credential encryption:** Payer portal credentials encrypted with Fernet at rest. Never returned in API responses. Decrypted only in-memory during inquiry execution.
- **PHI in scraping:** Raw HTML/data from payer portals may contain PHI. Stored encrypted in snapshots. Never logged in plaintext.
- **Event payloads:** All events use entity IDs only (patient_id, policy_id, inquiry_id). No names, DOBs, member IDs in event_log.
- **Access control:** Payer config management restricted to admin role. Inquiry triggers available to frontdesk and above.
- **Headless browser isolation:** Scraping engine runs in isolated process/container. Browser profiles cleared after each inquiry.

---

## 7. Edge Cases

1. **Payer portal down:** Inquiry fails gracefully with status=failed, retried later
2. **Invalid credentials:** Inquiry fails with status=auth_failed, admin notified to update credentials
3. **Portal layout changes:** Adapter extraction fails, returns partial data with warning flag
4. **Patient has no insurance:** Intake form allows "self-pay" designation, no inquiry triggered
5. **Dual insurance with same carrier:** Both policies verified independently by member_id
6. **Policy effective date in future:** Stored but eligibility_status set to "not_yet_effective"
7. **Re-inquiry during active visit:** Use last-known eligibility, queue re-check for next day

---

## 8. Success Metrics

| Metric | Target |
|--------|--------|
| Insurance field completion rate | >95% of active patients have all P0 fields filled |
| Manual portal lookups eliminated | >80% reduction in staff portal login time |
| Eligibility verification freshness | >90% of active patients verified within 7 days |
| Inquiry success rate | >90% of automated inquiries complete successfully |
| Mean time to detect eligibility change | <48 hours |

---

## 9. Out of Scope

- EDI 270/271 electronic eligibility transactions
- Real-time point-of-care eligibility (sub-second response)
- Patient self-service insurance card photo upload
- Prior authorization automation
- Claims submission (covered in PRD-008)
- Integration with practice management systems

---

## 10. Release Plan

### Phase 1 — Data Model + Manual Intake
- INS-01: Enhanced intake form with all PRD-004 fields
- INS-02: Dual insurance UI
- INS-12: Pharmacy benefit fields

### Phase 2 — Automated Inquiry Engine
- INS-03: Payer configuration registry
- INS-04: Manual eligibility inquiry
- INS-05: Immutable inquiry snapshots
- INS-08: Payer adapter library (generic + 1 payer)

### Phase 3 — Automation + Monitoring
- INS-06: Automated periodic re-inquiry
- INS-07: Pre-visit inquiry trigger
- INS-09: Inquiry dashboard
- INS-10: Eligibility alerts
- INS-11: Inquiry history per patient
- INS-08: Additional payer adapters (UHC, Aetna, BCBS, Cigna)

---

## 11. Open Questions

1. **Rate limiting:** Do payer portals rate-limit automated queries? Need to research per-payer limits and implement throttling.
2. **Terms of service:** Some payer portals may prohibit automated scraping. Legal review needed per payer.
3. **Credential sharing:** Can one set of portal credentials serve all patients, or does each clinic need its own provider portal account?
4. **Snapshot retention:** How long should raw inquiry snapshots be retained? Recommend 7 years per HIPAA retention requirements.
5. **W/D fields:** The paper form has W and D columns whose business meaning is unconfirmed (PRD-004 §2.2). Needs business stakeholder clarification before implementation.
