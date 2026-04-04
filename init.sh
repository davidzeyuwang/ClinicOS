#!/usr/bin/env bash
# ClinicOS — Standard Session Startup
# Run from repo root: ./init.sh
# Checks environment, starts backend, runs smoke test.

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$REPO_ROOT/backend"

echo "=== ClinicOS init ==="

# 0. Load .env.local if present (contains SECRET_KEY and other local secrets)
if [ -f "$REPO_ROOT/.env.local" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env.local"
  set +a
fi
# Fallback if .env.local is missing or SECRET_KEY still not set
if [ -z "$SECRET_KEY" ]; then
  echo "WARNING: SECRET_KEY not found in .env.local — using ephemeral key (sessions won't survive restarts)"
  export SECRET_KEY="local-dev-ephemeral-$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
fi

# 1. Check Python
python3 --version || { echo "ERROR: python3 not found"; exit 1; }

# 2. Install deps (quiet, fast if already installed)
echo "--- Installing backend deps..."
pip install -q -r "$BACKEND/requirements.txt"

# 3. Check if server is already running
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  echo "--- Server already running at http://localhost:8000"
else
  echo "--- Starting uvicorn (background)..."
  cd "$BACKEND" && uvicorn app.main:app --port 8000 &
  UVICORN_PID=$!
  echo "    PID: $UVICORN_PID"

  # Wait for startup
  for i in {1..10}; do
    sleep 1
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
      echo "    Server ready."
      break
    fi
    echo "    Waiting... ($i/10)"
  done

  if ! curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: Server did not start. Check logs above."
    exit 1
  fi
fi

# 4. Reset and seed demo data (clear all + seed staff/rooms/patients)
echo "--- Resetting demo data..."
curl -sf -X POST http://localhost:8000/prototype/test/reset > /dev/null
echo "    Demo data seeded (staff, rooms, patients)."

# 6. Smoke test — verify the DB layer is working
echo "--- Running smoke tests..."
cd "$BACKEND" && python -m pytest tests/test_prototype_e2e.py -x -q --tb=short 2>&1 | tail -10

SMOKE_STATUS=${PIPESTATUS[0]}
if [ $SMOKE_STATUS -ne 0 ]; then
  echo ""
  echo "WARNING: Smoke tests failed. Fix before building on top of broken state."
  echo "Run: cd backend && python -m pytest tests/ -x -v"
  echo ""
else
  echo "--- All smoke tests passed."
fi

# 7. Print current milestone status
echo ""
echo "=== Current State ==="
echo "  Milestone: M1 — Operations Board"
echo "  Tasks:     tasks/tracker.md"
echo "  Features:  tasks/features.json (authoritative completion)"
echo "  UI:        http://localhost:8000/ui/index.html"
echo "  API docs:  http://localhost:8000/docs"
echo ""
echo "Next task: check tasks/features.json for first item with passes=false"
echo "Workflow:  docs/workflow/AGENT-SDLC.md"
echo ""
echo "=== Ready ==="
