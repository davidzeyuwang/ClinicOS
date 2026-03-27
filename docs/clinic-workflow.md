# Clinic Current-State Workflow (As-Is)

This document maps the **existing clinic workflow** — all 18 steps, with compliance risks identified at each stage. This is the ground truth that Clinic OS must replace or improve.

> **See also:**
> - `PRD/003-clinic-os-prd-v2.md` — Canonical PRD with full module scope, tool migration strategy (§7), and phased implementation plan (§14)
> - `PRD/003-clinic-os-prd-v2.md` §3 — Expanded analysis of the same tools documented here
> - `PRD/003-clinic-os-prd-v2.md` §4 — Core problems derived from this workflow

## Flow Diagram

```mermaid
flowchart TD
    P[患者] -->|①| FO[前台 Intake]
    FO -->|②| AS[Asana 建 Eligibility Task]
    AS -->|③| BV[查保险专员]
    BV -->|④| PP[保险 Portal 查询]
    PP -->|⑤| NPL[Notability 患者长期表]
    NPL -->|⑥| SC[预约/回复]
    SC -->|⑦| PM_sys[PracticeMate 建预约]
    P -->|⑧| DSS[Daily Sign Sheet]
    DSS -->|⑨| XLS[Google Sheet 房间状态]
    DSS -->|⑩| EHR[医生记录]
    DSS -->|⑪| BO[后台抄写生成 Claim]
    BO -->|⑫| PM_sys[PracticeMate 提交 Claim]
    PM_sys -->|⑬| EOB1[Office Ally EOB]
    EOB1 -->|⑭| BO
    BO -->|⑮| PP[Portal 原始 EOB]
    PP -->|⑯| BO
    BO -->|⑰| PM_sys[修正 Posting]
    DSS -->|⑱| MG[日终统计]
```

---

## Step-by-Step Breakdown

### ① Patient Intake

**Current:** Patient fills out paper intake form.

