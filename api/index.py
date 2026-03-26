"""Vercel serverless entry point for ClinicOS FastAPI backend."""
import sys
import os
import socket

# Vercel Lambda does not support IPv6 outbound — force IPv4 for all connections
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

# Make `from app.xxx import ...` work inside the serverless function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: F401 — Vercel discovers the ASGI `app`
