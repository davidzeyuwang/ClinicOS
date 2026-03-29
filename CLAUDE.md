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
tasks/features.json          ← completed features (machine-verifiable, features only)
tasks/bugs.json              ← all bugs fixed (each linked to a feature_ref)
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

## Harness Engineering — Required Every Session

### Entry schemas

**Feature entry** (`tasks/features.json`):
```json
{ "id": "...", "title": "...", "description": "...",
  "api_test": "cd backend && python -m pytest tests/test_X.py -q",
  "ui_test":  "npx playwright test --grep \"<test name>\"",
  "verify": "<human-readable description of what to check>",
  "passes": true, "completed": "YYYY-MM-DD" }
```

**Bug entry** (`tasks/bugs.json`):
```json
{ "id": "BUG-N", "title": "...", "status": "fixed", "feature_ref": "<feature id>",
  "date_fixed": "YYYY-MM-DD", "root_cause": "...", "fix": "...",
  "files": [...],
  "api_test": "cd backend && python -m pytest tests/test_X.py -q",
  "ui_test":  "npx playwright test --grep \"<test name>\"" }
```

### Rules

- **Both `api_test` and `ui_test` are required.** Use `null` only when a layer genuinely has no test (e.g. a pure-backend-only change has no UI interaction to cover, or vice versa).
- `feature_ref` in bugs.json must point to an existing `id` in features.json.
- `bugs.json` is for bugs only — never add bugs to features.json.
- `features.json` is for features only — never add bugs or fix batches to features.json.

### On every code change — run related tests before committing

| File changed | Tests to run |
|---|---|
| `backend/app/services/db_service.py` | `cd backend && python -m pytest tests/ -x -q` + `npx playwright test` |
| `backend/app/services/pdf_service.py` | `cd backend && python -m pytest tests/test_pdf_who_what_when_where.py tests/test_prd004_features.py -q` + `npx playwright test --grep "sign sheet PDF"` |
| `backend/app/routers/db_routes.py` | `cd backend && python -m pytest tests/ -x -q` |
| `backend/app/schemas/prototype.py` | `cd backend && python -m pytest tests/ -x -q` |
| `frontend/index.html` | `npx playwright test` (from repo root) |
| `frontend/tests/e2e/*.ts` | `npx playwright test` (from repo root) |

**Full suite (always run before commit):**
```bash
cd backend && python -m pytest tests/ -x -q && cd .. && npx playwright test
```

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
