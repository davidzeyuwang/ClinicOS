# Clinic OS

**Vertical AI Operating System for Clinical Practice Management**

An event-driven clinic automation platform — replacing paper workflows with real-time, auditable, HIPAA-compliant digital operations.

## Vision

Clinic OS is not just a scheduling tool. It's an event-sourced operating system for clinical practices that handles:

- **Daily Sign Sheet** — digital replacement for paper check-in/service/payment tracking
- **Room & Resource Management** — real-time room status and therapist utilization
- **Revenue Cycle Management** — payment tracking, EOB reconciliation, automated reporting
- **Compliance & Audit** — full event trail, PHI protection, RBAC, HIPAA compliance

## Architecture Principles

1. **Event Sourcing** — All state changes are immutable events in `event_log`. Never overwrite history.
2. **CQRS** — Writes go through events; reads come from projections.
3. **Audit by Default** — Every operation is traceable: who, what, when.
4. **PHI Protection** — No PHI in logs, no PHI in task trackers, encryption at rest and in transit.
5. **iPad-First UX** — Must be as fast as paper. Touch/stylus optimized.

## Tech Stack

- **Backend:** Python + FastAPI + PostgreSQL
- **Frontend:** TBD (React/Next.js likely, iPad-optimized)
- **Events:** PostgreSQL event_log table (upgrade to message broker when needed)
- **Auth:** RBAC with role-based access control
- **Testing:** pytest + coverage gates

## Project Structure

```
clinic-os/
├── agents/           # Multi-agent role cards (PM, Architect, Engineer, etc.)
├── docs/
│   ├── PRD/          # Product Requirements Documents
│   └── ADR/          # Architecture Decision Records
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/       # SQLAlchemy / DB models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── events/       # Event definitions & handlers
│   │   ├── projections/  # Read-model projections
│   │   ├── routers/      # API endpoints
│   │   └── auth/         # RBAC & authentication
│   └── tests/
├── frontend/
└── README.md
```

## Multi-Agent Workflow

This project uses a multi-agent development workflow. See `/agents/*.md` for role definitions.

**Workflow per feature:**
1. **PM** → PRD with acceptance criteria
2. **Architect** → Data model, event model, API design
3. **Backend Engineer** → Implementation + tests
4. **Frontend Designer** → UI implementation
5. **Reviewer** → Code review (BLOCKER/NON-BLOCKER)
6. **Tester** → Test cases, coverage, regression
7. **Compliance** → HIPAA/PHI audit (veto power)
8. **Human (you)** → Final merge gate

## MVP: Sprint 1 — Electronic Daily Sign Sheet

See `docs/PRD/001-daily-sign-sheet.md` for full PRD.

## Getting Started

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
