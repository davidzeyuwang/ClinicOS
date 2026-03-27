# Clinic OS — Product Roadmap

**Last Updated:** 2026-03-27

> **Canonical PRD:** `PRD/003-clinic-os-prd-v2.md` (v2.0) — all module scope, phasing, and tool migration strategy are defined there.
> **Form Field Gap Analysis:** `PRD/004-form-field-gap-analysis.md` — field-by-field diff between actual paper forms and current ClinicOS implementation (updated 2026-03-26).

## Vision

Clinic OS is a **Vertical AI Operating System** for clinical practices — replacing fragmented paper + SaaS workflows (Daily Sign In Sheet, Google Sheets, Notability, Asana) with an event-sourced, HIPAA-compliant, unified clinic operating system.

Long-term this becomes:
- SaaS for clinic operations (unified patient master + visit + note + billing)
- Automated RCM (Revenue Cycle Management)
- AI-powered billing & reconciliation
- AI agent–driven back-office automation (copilot → operator)
- Compliance-as-a-service
- Multi-clinic / multi-location platform

## Phased Roadmap (aligned with PRD v2.0 §14)

### Phase 1 — 运营核心打通 (Operations Core)

| Module | Replaces | PRD §  | Status |
|---|---|---|---|
| Event Log System + Compliance Audit Log | Foundation for everything | §9, §11.11 | 🔲 Not started |
| Auth + RBAC | N/A (new capability) | §11.11 | 🔲 Not started |
| Patient Master File | Scattered records across paper/Notability | §11.1 | ⚠️ M1 core in progress |
| Appointment Management | PracticeMate only, no unified view | §11.2 | 🔲 Deferred after M1 core |
| Front Desk Operations Board (签到 + 房间/资源板) | Paper sign sheet (⑧) + Google Sheets (⑨) + Manual tally (⑱) | §11.3 | ⚠️ M1 core in progress |
| Visit Management | Manual tracking | §11.5 | ⚠️ M1 core in progress |
| **Insurance Policy Fields (P0)** | 个人签字表表头 — Member ID, Deductible, OOP, Copay, Visits | §11.7 + PRD-004 §2.1 | 🔲 Not started |
| **Copay Collection + WD Verified per Visit (P0)** | 每次就诊实收共付额（CC字段）+免赔额核实（WD） | PRD-004 §2.2 | 🔲 Not started |
| Clinical Note (basic status) | EHR notes, Notability | §11.6 | 🔲 Deferred after M1 core |
| **Multi-modality Treatment Record (P1)** | 个人诊疗记录表 — 每次就诊多个治疗项目 | PRD-004 §2.4 | 🔲 Not started |
| Document / Signature Archive (basic) | Notability 手工归档 | §11.4 | ⚠️ M1 PDF/sign flow in progress |
| Task Management (basic) | Asana (②③) | §11.9 | 🔲 Deferred after M1 core |
| Dashboard (basic) | Manual tallying (⑱) | §11.10 | ⚠️ M1 daily report in progress |

#### Milestone 1 — Operations Board (first build target)
Scope:
- Patient management: create/search/view patient records needed for front-desk flow
- Admin portal: room management (create/edit/active status), staff management (create/edit/role/active status)
- User portal: patient check-in workflow with check-in time, service type, service start time, service end/check-out time, room status updates
- Checkout flow: copay capture, WD verification, patient-signed visit confirmation
- Sign sheet PDF: generate printable per-patient sign sheet from structured visit history
- Daily reporting: auto-generate day-end report and persist all event + projection data

Deliverables:
- Event contracts for patient, room, staff, check-in/out, service timing, payment/sign-off, and room status change
- Read models for room board, visit history, staff-hour aggregates, sign-sheet PDF source data, and daily summary report
- API + UI slices for patient management, admin setup, check-in/check-out, and daily operations workflows
- Backend and browser E2E coverage for the M1 golden path
- Daily report persistence job (scheduled + manual re-run)

Definition of done:
- Front desk can manage patients, staff, and rooms needed for daily flow without paper trackers
- Front desk and therapists can complete check-in, room assignment, service, and check-out without paper
- Printable sign-sheet PDF can be generated from ClinicOS visit data for in-clinic signing workflow
- Manager can see real-time staff hours, room occupancy, and end-of-day aggregation
- End-of-day report is generated, saved, and reproducible from event log

Out of scope for M1:
- Eligibility workflow / Asana replacement
- Insurance portal operations beyond basic stored policy fields
- Appointment-first workflow as the primary entry point
- Claim submission, EOB reconciliation, denial handling, and posting correction
- Full clinical note workflow beyond basic status support

