# Clinic OS

**Vertical AI Operating System for Clinical Practice Management**

An event-driven clinic automation platform — replacing paper workflows with real-time, auditable, HIPAA-compliant digital operations.

**Production:** https://clinicos-psi.vercel.app

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

- **Backend:** Python 3.11 · FastAPI · SQLAlchemy 2.0 async · Pydantic v2
- **Database:** SQLite (local dev) / Supabase PostgreSQL (production)
- **Frontend:** Single-file HTML/JS (`frontend/index.html`) — iPad-optimized
- **Deployment:** Vercel (frontend + API routes) + Supabase (database)
- **Auth:** JWT-based, role-aware (admin · frontdesk · doctor)
- **Testing:** pytest (backend) · Playwright (end-to-end UI)

## Recently Implemented Features

### 🔐 Authentication & Multi-Tenancy *(2026-04-03)*
- **Clinic owner self-registration** — public signup creates clinic + owner account in one step (`POST /auth/register`)
- **User accounts & JWT authentication** — `users` table with hashed passwords; `POST /auth/login` returns a signed JWT
- **Role model** — `admin` (full access) · `frontdesk` (ops + checkout + reports) · `doctor` (read-only patient/treatment data)
- **Tenant data model** — `clinics` table with `clinic_id` FK on all tenant-scoped tables (staff, rooms, patients, visits)
- **Tenant isolation middleware** — FastAPI dependency injects `clinic_id` from JWT into every DB query; cross-tenant data leakage is impossible

### 🛠️ Admin Configuration *(2026-04-03)*
- **Admin-managed service types** — admins create/edit/retire service types via API; no more hard-coded frontend lists
- **Staff qualification by service type** — each staff member linked to the service types they can perform; assignment flows respect qualifications

### 💊 Multiple Treatments Per Visit *(2026-03-26 – 2026-03-27)*
- **Backend API** — `visit_treatments` table + 5 endpoints: add · list · update · delete · filter records; all operations logged to `event_log`
- **Treatment management UI** — "➕ Tx" button on in-service visits; add/edit/delete treatments modal with modalities (PT, OT, E-stim, Massage, Cupping, Acupuncture, Heat, Cold)
- **Checkout summary** — checkout modal shows all treatments performed before patient signs
- **Treatment records page** — new 🩺 tab with date-range / patient / staff filters for billing and compliance review

### 📄 PDF & Document Archive *(2026-03-26)*
- **Simplified sign-sheet PDF** — clean format: Date · Service · Room · Copay · WD · Sign · Check-Out; no verbose headers
- **PDF at checkout** — "📄 Download Sign Sheet PDF" button in checkout modal
- **Selective PDF generation** — visit-history checkboxes let front desk pick specific visits; `?visit_ids=x,y,z` backend param; "Selected (N) PDF" button

### 🏥 Core Operations *(2026-03-26)*
- **Patient Master File** — create, search, view patient records (replaces paper/Notability)
- **Front Desk Operations Board** — real-time room board: check-in/out, room status, copay (CC), WD verified, patient signature
- **Visit lifecycle management** — `checkin → in_service → service_completed → checked_out` with room assignment and service timestamps
- **Daily Summary Report** — auto-generated end-of-day visit counts, copay totals, staff hours
- **Supabase REST backend** — production-ready backend deployed to Vercel with Supabase PostgreSQL

## Current Status

| Area | Status |
|---|---|
| Core ops board (M1) | ✅ Complete |
| Multiple treatments | ✅ Complete (backend + frontend) |
| PDF sign sheet | ✅ Complete (selective + checkout) |
| Auth + JWT | ✅ Complete |
| Multi-tenancy | ✅ Complete |
| Admin service types | ✅ Complete |
| RBAC enforcement on all routes | 🔜 Next |
| Frontend: auth/login flow | 🔜 Next |

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
# 1. Install backend dependencies
cd backend && pip install -r requirements.txt

# 2. Start the server (SQLite auto-created, demo staff seeded)
uvicorn app.main:app --reload --port 8000

# 3. Verify it's alive
curl http://localhost:8000/health

# 4. Open the UI
open http://localhost:8000/ui/index.html
```

Or use the one-command startup from the repo root:

```bash
./init.sh
```

## Running Tests

```bash
# Backend (pytest)
cd backend && python -m pytest tests/ -x -q

# End-to-end UI (Playwright)
npx playwright test
```

## UI Harness

ClinicOS includes a Playwright-based browser harness for catching UI regressions.

Install:

```bash
./scripts/install-playwright.sh
```

Run:

```bash
./scripts/test-ui.sh
```

Details: `docs/workflow/HARNESS.md`
