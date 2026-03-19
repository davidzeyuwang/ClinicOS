# Clinic OS — Product Roadmap

**Last Updated:** 2026-03-16

> **Canonical PRD:** `PRD/003-clinic-os-prd-v2.md` (v2.0) — all module scope, phasing, and tool migration strategy are defined there.

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
| Patient Master File | Scattered records across paper/Notability | §11.1 | 🔲 Not started |
| Appointment Management | PracticeMate only, no unified view | §11.2 | 🔲 Not started |
| Front Desk Operations Board (签到 + 房间/资源板) | Paper sign sheet (⑧) + Google Sheets (⑨) + Manual tally (⑱) | §11.3 | 🔲 Not started |
| Visit Management | Manual tracking | §11.5 | 🔲 Not started |
| Clinical Note (basic status) | EHR notes, Notability | §11.6 | 🔲 Not started |
| Document / Signature Archive (basic) | Notability 手工归档 | §11.4 | 🔲 Not started |
| Task Management (basic) | Asana (②③) | §11.9 | 🔲 Not started |
| Dashboard (basic) | Manual tallying (⑱) | §11.10 | 🔲 Not started |

#### Milestone 1 — Operations Board (first build target)
Scope:
- Admin portal: room management (create/edit/active status), staff management (create/edit/role/active status)
- User portal: patient check-in workflow with check-in time, service type, service start time, service end/check-out time, room status updates
- Real-time aggregate: per-staff working hours and active session counters
- Daily reporting: auto-generate day-end report and persist all event + projection data

Deliverables:
- Event contracts for room, staff, check-in/out, service timing, and room status change
- Read models for room board, staff-hour aggregates, and daily summary report
- API + UI slices for admin and user portal workflows
- Daily report persistence job (scheduled + manual re-run)

Definition of done:
- Front desk and therapists can complete full visit lifecycle without paper
- Manager can see real-time staff hours and room occupancy
- End-of-day report is generated, saved, and reproducible from event log

### Phase 2 — 后台保险与 Claim 流程打通 (Insurance + Billing)

| Module | Replaces | PRD § | Status |
|---|---|---|---|
| Insurance / Eligibility | Portal queries (④), Notability ledger (⑤) | §11.7 | 🔲 Not started |
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
