"""
Security blocker regression tests.
Covers: BLOCKER-1, BLOCKER-2, BLOCKER-3, BLOCKER-4
See: docs/COMPLIANCE/002-pre-production-security-blockers.md
"""
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app, ALLOWED_ORIGINS

TEST_TOKEN_HEADER = {"x-test-token": "test-admin-secret-fixed-token"}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        c.post("/prototype/test/reset", headers=TEST_TOKEN_HEADER)
        yield c


# ── BLOCKER-1: Debug endpoints must not exist ─────────────────────────────────

def test_debug_db_endpoint_removed(client):
    """BLOCKER-1: /debug-db must not be reachable (was unauthenticated, leaked DB URL)."""
    r = client.get("/debug-db")
    assert r.status_code == 404, f"Expected 404 (removed), got {r.status_code}"


def test_debug_httpx_endpoint_removed(client):
    """BLOCKER-1: /prototype/debug/httpx-test must not be reachable (SSRF vector)."""
    r = client.get("/prototype/debug/httpx-test")
    assert r.status_code == 404, f"Expected 404 (removed), got {r.status_code}"


def test_debug_room_board_endpoint_removed(client):
    """BLOCKER-1: /prototype/debug/room-board-steps must not be reachable."""
    r = client.get("/prototype/debug/room-board-steps")
    assert r.status_code == 404, f"Expected 404 (removed), got {r.status_code}"


# ── BLOCKER-2: SECRET_KEY must be set — fail-fast if missing ─────────────────

def test_secret_key_is_set():
    """BLOCKER-2: SECRET_KEY env var must be present (conftest sets it for tests)."""
    assert os.environ.get("SECRET_KEY"), "SECRET_KEY must be set before the app loads"


def test_secret_key_is_not_default_insecure_value():
    """BLOCKER-2: SECRET_KEY must not be the old hardcoded fallback."""
    assert os.environ.get("SECRET_KEY") != "dev-secret-key-change-in-production", (
        "SECRET_KEY is still set to the insecure default"
    )


def test_missing_secret_key_raises_at_import():
    """BLOCKER-2: jwt_utils raises RuntimeError immediately if SECRET_KEY is absent."""
    import importlib
    import sys

    # Temporarily remove SECRET_KEY
    original = os.environ.pop("SECRET_KEY", None)
    # Remove cached module so it re-executes module-level code
    sys.modules.pop("app.auth.jwt_utils", None)
    try:
        with pytest.raises(RuntimeError, match="SECRET_KEY environment variable is not set"):
            import app.auth.jwt_utils  # noqa: F401
    finally:
        # Restore for remaining tests
        if original:
            os.environ["SECRET_KEY"] = original
        sys.modules.pop("app.auth.jwt_utils", None)
        import app.auth.jwt_utils  # reload with key restored


# ── BLOCKER-3: Password must not appear in seed log output ───────────────────

def test_seed_log_does_not_contain_password(capsys):
    """BLOCKER-3: Startup seed print must not include the admin password."""
    # Re-trigger the seed path by calling _seed_test_clinic directly
    import asyncio
    from app.main import _seed_test_clinic

    asyncio.get_event_loop().run_until_complete(_seed_test_clinic())
    captured = capsys.readouterr()
    # The seed is idempotent so it returns early if clinic exists — either way no password
    assert "test1234" not in captured.out, "Admin password must not appear in server logs"
    assert "test1234" not in captured.err, "Admin password must not appear in server logs"


# ── BLOCKER-4: CORS must use explicit origins, not wildcard ──────────────────

def test_cors_allowed_origins_is_not_wildcard():
    """BLOCKER-4: ALLOWED_ORIGINS must never contain bare '*'."""
    assert "*" not in ALLOWED_ORIGINS, (
        "CORS must not use wildcard origin when allow_credentials=True"
    )


def test_cors_allowed_origins_includes_localhost():
    """BLOCKER-4: localhost must be in the allowlist for local development."""
    assert "http://localhost:8000" in ALLOWED_ORIGINS


def test_cors_allowed_origins_includes_production():
    """BLOCKER-4: Production Vercel origin must be in the allowlist."""
    assert "https://clinicos-psi.vercel.app" in ALLOWED_ORIGINS


def test_cors_origin_not_allowed_returns_no_acao_header(client):
    """BLOCKER-4: Request from an unlisted origin must not receive ACAO header."""
    r = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers, (
        "Server must not echo back an unlisted origin in ACAO header"
    )


def test_cors_allowed_origin_gets_acao_header(client):
    """BLOCKER-4: Request from a listed origin must receive correct ACAO header."""
    r = client.get("/health", headers={"Origin": "http://localhost:8000"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:8000"
