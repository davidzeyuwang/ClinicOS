#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/backend"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  PYTHON_BIN="$(command -v python)"
fi

export PYTHONPATH="$ROOT_DIR/backend"
export SUPABASE_URL=""
export SUPABASE_SERVICE_KEY=""

exec "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
