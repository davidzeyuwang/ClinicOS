"""Clinic OS — Backend Application Entry Point.

Aligned with PRD v2.0 (PRD/003-clinic-os-prd-v2.md).
Event-sourced clinic operating system with CQRS (ADR-001).
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers.auth_routes import router as auth_router
from app.routers.db_routes import router as db_router

# Resolve frontend directory (../frontend relative to backend/)
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup and seed test clinic."""
    await init_db()
    await _seed_test_clinic()
    yield


async def _seed_test_clinic() -> None:
    """Idempotent: create default test clinic + admin user on first startup."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.tables import Clinic, User, _new_id, _utc_now
    from app.auth.password import hash_password

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(Clinic).where(Clinic.slug == "test"))
        if existing:
            return
        clinic = Clinic(
            clinic_id=_new_id(),
            name="Test Clinic",
            slug="test",
            timezone="America/New_York",
            is_active=True,
            created_at=_utc_now(),
        )
        db.add(clinic)
        await db.flush()
        user = User(
            user_id=_new_id(),
            clinic_id=clinic.clinic_id,
            username="admin@test.clinicos.local",
            hashed_password=hash_password("test1234"),
            display_name="Test Admin",
            role="admin",
            is_active=True,
            created_at=_utc_now(),
        )
        db.add(user)
        await db.commit()
        print(f"[seed] Test clinic created (id={clinic.clinic_id}), admin: admin@test.clinicos.local / test1234")


app = FastAPI(
    title="Clinic OS",
    description=(
        "Event-sourced clinic operating system — unified patient master, "
        "visit lifecycle, clinical notes, insurance/eligibility, "
        "document management, and task/case management. "
        "Aligned with PRD v2.0."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(db_router)


@app.get("/")
async def root():
    """Redirect root to frontend UI."""
    return RedirectResponse(url="/ui/index.html")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.3.0"}

@app.get("/debug-db")
async def debug_db():
    """Diagnose DB connectivity — remove after debugging."""
    import traceback
    from app.database import DATABASE_URL, _is_postgres, engine
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            return {"status": "ok", "db_type": "postgres" if _is_postgres else "sqlite", "url_prefix": DATABASE_URL[:40]}
    except Exception as e:
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()[-500:]}



# Serve frontend static files at /ui/*
if FRONTEND_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
