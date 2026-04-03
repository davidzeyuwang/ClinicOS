"""
Database layer.
- In production (Supabase): uses REST API via httpx (HTTPS only, Vercel-safe)
- Locally: falls back to SQLite via SQLAlchemy for development
"""
import os
from typing import Optional, Any

_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
_IS_SUPABASE = bool(_SUPABASE_URL and _SUPABASE_KEY)

# ── Local SQLite path (dev only) ──────────────────────────────────────────────
if not _IS_SUPABASE:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.orm import DeclarativeBase

    DATABASE_URL = "sqlite+aiosqlite:///./clinicos.db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    class Base(DeclarativeBase):
        pass

    async def get_db():
        async with async_session() as session:
            yield session

    async def init_db():
        async with engine.begin() as conn:
            from app.models.tables import Base as _  # noqa
            await conn.run_sync(Base.metadata.create_all)
            # Incremental migrations — safe to re-run (ignored if column exists)
            migrations = [
                "ALTER TABLE visits ADD COLUMN supervising_staff_id VARCHAR(36)",
            ]
            for sql in migrations:
                try:
                    await conn.execute(__import__("sqlalchemy").text(sql))
                except Exception:
                    pass  # column already exists
        from app.services.db_service import ensure_default_demo_staff
        async with async_session() as session:
            await ensure_default_demo_staff(session)

# ── Supabase REST helper ───────────────────────────────────────────────────────
class SupabaseClient:
    """Minimal async Supabase REST client using httpx."""

    def __init__(self):
        self._url = _SUPABASE_URL.rstrip("/")
        self._headers = {
            "apikey": _SUPABASE_KEY,
            "Authorization": f"Bearer {_SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        self._client = None  # Lazy init to avoid serverless issues

    def _get_client(self):
        """Lazy initialize httpx client to avoid Lambda freeze/thaw issues."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(headers=self._headers, timeout=10)
        return self._client

    async def select(self, table: str, filters: dict = None, limit: int = 1000, status_in: list = None) -> list:
        """Select with optional status_in for multi-value filtering (avoids fetching all rows)."""
        params = {"select": "*", "limit": limit}
        if filters:
            for k, v in filters.items():
                # PostgREST requires lowercase 'true'/'false' for booleans
                if isinstance(v, bool):
                    v = "true" if v else "false"
                params[k] = f"eq.{v}"
        if status_in:
            # Supabase PostgREST syntax: status=in.("value1","value2","value3")
            quoted_values = ','.join(f'"{s}"' for s in status_in)
            params["status"] = f"in.({quoted_values})"
        r = await self._get_client().get(f"{self._url}/rest/v1/{table}", params=params)
        r.raise_for_status()
        return r.json()

    async def insert(self, table: str, data: dict) -> dict:
        r = await self._get_client().post(f"{self._url}/rest/v1/{table}", json=data)
        r.raise_for_status()
        result = r.json()
        return result[0] if isinstance(result, list) else result

    async def update(self, table: str, pk_col: str, pk_val: str, data: dict) -> dict:
        params = {pk_col: f"eq.{pk_val}"}
        # Filter out None values for Supabase compatibility
        filtered_data = {k: v for k, v in data.items() if v is not None}
        r = await self._get_client().patch(f"{self._url}/rest/v1/{table}", params=params, json=filtered_data)
        r.raise_for_status()
        result = r.json()
        return result[0] if isinstance(result, list) and result else data

    async def delete(self, table: str, pk_col: str, pk_val: str) -> None:
        params = {pk_col: f"eq.{pk_val}"}
        r = await self._get_client().delete(f"{self._url}/rest/v1/{table}", params=params)
        r.raise_for_status()

    async def rpc(self, func: str, params: dict = None) -> Any:
        r = await self._get_client().post(f"{self._url}/rest/v1/rpc/{func}", json=params or {})
        r.raise_for_status()
        return r.json()


# Don't use singleton in serverless - create new client each time
def get_supabase() -> "SupabaseClient":
    """Get Supabase client - creates new instance each time for serverless safety."""
    return SupabaseClient()

# ── Compat shim: get_db yields None in Supabase mode (not used) ──────────────
async def get_db():
    if _IS_SUPABASE:
        yield None
    else:
        async with async_session() as session:
            yield session

async def init_db():
    if not _IS_SUPABASE:
        async with engine.begin() as conn:
            from app.models.tables import Base as _  # noqa
            await conn.run_sync(Base.metadata.create_all)
        from app.services.db_service import ensure_default_demo_staff, ensure_default_service_types
        async with async_session() as session:
            await ensure_default_demo_staff(session)
            await ensure_default_service_types(session)
