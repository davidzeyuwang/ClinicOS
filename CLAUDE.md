# ClinicOS — Project Contract

> Read this first. Every session. No exceptions.

## What This Is

ClinicOS is a clinic operating system replacing paper Sign-In Sheet + Google Sheets + Notability + Asana with a unified, event-sourced, auditable platform.

**Stack:** FastAPI · Python 3.11+ · SQLAlchemy 2.0 async · Pydantic v2 · SQLite (local) / Supabase (prod)

---

## First Thing Every Session

```bash
cat SESSION.md      # read last session's state and next steps
./init.sh           # start server + smoke tests
```

---

## How to Start

```bash
# 1. Start the backend (SQLite auto-created, demo staff seeded)
cd backend && uvicorn app.main:app --reload --port 8000

# 2. Verify it's alive
curl http://localhost:8000/health

# 3. Open UI
open http://localhost:8000/ui/index.html
```

Or just run `./init.sh` from the repo root.

**Run tests:**
```bash
cd backend && python -m pytest tests/ -x -q
```

**Local DB:** `backend/clinicos.db` — SQLite, auto-created on startup. Delete it to reset.
**Prod DB:** Supabase — requires `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` env vars.

---

## Current State

**Milestone:** M1 — Operations Board
**Progress:** See `tasks/features.json` (the authoritative completion record)
**Task board:** `tasks/tracker.md`
**Workflow:** `docs/workflow/AGENT-SDLC.md` (6-phase: PM → Architect → QA → SDE-A → Review → Human)

---

## Architecture Invariants (Non-Negotiable)

These come from `docs/ADR/001-event-sourcing.md`. Violating them breaks the audit chain.

1. **Write to `event_log` first.** Every state change is an event. No exceptions.
2. **Read from projections only.** Never query `event_log` for display data.
3. **Never mutate projection state directly.** Projections are rebuilt from events.
4. **No PHI in logs or error messages.** Use entity IDs only.
5. **Every endpoint needs Pydantic schema validation.** No raw dict parsing in routers.

---

## Where Things Live

```
CLAUDE.md                    ← you are here (project contract)
SESSION.md                   ← last session's state + next steps (read first!)
init.sh                      ← one-command startup
tasks/features.json          ← M1 completion status (machine-verifiable)
tasks/tracker.md             ← task board
tasks/progress-dashboard.md  ← high-level milestone progress

docs/workflow/AGENT-SDLC.md  ← 6-phase agent workflow definition
docs/PRD/003-clinic-os-prd-v2.md  ← full product requirements
docs/ADR/001-event-sourcing.md    ← architecture decisions

agents/                      ← agent role definitions (source of truth)
.claude/agents/              ← Claude Code subagents (loaded from agents/)

backend/app/
  main.py                    ← FastAPI app entry point
  routers/db_routes.py       ← all API routes (prefix: /prototype)
  services/db_service.py     ← business logic (SQLite mode)
  services/db_service_supa.py← business logic (Supabase mode)
  models/tables.py           ← SQLAlchemy models
  schemas/prototype.py       ← Pydantic schemas
  tests/test_prototype_e2e.py← E2E test suite

frontend/index.v1.html       ← single-file UI prototype
```

---

## Agent Roles (use as subagents)

| Role | File | When to invoke |
|---|---|---|
| `pm` | `.claude/agents/pm.md` | Requirements → PRD |
| `architect` | `.claude/agents/architect.md` | PRD → RFC + task breakdown |
| `backend-engineer` | `.claude/agents/backend-engineer.md` | Implement M1-BE-* tasks |
| `tester` | `.claude/agents/tester.md` | Write + run test specs |
| `reviewer` | `.claude/agents/reviewer.md` | Code review gate |
| `compliance` | `.claude/agents/compliance.md` | PHI/RBAC audit |
| `manager` | `.claude/agents/manager.md` | Orchestrate phases, update tracker |

---

## Absolute Prohibitions

- **Never mark `passes: true` in features.json** without running the `verify` command and seeing it pass.
- **Never write to a projection table directly** — always replay from events.
- **Never log patient names, DOBs, SSNs** — log entity IDs only.
- **Never skip the AGENT-SDLC phase gates** without explicit human approval.
- **Never commit with failing tests** (run `cd backend && python -m pytest tests/ -x -q` first).

---

## Context Compaction Priority

If context is compressed, preserve in this order:
1. Architecture decisions (ADR-001 invariants above)
2. PRD constraints (what the product must do)
3. RFC schemas (API contracts, event payloads)
4. Current task states (features.json `passes` fields)
5. Tool output / scratch work (safe to drop)
