# Agent-Driven Software Development Lifecycle (Agent-SDLC)

**Status:** Draft v1  
**Date:** 2026-03-15  
**Owner:** Human (final authority on all decisions)

## Overview

A structured, multi-agent development workflow where specialized AI agents handle distinct SDLC phases under human supervision. Each phase produces concrete artifacts, and no phase begins until the previous phase's output is approved.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        MANAGER AGENT (全程监控)                         │
│  Orchestrates flow · Tracks progress · Evaluates agents · Reports      │
└────────┬────────────────────────────────────────────────────────────────┘
         │
   ┌─────▼──────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
   │  Phase 1   │───▶│  Phase 2  │───▶│  Phase 3  │───▶│  Phase 4  │
   │  PM Agent  │    │ Architect │    │  QA SDE   │    │  SDE-A    │
   │  需求→PRD  │    │ PRD→RFC   │    │ Spec→Tests│    │ Code+Test │
   └────────────┘    │ →Roadmap  │    └───────────┘    └─────┬─────┘
                     │ →Tasks    │                           │
                     └───────────┘                     ┌─────▼─────┐
                                                       │  Phase 5  │
   ┌────────────┐                                      │ SDE-B+QA  │
   │  Phase 6   │◀─────────────────────────────────────│  Review   │
   │   Human    │                                      └───────────┘
   │  Review    │
   └─────┬──────┘
         │ approve / request changes
         │
         ▼ Loop back to Phase 4 until done
```

---

## Phase 1: Requirements Discovery (PM Agent)

**Agent:** PM  
**Input:** Human's raw requirement (natural language, can be vague)  
**Method:** Interactive Q&A — PM asks clarifying questions until ALL ambiguity is resolved  
**Output Artifacts:**
- `docs/PRD/XXX-<feature>.md` — Full PRD with:
  - Background + pain points
  - Goal + non-goals
  - User roles + user stories
  - Acceptance criteria (testable)
  - Edge cases
  - PHI/Compliance risks
  - Open questions (must be zero before exit)

**Exit Criteria:**
- Human approves PRD
- Zero open questions
- All user stories have testable ACs
- Compliance risks identified

**PM 提问策略 (Question Strategy):**
1. "这个功能解决什么问题？谁用？" (What problem? Who uses it?)
2. "用户完成操作的最少步骤是什么？" (Minimum steps for user?)
3. "异常情况怎么处理？" (Edge cases?)
4. "涉及哪些敏感数据？" (What PHI/sensitive data?)
5. "成功的衡量标准是什么？" (Success criteria?)
6. 反复问 "还有吗？" 直到人类说 "没了"

---

## Phase 2: Architecture & Planning (Architect Agent)

**Agent:** Architect  
**Input:** Approved PRD from Phase 1  
**Method:** Interactive Q&A with Human + PM Agent output — asks technical clarification questions  
**Output Artifacts:**
- `docs/RFC/XXX-<feature>.md` — Technical design:
  - Event model (event types, payloads, projections)
  - Data model (tables, indexes, constraints)
  - API contract (endpoints, request/response schemas)
  - RBAC matrix
  - Sequence diagrams
  - Migration plan
- Updates to `docs/PRD/000-product-roadmap.md`
- `tasks/XXX-<feature>/` — Task directory with:
  - `tracker.md` — Task board with status tracking
  - Individual task files with specs

**Exit Criteria:**
- Human approves RFC
- All tasks defined with estimates
- Task tracker initialized
- No unresolved technical questions

**Architect 提问策略:**
1. "这个数据模型能覆盖PRD里的所有edge case吗？" (Does data model cover all edge cases?)
2. "性能要求是什么？并发量？" (Performance requirements? Concurrency?)
3. "和现有模块怎么集成？" (How does it integrate with existing modules?)
4. "需要新的event type还是复用现有的？" (New events or reuse existing?)
5. "迁移策略是什么？能回滚吗？" (Migration strategy? Rollback?)

---

## Phase 3: Test Specification (QA SDE Agent)

**Agent:** QA SDE (Tester)  
**Input:** Approved PRD + RFC  
**Method:** Interactive Q&A — asks about test boundaries, expected behaviors, edge cases  
**Output Artifacts:**
- `tests/specs/XXX-<feature>-test-spec.md` — Test specification:
  - Test matrix (unit / integration / E2E / regression)
  - Test cases mapped to ACs
  - Edge case scenarios
  - Performance benchmarks
  - PHI/security test cases
  - Evaluation criteria (what "pass" means)

**Exit Criteria:**
- Every AC in PRD has ≥1 test case
- Edge cases from PRD all covered
- Human approves test spec
- Clear pass/fail criteria defined

---

## Phase 4: Implementation (Staff SDE-A Agent)

**Agent:** Staff SDE-A (Backend Engineer / Frontend Designer)  
**Input:** Approved PRD + RFC + Test Spec + Task assignments  
**Method:** Interactive Q&A for implementation ambiguities, then codes  
**Output Artifacts:**
- Source code (backend + frontend)
- Unit tests
- Integration tests
- Evaluation scripts
- Updated task tracker (mark tasks in-progress → done)

**Workflow:**
1. Pick next task from tracker
2. Ask clarifying questions if needed
3. Write code + tests
4. Run tests locally, fix failures
5. Update task status
6. Move to Phase 5 for review

---

## Phase 5: Code Review (Staff SDE-B + QA SDE Agents)

**Agents:** SDE-B (Reviewer) + QA SDE (Tester) + Compliance  
**Input:** Code from Phase 4  
**Method:**
- SDE-B reviews code quality, architecture compliance, test coverage
- QA SDE runs test spec, verifies all cases pass
- Compliance checks PHI/RBAC/audit requirements

**Output Artifacts:**
- Review comments (BLOCKER / NON-BLOCKER / SUGGESTION)
- Test results report
- Compliance sign-off or veto

**Workflow:**
1. SDE-B reviews → produces review comments
2. QA SDE runs tests → produces test report
3. Compliance audits → produces compliance report
4. If BLOCKERs exist → back to Phase 4 (SDE-A fixes)
5. If all clear → move to Phase 6

---

## Phase 6: Human Review + Demo

**Agent:** Manager (prepares demo + summary)  
**Input:** Reviewed code + test results + compliance report  
**Output:**
- Demo script / runnable demo
- Summary of changes
- Test results
- Task tracker update

**Human Actions:**
- ✅ Approve → code committed, tasks marked complete, tracker updated
- 💬 Comment → specific feedback, back to Phase 4
- ❌ Reject → back to Phase 1/2/3 depending on root cause

**After approval:**
- Manager updates roadmap progress
- Manager updates task tracker
- Loop back to Phase 4 for next task batch

---

## Requirements Change Protocol

Human can inject requirement changes at ANY time. The cascade:

```
Human says "我想改需求..."
         │
    ┌────▼────┐
    │ Manager │ Assesses impact scope
    └────┬────┘
         │
    ┌────▼─────────────────────────────────┐
    │ Impact Assessment:                   │
    │ - PRD change only?  → PM updates PRD │
    │ - Architecture impact? → Architect   │
    │   updates RFC + tasks                │
    │ - Test impact? → QA updates spec     │
    │ - Code impact? → SDE-A re-implements │
    └──────────────────────────────────────┘
