"""Pytest configuration — set required env vars before any app module is imported."""
import os

# Must be set before app.auth.jwt_utils is imported, or it raises RuntimeError.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use")
