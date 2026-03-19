# ADR-001: Event Sourcing as Core Architecture

**Status:** Accepted
**Date:** 2026-03-02 (updated 2026-03-16)

## Context

Clinic OS handles patient visits, services, payments, and compliance data. Per PRD v2.0 (`PRD/003-clinic-os-prd-v2.md`), the system scope covers 14 core domain objects: Patient, Appointment, Visit, Room/Resource Allocation, Clinical Note, Document, Consent/Intake Package, Insurance Policy, Eligibility Check, Claim, Task/Case, User, Role/Permission, Audit Log.

In healthcare:

- Every change must be traceable (HIPAA audit requirements)
- History must never be lost (no accidental overwrites)
- Multiple views of the same data are needed (daily sheet, room board, reports)
- Disputes and investigations require "what happened and when"

## Decision

Use **Event Sourcing** as the core data architecture:

1. All state changes are recorded as immutable events in an `event_log` table
2. Current state is derived by projecting events into read-optimized views
3. Events are append-only — never updated, never deleted
4. Projections can be rebuilt from events at any time

Combined with **CQRS** (Command Query Responsibility Segregation):
- Write path: Command → Validate → Event → Store
- Read path: Query → Projection → Response

## Consequences

### Positive
- Full audit trail by default (free HIPAA compliance for data changes)
- Can rebuild any view from events (new reports, new dashboards)
- Temporal queries ("what was the state at 2pm?") are trivial
- No accidental data loss — immutable history
- Supports PRD v2.0’s unified state machine across appointment / visit / note / claim / task / document lifecycle
- Enables future AI agent operations to be fully auditable and rollback-capable (PRD v2.0 §11.9)

### Negative
- More complex than simple CRUD
- Projections must be maintained and kept in sync
- Event schema evolution requires careful versioning
- Higher storage usage (events + projections)

### Mitigations
- Start with PostgreSQL for both events and projections (single DB, simpler ops)
- Use event versioning from day one (schema_version field)
- Build projection rebuild tooling early
- Monitor projection lag

## Alternatives Considered

1. **Traditional CRUD with audit table** — Simpler but audit is bolted-on, easy to forget, harder to rebuild state
2. **Full event streaming (Kafka)** — Overkill for MVP, can migrate later if needed

## References

- Martin Fowler: Event Sourcing
- Greg Young: CQRS and Event Sourcing
- `PRD/003-clinic-os-prd-v2.md` — Clinic OS PRD v2.0 (canonical scope & domain model)
- `PRD/001-daily-sign-sheet.md` — Detailed event model for Front Desk Operations Board
- `docs/clinic-workflow.md` — As-is 18-step workflow and compliance risk map