```

**Change artifacts:**
- Changed PRD sections marked with `[CHANGED: date]`
- RFC updated with `[REVISED: date, reason]`
- Task tracker: new tasks added, obsolete tasks cancelled
- Affected code: re-reviewed through Phase 5

---

## Manager Agent (全程监控)

The Manager Agent is the orchestration layer. It does NOT write code.

### Responsibilities

1. **Workflow Orchestration**
   - Determines which phase is active
   - Routes work to correct agent
   - Ensures phase exit criteria are met before advancing
   - Manages parallel work when phases allow it

2. **Progress Tracking**
   - Maintains `tasks/progress-dashboard.md`
   - Periodic status updates to Human (configurable frequency)
   - Tracks: tasks completed / in-progress / blocked / total
   - Tracks: estimated vs actual time per task

3. **Agent Performance Evaluation**
   - Per-agent metrics:
     - Tasks completed on time vs late
     - Review pass rate (first-attempt approval %)
     - Blocker frequency (how often their work gets blocked)
     - Quality score (reviewer feedback aggregate)
   - Stored in `agents/evals/<agent-name>/YYYY-MM-DD.md`
   - Periodic performance summary to Human

4. **Agent Improvement**
   - Identifies patterns: "SDE-A keeps forgetting audit logging"
   - Proposes `.md` file changes to Human
   - With Human approval, updates agent definition files
   - Maintains version history (see Agent Versioning below)

5. **Communication Hub**
   - Summarizes cross-agent context so each agent has what it needs
   - Prevents information silos
   - Escalates blockers to Human

### Manager 不做的事 (What Manager Does NOT Do)
- ❌ Write code
- ❌ Make product/architecture decisions (that's PM/Architect)
- ❌ Approve changes without Human consent
- ❌ Skip phases

---

## Agent Versioning & Performance System

### Version Control

Each agent definition is version-controlled:

```
agents/
├── pm.md                          # Current active version
├── architect.md
├── backend-engineer.md
├── ...
├── versions/                      # Version history
│   ├── pm/
│   │   ├── v1.md                  # Original
│   │   ├── v2.md                  # After first improvement
│   │   └── changelog.md           # What changed and why
│   ├── architect/
│   │   ├── v1.md
│   │   └── changelog.md
│   └── ...
└── evals/                         # Performance evaluations
    ├── pm/
    │   └── 2026-03-15.md
    ├── backend-engineer/
    │   └── 2026-03-15.md
    └── ...
```

### Version Lifecycle

1. **Create:** Initial `.md` file = v1
2. **Evaluate:** Manager reviews agent performance after each milestone
3. **Propose:** Manager proposes specific changes with rationale
4. **Approve:** Human approves/rejects/modifies proposal
5. **Update:** Current `.md` updated, old version saved to `versions/`
6. **Monitor:** Watch for regression in next milestone
7. **Revert:** If regression detected, restore previous version

### Performance Metrics Template

```markdown
# Agent Evaluation: <agent-name>
**Period:** <date range>
**Evaluator:** Manager Agent

