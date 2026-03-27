# ClinicOS Harness

This repo now includes a lightweight local harness for UI-driven regression testing.

## What It Includes

- `scripts/start-backend.sh`
  - Starts the FastAPI app in local SQLite mode for deterministic testing
- `scripts/install-playwright.sh`
  - Installs npm dependencies and the Chromium browser used by Playwright
- `scripts/test-ui.sh`
  - Runs the Playwright suite
- `frontend/tests/e2e/`
  - Browser tests for the most important click flows
- `POST /prototype/test/reset`
  - Local-only test reset endpoint for clearing demo data before each run

## Why This Exists

Most ClinicOS bugs are found by clicking through the UI:

- room state not refreshing
- visit lifecycle buttons not matching backend state
- report totals drifting from the actual flow
- event log not reflecting the visible workflow

API tests alone do not catch these regressions reliably. The harness adds a browser-level feedback loop.

## Install

```bash
./scripts/install-playwright.sh
```

## Run

```bash
./scripts/test-ui.sh
```

Headed mode:

```bash
npm run test:e2e:headed
```

## Current Coverage

- Admin creates room
- Admin creates staff
- Ops Board walk-in check-in and service start
- Service end and checkout
- Daily report generation
- Event log visibility for the completed visit flow

## Regression Workflow

When you find a bug manually:

1. Write down the exact click path.
2. Add a Playwright test that reproduces it.
3. Watch the test fail.
4. Fix the bug.
5. Keep the test in the suite.

That turns one-off manual discoveries into permanent regression protection.
