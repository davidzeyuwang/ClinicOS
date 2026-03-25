"""Vercel serverless entry point for ClinicOS FastAPI backend."""
import sys
import os

# Make `from app.xxx import ...` work inside the serverless function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: F401 — Vercel discovers the ASGI `app`