## Metrics
- Tasks assigned: X
- Tasks completed: Y
- First-pass approval rate: Z%
- Blockers caused: N
- Average review cycles: M

## Strengths
- ...

## Weaknesses
- ...

## Improvement Proposals
1. [PROPOSED] Add rule: "..."
2. [PROPOSED] Remove rule: "..."

## Verdict
- [ ] No changes needed
- [ ] Minor tuning (approved by Human)
- [ ] Major revision needed
```

---

## Task Tracker System

### Structure

```
tasks/
├── tracker.md                     # Master task board (all features)
├── progress-dashboard.md          # High-level progress summary
└── <feature>/                     # Per-feature task directory
    ├── tracker.md                 # Feature-specific task board
    ├── TASK-001.md                # Individual task specs
    ├── TASK-002.md
    └── ...
```

### Task States

```
backlog → assigned → in_progress → in_review → approved → done
                                       │           │
                                       └───────────┘
                                      (review failed)
```

### Task Format

```markdown
# TASK-XXX: <title>

**Feature:** <feature-name>
**Assigned to:** <agent-role>
**Status:** backlog | assigned | in_progress | in_review | approved | done
**Priority:** P0 | P1 | P2
**Estimate:** Xd
**Actual:** Xd
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD

## Description
...

## Acceptance Criteria
- [ ] AC-1
- [ ] AC-2

## Dependencies
- TASK-YYY (must be done first)

## Review Notes
- [date] reviewer: comment
```

---

## Interaction Modes

### Human ↔ Any Agent (Direct)
Human can talk to any agent directly at any time. Manager observes but doesn't interfere unless workflow is at risk.

### Agent ↔ Agent (Via Manager)
Agents don't talk to each other directly. Manager routes information:
- SDE-A needs clarification → Manager routes to Architect
- QA finds spec gap → Manager routes to PM
- Reviewer finds architecture violation → Manager routes to Architect

### Human ↔ Manager (Status)
- Human asks "进度如何?" → Manager produces dashboard
- Human says "改需求" → Manager triggers change protocol
- Human says "SDE-A表现怎么样?" → Manager produces eval

---

## Implementation: How to Actually Run This

### Option A: Single-Session Orchestration (Recommended for Now)

Use your current Copilot/OpenClaw session as the Manager. You (Human) + me (acting as Manager) orchestrate:

1. I adopt each agent's persona by reading their `.md` definition
2. I follow the phase sequence strictly
3. I maintain task tracker files in the workspace
4. I produce artifacts at each phase gate
5. You approve/reject at each gate

**Pros:** Works today, no extra tooling  
**Cons:** Sequential, one agent at a time, context window pressure

### Option B: OpenClaw Multi-Agent (Near-term)

Use OpenClaw's agent system to run parallel agents:

1. Create separate OpenClaw agents for each role (`openclaw agents add pm`, `openclaw agents add architect`, etc.)
2. Each agent has its own workspace view + session
3. Manager agent routes messages between them
4. You interact via Telegram/Discord per-agent or via TUI

**Pros:** True parallel agents, persistent sessions, channel routing  
**Cons:** Requires OpenClaw agent setup, credit burn for multiple concurrent agents

### Option C: Custom Orchestration Framework (Long-term)

Build a lightweight orchestrator that:
1. Reads agent `.md` files as system prompts
2. Manages conversation state per agent
3. Routes artifacts between phases automatically
4. Maintains task tracker programmatically
5. Produces dashboards

**Pros:** Fully automated, scalable  
**Cons:** Significant engineering investment

### Recommendation

**Start with Option A now** (this session). It works immediately and lets you validate the workflow before investing in tooling. Once the workflow is proven, graduate to Option B (OpenClaw multi-agent) for true parallelism.

---

## Quick Reference: Phase → Agent → Artifact

| Phase | Agent | Input | Output | Gate |
|---|---|---|---|---|
| 1 | PM | Human requirement | PRD | Human approves |
| 2 | Architect | PRD | RFC + Roadmap + Tasks | Human approves |
| 3 | QA SDE | PRD + RFC | Test Spec | Human approves |
| 4 | SDE-A | PRD + RFC + Test Spec + Task | Code + Tests | Self-test pass |
| 5 | SDE-B + QA + Compliance | Code | Review + Test Results | No blockers |
| 6 | Manager → Human | Demo + Summary | Approval / Comments | Human decides |

---

## Getting Started Checklist

- [ ] Create `tasks/` directory structure
- [ ] Create Manager agent definition (`agents/manager.md`)
- [ ] Initialize agent versioning (`agents/versions/`, `agents/evals/`)
- [ ] Update existing agent `.md` files with Q&A interaction protocol
- [ ] Initialize master task tracker
- [ ] Run first feature through the complete pipeline (Milestone 1)