### Phase 2 — 后台保险与 Claim 流程打通 (Insurance + Billing)

| Module | Replaces | PRD § | Status |
|---|---|---|---|
| Insurance / Eligibility | Portal queries (④), Notability ledger (⑤) | §11.7 + PRD-004 §2.7 | 🔲 Not started |
| **Eligibility Verification Workflow (替代 Asana)** | asana insurance inquiry list — 5-question SOP, by year, per patient | PRD-004 §2.7 | 🔲 Not started |
| **Digital Signature Archive (替代 Notability)** | 签字总表 — 317+ patient notebooks | PRD-004 §2.6 | 🔲 Not started |
| Claim / Billing State Machine | Manual claim entry (⑪⑫) | §11.8 | 🔲 Not started |
| Denial / AR Queue | Manual comparison (⑬–⑰) | §11.8 | 🔲 Not started |
| Billing Dashboard | Manual reconciliation | §11.10 | 🔲 Not started |
| Task Migration (Asana → Clinic OS) | Asana (②③) | §11.9 | 🔲 Not started |

### Phase 3 — AI 输入与自动化 (AI Input + Automation)

| Module | Replaces | PRD § | Status |
|---|---|---|---|
| Voice / Handwriting / Free-text Input | Manual structured entry | §11.6 | 🔲 Not started |
| OCR / Speech-to-Text / LLM Extraction | Manual transcription | §8.2 | 🔲 Not started |
| AI Note Completeness Check | Human review only | §11.6 | 🔲 Not started |
| AI Tasking / AI QA | Manual task creation | §11.9 | 🔲 Not started |

### Phase 4 — AI Agent 后台协作 (AI Agent Back-Office)

| Module | Description | PRD § | Status |
|---|---|---|---|
| AI Agent Standardized Case Processing | Auto-process eligibility, denial classification, claim prep | §11.9 | 🔲 Not started |
| Human Review + Exception Handling | Human-in-the-loop for high-risk actions | §11.9 | 🔲 Not started |
| Operation Log / Rollback / Approval Flow | Full audit for AI actions | §11.9, §11.11 | 🔲 Not started |

### Phase 5 — 合规强化与深度集成 (Compliance + Integration)

| Module | Description | PRD § | Status |
|---|---|---|---|
| Audit Log Enhancement | Field-level tracking, retention policies | §12.1 | 🔲 Not started |
| Permission Fine-tuning | Granular RBAC, least-privilege enforcement | §11.11 | 🔲 Not started |
| External Integrations | EHR (⑩), PracticeMate (⑦), Clearinghouse, Calendar, Payment | §8.2 | 🔲 Not started |
| Multi-clinic / Multi-location | Multi-brand, multi-site support | §12.2 | 🔲 Not started |

## Tool Migration Strategy (PRD v2.0 §7)

| Tool | MVP Phase | Long-term | Clinic OS Module |
|---|---|---|---|
| Daily Sign In Sheet | 迁移期可并存 | 停用主流程 | Front Desk Operations Board |
| Google Sheets (room board) | 迁移期对照使用 | 被替代 | Front Desk Operations Board + Resource Model |
| Notability | 可部分保留 | 保留文档层 | Document / Consent / Clinical Note |
| Asana | 迁移期并存 | 患者任务迁回 Clinic OS | Task / Case Management |

## Key Decision: Compliance First

> **The first priority is NOT AI. The first priority is compliant architecture.**
> Without HIPAA-compliant infrastructure, nothing can be commercialized.

Every module must pass compliance review before shipping. The Compliance agent has veto power.

## Core Domain Model (PRD v2.0 §9)

Patient · Appointment · Visit · Room / Resource Allocation · Clinical Note · Document · Consent / Intake Package · Insurance Policy · Eligibility Check · Claim · Task / Case · User · Role / Permission · Audit Log

## Tech Decisions

| Decision | Choice | ADR |
|---|---|---|
| Core architecture | Event Sourcing + CQRS | ADR-001 |
| Backend | Python + FastAPI + PostgreSQL | — |
| Frontend | TBD (React/Next.js, iPad-first) | — |
| Auth | JWT + RBAC | — |

## PRD Documents

| Doc | Title | Status |
|---|---|---|
| PRD-000 | Product Roadmap (this file) | Active |
| PRD-001 | Electronic Daily Sign Sheet | Draft v2 — scoped under PRD-003 §11.3 |
| PRD-002 | M1 Task Breakdown + Prototype | Ready to execute |
| PRD-003 | Clinic OS PRD v2.0（完整整合版） | **Canonical** |