**Data collected:**
- Full name
- Date of birth (DOB)
- Insurance information (carrier, member ID, group #)
- Signature

**Compliance:**
- ⚠️ PHI — must be encrypted at rest
- ⚠️ Must transmit over HTTPS only
- ⚠️ Cannot send via unencrypted email
- Paper forms must be stored in locked cabinet

---

### ② Front Desk Creates Eligibility Task (Asana)

**Current:** Front desk manually creates a task in Asana with patient name + insurance company.

**Compliance:**
- 🔴 **HIGH RISK:** Asana is NOT HIPAA-compliant (no BAA available)
- 🔴 Cannot store full PHI (name, DOB, insurance details)
- ⚠️ At most: patient initials + internal ID
- **Clinic OS must replace this** with an internal task system

---

### ③ Assign to Eligibility Specialist

**Current:** Manual drag-and-drop in Asana to assign task.

**Problems:**
- Fully manual — no automation
- No auto-reminders if task stalls
- No SLA tracking

**Compliance:**
- ⚠️ Should not expose full DOB on shared board

---

### ④ Login to Insurance Portal & Query

**Current:** Staff logs into insurance company portal to check:
- Eligibility status
- Visit limits (authorized visits remaining)
- Copay amount
- Deductible status

**Compliance:**
- 🔴 Login credentials must be securely managed (password manager)
- 🔴 No shared accounts — each staff needs individual credentials
- 🔴 Portal screenshots must not be stored in unencrypted locations
- ⚠️ Risk: credential leakage if passwords shared via chat/email

---

### ⑤ Record to Notability Patient Ledger

**Current:** Staff pastes portal screenshots into Notability (iPad app). Records:
- Visit count / remaining visits
- Insurance summary
- Copay/deductible notes

**Problems:**
- Non-structured data (screenshots + handwritten notes)
- No encryption
- No access control (anyone with iPad access can see all patients)
- No search capability
- Cannot generate reports

**Compliance:**
- 🔴 PHI stored on iPad locally — device must have encryption enabled
- 🔴 iCloud sync — is iCloud HIPAA-compliant? (Only with Apple BAA + Managed Apple ID)
- ⚠️ No role-based access — front desk and therapists see same data
- **Clinic OS must replace this** with structured, encrypted patient ledger

---

### ⑥ Reply to Patient / Quote

**Current:** Staff contacts patient to communicate:
- Copay amount
- Coverage explanation
- Out-of-pocket estimates

**Compliance:**
- 🔴 Cannot send PHI via unencrypted SMS
- 🔴 Cannot leave detailed diagnosis info in voicemail
- ⚠️ Email OK only if encrypted or patient has consented
- Preferred: patient portal or secure messaging

---

### ⑦ Create Appointment in PracticeMate

**Current:** Staff creates appointment in PracticeMate, links insurance.

**Compliance:**
- ✅ PracticeMate is HIPAA-compliant (BAA available)
- ✅ This step is compliant

---

### ⑧ Daily Sign Sheet — Paper Check-In

**Current:** Paper sign-in sheet tracks daily activity:
- Patient sign-in
- Service type
- Service start/end time
- Room assignment
- Payment (copay, cash, card)
- Patient signature

**Problems:**
- Paper — no encryption, no backup
- Can be photographed by anyone nearby
- Can be lost or damaged
- Manual tallying for daily reports
- No real-time visibility for staff

**Compliance:**
- 🔴 Paper PHI must be stored in locked cabinet at end of day
- 🔴 Must not be left visible in waiting area
- 🔴 Photo risk — anyone could photograph patient list
- **Clinic OS MVP must replace this** — highest priority

---

### ⑨ Google Sheet Room Status Update

**Current:** Staff updates Google Sheet with room status (which patient, which room, time).

**Problems:**
- Overwrites old data — no history
- Cannot trace who changed what
- Not real-time enough for fast clinic flow

**Compliance:**
- 🔴 **Does Google Workspace have a signed BAA?** If not, cannot store PHI
- ⚠️ Even with BAA, Google Sheets has no row-level access control
- **Clinic OS must replace this** with real-time room board

---

### ⑩ Doctor Writes EHR

**Current:** Doctor writes clinical notes, diagnosis (ICD-10), procedure codes (CPT) in EHR system.

**Compliance:**
- ✅ EHR systems are HIPAA-compliant
- ⚠️ Risk: doctor forgets to complete notes → insurance requests additional documentation → delays payment
- ⚠️ Incomplete records = audit risk

---

### ⑪ Back Office Manually Creates Claim

**Current:** Back office staff:
1. Reads paper Daily Sign Sheet
2. Looks up Notability ledger for visit count
3. Manually enters claim data into PracticeMate

**Problems:**
- High error rate (transcription from paper)
- Human judgment calls on CPT codes
- Slow — each claim is manual

**Compliance:**
- 🔴 **Billing errors can constitute fraud** (even unintentional)
- 🔴 CPT codes must be accurate — upcoding is federal offense
- 🔴 Must have audit trail for who created each claim
- **Clinic OS should automate this** — claim generation from structured events

---

### ⑫ Submit Claim

**Current:** Electronic claim submission through PracticeMate.

**Compliance:**
- ✅ Must comply with CMS billing standards
- ✅ Electronic submission is standard

---

### ⑬ Office Ally Returns EOB

**Current:** Office Ally provides simplified EOB (Explanation of Benefits).

**Problems:**
- Simplified/incomplete data
- May not match original claim exactly

**Compliance:**
- ✅ Low risk at this step

---

### ⑭ Back Office Discovers Mismatch

**Current:** Auto-post fails in PracticeMate. Back office must manually investigate.

**Problems:**
- Fully manual investigation
- No tooling to compare claim vs EOB
- Relies on experience and memory

---

### ⑮ Login to Portal for Original EOB

**Current:** Staff logs into insurance portal to view:
- Full EOB details
- Adjustment codes
- Denial reasons
- Allowed amounts

**Compliance:**
- 🔴 Portal accounts must not be shared among staff
- 🔴 Each user needs individual credentials
- ⚠️ Same credential risks as step ④

---

### ⑯ Manual Comparison

**Current:** Staff manually compares:
- Claim submitted amount vs EOB allowed amount
- Adjustment codes
- Decides whether to appeal, resubmit, or write off

**Problems:**
- Entirely experience-based — no systematic rules
- Error-prone
- Time-consuming

**Compliance:**
- 🔴 Cannot bill patient for amounts not contractually allowed
- 🔴 Cannot knowingly upcode or resubmit fraudulent claims
- **Clinic OS should automate** — dual-source EOB reconciliation

---

### ⑰ Correct Posting

**Current:** Modify payment posting in PracticeMate. May resubmit claim.

**Compliance:**
- 🔴 **All modifications must have audit trail**
- 🔴 **Original records must never be deleted** — only amended
- 🔴 Must document reason for correction

---

### ⑱ End-of-Day Summary

**Current:** Manual calculation of:
- Therapist hours worked
- Total patients seen
- Total revenue collected
- Room utilization

**Problems:**
- Manual tallying from paper sheet
- Not auditable — no trail of how numbers were derived
- Errors compound

**Compliance:**
- 🔴 Financial records must be retained 7+ years
- ⚠️ Must be reproducible for audits

---

## Critical Compliance Risk Summary

| Step | Tool | Risk Level | Issue |
|------|------|------------|-------|
| ② ③ | Asana | 🔴 HIGH | Not HIPAA-compliant, no BAA, PHI exposure |
| ⑤ | Notability | 🔴 HIGH | Unstructured PHI, no encryption, no access control |
| ⑨ | Google Sheets | 🔴 HIGH | BAA status unknown, overwrites history |
| ⑧ | Paper Sign Sheet | 🔴 HIGH | PHI exposure, no encryption, loss risk |
| ④ ⑮ | Insurance Portals | 🟡 MEDIUM | Shared credentials risk |
| ⑪ | Manual Claim Entry | 🟡 MEDIUM | Billing accuracy / fraud risk |
| ⑯ ⑰ | Manual Reconciliation | 🟡 MEDIUM | No audit trail for corrections |
| ⑥ | Patient Communication | 🟡 MEDIUM | Unencrypted channels for PHI |
| ⑦ ⑩ ⑫ | PracticeMate / EHR | ✅ LOW | HIPAA-compliant systems |

---

## Clinic OS Module Mapping (aligned with PRD v2.0 §14)

Each compliance risk maps to a Clinic OS module and implementation phase:

| Clinic OS Module | Replaces Steps | PRD v2.0 § | Phase |
|---|---|---|---|
| **Event Log System** | Foundation for all modules | §9 | Phase 1 |
| **Front Desk Operations Board** (was: Electronic Daily Sign Sheet) | ⑧ ⑨ ⑱ | §11.3 | Phase 1 |
| **Patient Master File** | Scattered records | §11.1 | Phase 1 |
| **Appointment Management** | PracticeMate partial | §11.2 | Phase 1 |
| **Visit Management** | Manual tracking | §11.5 | Phase 1 |
| **Clinical Note (basic)** | EHR notes / Notability | §11.6 | Phase 1 |
| **Document / Signature Archive** | Notability 手工归档 | §11.4 | Phase 1 |
| **Task Management (basic)** | Asana (②③) | §11.9 | Phase 1 |
| **Insurance / Eligibility** | ② ③ ④ ⑤ | §11.7 | Phase 2 |
| **Claim / Billing State Machine** | ⑪ ⑫ | §11.8 | Phase 2 |
| **Dual-Source EOB Reconciliation** | ⑬ ⑭ ⑮ ⑯ ⑰ | §11.8 | Phase 2 |
| **AI Input / Extraction** | Manual transcription | §11.6 | Phase 3 |
| **AI Agent Back-Office** | Manual case processing | §11.9 | Phase 4 |
| **Compliance Audit Log** | All steps | §11.11 | Phase 1–5 |
| **Secure Messaging** | ⑥ | — | Phase 5+ |
| **Intake Digitization** | ① | — | Phase 5+ |

---

## Architecture Mandate

Before any feature ships, the following must be in place:

1. **All data encrypted** (at rest + in transit)
2. **Role-based access control** (RBAC) — least privilege
3. **Immutable audit trail** — every change tracked, nothing deletable
4. **Automatic event logging** — not optional, not "add later"
5. **BAA signed** with every third-party SaaS that touches PHI
6. **No PHI in non-compliant tools** (Asana, Notion, Slack, etc. unless BAA)
7. **Financial records retained 7+ years**
8. **Credential management** — no shared accounts, password manager required

# Current Software Landscape & Claim Infrastructure

## 1. Overview

The clinic currently operates on a fragmented stack of multiple tools and systems that together form an unofficial “operating system” for daily operations, insurance workflows, and revenue cycle management (RCM).

These systems are loosely integrated (mostly manual), leading to inefficiencies, data inconsistency, and compliance risks.

---

## 2. System Categorization

The current tools can be grouped into five layers:

1. Core Medical & Billing Systems (RCM Core)
2. Insurance Workflow Management
3. Patient Long-Term Records
4. Daily Operations & Scheduling
5. External Insurance Data Sources

---

## 3. Core Medical & Claim Systems (RCM Core)

### 3.1 Office Ally (Clearinghouse)

**Role:**
- Primary claim submission system
- Payment processing
- EOB (Explanation of Benefits) delivery

**Responsibilities:**
- Submit claims to insurance providers
- Receive payment data
- Provide EOB summaries
- Support limited auto-posting

**Key Insight:**
This is the **financial backbone** of the clinic. All revenue flows through this system.

---

### 3.2 PracticeMate (Office Ally PMS)

**Role:**
- Practice management system (PMS)
- Appointment scheduling
- Billing interface

**Used for:**
- Creating appointments
- Managing patients
- Entering claim data
- Viewing claim status

---

### 3.3 EHR (Office Ally EHR)

**Role:**
- Doctor notes
- Clinical documentation
- CPT / diagnosis input

**Characteristics:**
- Used exclusively by doctors
- Required for compliant billing
- Not integrated with operational tools

---

### 3.4 Claim Flow (Current)

```

Appointment (PracticeMate)
→ Doctor Notes (EHR)
→ Claim Creation (PracticeMate)
→ Submission (Office Ally)
→ Insurance Processing
→ EOB Returned (Office Ally)
→ Manual Reconciliation

```

---

## 4. External Insurance Systems

### 4.1 Insurance Provider Portals

Examples:
- Aetna
- UnitedHealthcare
- Availity

**Used for:**
- Eligibility verification
- Claim status tracking
- Detailed EOB retrieval
- Denial reason analysis

---

### 4.2 Critical Observation

There are **two sources of truth for claims:**

| Source | Description |
|------|------------|
| Office Ally | Simplified EOB |
| Insurance Portal | Full, detailed EOB |

---

### 4.3 Current Reconciliation Process

```

Office Ally EOB
↓
Mismatch detected
↓
Manual login to portal
↓
Compare data manually
↓
Fix posting or resubmit claim

```

This is fully manual and highly error-prone.

---

## 5. Insurance Workflow Management

### 5.1 Asana (Workflow Engine)

**Role:**
Insurance verification pipeline management

---

### 5.2 Board Structure

```

TO DO → DOING → REPLY → APPOINTMENT

```

---

### 5.3 Task Structure

Each task represents:
- One patient
- One insurance verification process

Contains:
- Patient info
- Insurance details
- Notes
- Status

---

### 5.4 Observed Issues

- Not HIPAA-compliant
- Stores PHI without proper controls
- No audit logs
- No role-based access
- No integration with billing systems

---

## 6. Patient Long-Term Records

### 6.1 Notability

**Role:**
Patient-level long-term tracking (unofficial database)

---

### 6.2 Data Stored

- Insurance usage (visit counts)
- Remaining benefits
- Preferences
- Notes across staff
- Historical summaries

---

### 6.3 Collaboration Model

- Shared across front desk, insurance staff, and backend
- Requires shared account for synchronization
- Uses different pen colors to represent roles

---

### 6.4 Critical Issues

- No user identity tracking
- No audit logs
- No access control
- No structured data
- Cannot scale

**Key Insight:**
Notability is functioning as a **collaborative database without any database features.**

---

## 7. Daily Operations Systems

---

### 7.1 Daily Sign-in Sheet (Paper)

**Role:**
Primary daily operational record

---

### 7.1.1 Data Captured

- Patient name
- Service performed
- Staff
- Time
- Payment

---

### 7.1.2 Issues

- Paper-based
- Single-writer limitation
- Requires manual transcription
- No real-time visibility
- No audit trail

---

### 7.2 Google Spreadsheet (Room Management)

**Role:**
Real-time room allocation board

---

### 7.2.1 Data Captured

- Room usage
- Patient assignment
- Service type
- Timestamp updates

---

### 7.2.2 Issues

- Overwrites historical data
- No time-series tracking
- No audit logs
- Weak permission control

---

## 8. Full System Relationship

```

Asana
↓
(Insurance Workflow)

Notability
↓
(Patient Long-term Data)

PracticeMate
↓
(Appointments & Billing Entry)

EHR
↓
(Doctor Notes)

Office Ally
↓
(Claim Submission & EOB)

Insurance Portals
↓
(True Claim Data)

Google Sheet
↓
(Room Tracking)

Paper Sign-in
↓
(Daily Operations)

```

---

## 9. Core Problems Summary

---

### 9.1 System Fragmentation

Patient data is distributed across:
- Asana
- Notability
- Paper sheets
- Google Sheets
- PracticeMate
- EHR

---

### 9.2 Redundant Data Entry

Same data is manually copied across multiple systems.

---

### 9.3 Lack of System Integration

No automated data flow between:
- Insurance → Appointment
- Appointment → Check-in
- Check-in → Billing
- Billing → Reconciliation

---

### 9.4 Collaboration Failure

- No multi-user support
- No identity tracking
- No audit logs

---

### 9.5 Compliance Risks

| System | Risk |
|------|------|
| Asana | PHI exposure |
| Notability | Shared account |
| Google Sheets | Weak access control |
| Paper | Physical exposure |

---

### 9.6 Revenue Cycle Inefficiency

- Manual claim correction
- Manual EOB comparison
- No automated denial analysis

---

## 10. Strategic Insight

The clinic is currently operating on:

```

A manually stitched system composed of:

* Workflow tool (Asana)
* Note-taking app (Notability)
* Spreadsheet (Google Sheets)
* Paper records
* Billing system (Office Ally)
* External portals

```

This is effectively an **unofficial operating system** without structure, auditability, or automation.

---

## 11. Opportunity Areas

---

### 11.1 Claim & EOB Automation (Highest Value)

- Dual-source reconciliation
- Denial reason automation
- Auto-posting correction

---

### 11.2 Patient Ledger System

- Replace Notability
- Structured data
- Multi-user collaboration
- Audit logs

---

### 11.3 Insurance Workflow Engine

- Replace Asana
- Automated eligibility verification
- Integrated workflow tracking

---

## 12. Conclusion

The current system is not a single platform but a collection of disconnected tools.

The opportunity is to build:

**A unified Clinic Operating System (Clinic OS)**

that integrates:
- Workflow
- Patient records
- Billing
- Insurance
- Operations

into a single, auditable, and automated platform.
