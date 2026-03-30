# ClinicOS Harness

This repo now includes a lightweight local harness for UI-driven regression testing.

## What It Includes

- `scripts/start-backend.sh`
  - Starts the FastAPI app in local SQLite mode for deterministic testing
- `scripts/install-playwright.sh`
  - Installs npm dependencies and the Chromium browser used by Playwright
- `scripts/test-ui.sh`
  - Runs the Playwright suite
- `scripts/setup-hooks.sh` ✨ **NEW**
  - Installs pre-commit hook for automatic test running
- `scripts/pre-commit.sh` ✨ **NEW**
  - Pre-commit hook that runs tests before allowing commit
- `.github/workflows/test.yml` ✨ **NEW**
  - GitHub Actions workflow for CI/CD automated testing
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
./scripts/setup-hooks.sh  # Install pre-commit hook
```

## Run

```bash
./scripts/test-ui.sh
```

Headed mode:

```bash
npm run test:e2e:headed
```

## Automated Testing

### Pre-Commit Hook

After running `./scripts/setup-hooks.sh`, tests will automatically run before each commit:

```bash
git commit -m "your changes"
# → Automatically runs pytest + playwright tests if relevant files changed
```

To skip hook for emergency commits:

```bash
git commit --no-verify -m "emergency fix"
```

### CI/CD Pipeline

Tests run automatically on every push to `main` or `develop`:

1. **Backend tests**: `pytest tests/ -x -q`
2. **Frontend tests**: `npx playwright test`

See `.github/workflows/test.yml` for configuration.

## Current Coverage

### Existing Tests

- Admin creates room
- Admin creates staff
- Ops Board walk-in check-in and service start
- Service end and checkout
- Daily report generation
- Event log visibility for the completed visit flow
- Treatment records tab validation
- Sign sheet PDF generation and verification
- Insurance copay pre-fill (BUG-13)
- Patient creation validation (BUG-15)

### Comprehensive End-to-End Test ✨ **NEW**

**Test name**: `complete clinic workflow: staff → patient → checkin → treatments → checkout → PDF verification`

**Full workflow coverage**:
1. ✅ Create new staff member with license
2. ✅ Create new patient with DOB and phone
3. ✅ Add insurance policy with copay
4. ✅ Check-in patient with doctor and initial treatment (PT 45m)
5. ✅ Add additional treatment (Acupuncture 30m) with notes
6. ✅ End service
7. ✅ Checkout with pre-filled copay ($45)
8. ✅ Verify WD and patient signature checkboxes
9. ✅ Generate sign-sheet PDF
10. ✅ Validate PDF structure and content
11. ✅ Verify daily report shows correct totals (1 visit, $45, 1h15m staff hours)

**Runs on**: Every commit with frontend changes (via pre-commit hook + CI/CD)

## Regression Workflow

When you find a bug manually:

1. Write down the exact click path.
2. Add a Playwright test that reproduces it.
3. Watch the test fail.
4. Fix the bug.
5. Keep the test in the suite.

That turns one-off manual discoveries into permanent regression protection.

## Test Harness Rules

From `CLAUDE.md`:

### Before Committing

| File changed | Tests to run |
|---|---|
| `backend/app/services/db_service.py` | `cd backend && python -m pytest tests/ -x -q` + `npx playwright test` |
| `backend/app/services/pdf_service.py` | `cd backend && python -m pytest tests/test_pdf_who_what_when_where.py tests/test_prd004_features.py -q` + `npx playwright test --grep "sign sheet PDF"` |
| `backend/app/routers/db_routes.py` | `cd backend && python -m pytest tests/ -x -q` |
| `backend/app/schemas/prototype.py` | `cd backend && python -m pytest tests/ -x -q` |
| `frontend/index.html` | `npx playwright test` |
| `frontend/tests/e2e/*.ts` | `npx playwright test` |

**Full suite (pre-commit hook runs this automatically)**:
```bash
cd backend && python -m pytest tests/ -x -q && cd .. && npx playwright test
```

### features.json and bugs.json Requirements

- **Both `api_test` AND `ui_test` required** (use `null` only when genuinely no test exists)
- **`feature_ref` in bugs.json** must point to existing feature ID
- **Never mark `passes: true`** without running tests
- **bugs.json = bugs only** (never add to features.json)
- **features.json = features only** (never add bugs)

