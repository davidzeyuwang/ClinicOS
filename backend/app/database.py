"""Database configuration and session management."""
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

_raw = os.getenv("DATABASE_URL", "")
if _raw.startswith("postgres://"):
    _raw = _raw.replace("postgres://", "postgresql+psycopg://", 1)
elif _raw.startswith("postgresql://") and "+psycopg" not in _raw and "+asyncpg" not in _raw:
    _raw = _raw.replace("postgresql://", "postgresql+psycopg://", 1)
elif _raw.startswith("postgresql+asyncpg://"):
    _raw = _raw.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

DATABASE_URL = _raw if _raw else "sqlite+aiosqlite:///./clinicos.db"
_is_postgres = DATABASE_URL.startswith("postgresql")

# psycopg3 accepts sslmode via connect_args
_connect_args = {"sslmode": "require"} if _is_postgres else {}

engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    if not _is_postgres:
        async with engine.begin() as conn:
            from app.models.tables import Base as _  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
