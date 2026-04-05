"""Auth service: create/query users and clinics (SQLite mode)."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_utils import create_access_token
from app.auth.password import hash_password, verify_password
from app.models.tables import Clinic, User


def _new_id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def create_clinic(db: AsyncSession, name: str, slug: str, timezone_str: str = "America/New_York") -> Clinic:
    clinic = Clinic(
        clinic_id=_new_id(),
        name=name,
        slug=slug,
        timezone=timezone_str,
        is_active=True,
        created_at=_utc_now(),
    )
    db.add(clinic)
    await db.flush()
    return clinic


async def create_user(
    db: AsyncSession,
    clinic_id: str,
    email: str,
    plain_password: str,
    display_name: str = "",
    role: str = "frontdesk",
    username: Optional[str] = None,
) -> User:
    existing_email = await db.execute(select(User).where(User.email == email))
    if existing_email.scalar_one_or_none():
        raise ValueError("Email already exists")
    if username:
        existing_username = await db.execute(select(User).where(User.username == username))
        if existing_username.scalar_one_or_none():
            raise ValueError("Username already exists")
    user = User(
        user_id=_new_id(),
        clinic_id=clinic_id,
        email=email,
        username=username or None,
        hashed_password=hash_password(plain_password),
        display_name=display_name or email,
        role=role,
        is_active=True,
        created_at=_utc_now(),
    )
    db.add(user)
    await db.flush()
    return user


async def authenticate_user(db: AsyncSession, identifier: str, password: str) -> Optional[dict]:
    """Accept email or username as identifier. Return token dict on success, None on failure."""
    result = await db.execute(
        select(User).where(
            or_(User.email == identifier, User.username == identifier),
            User.is_active == True,
        )
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        return None
    token = create_access_token(
        {
            "sub": user.user_id,
            "clinic_id": user.clinic_id,
            "role": user.role,
            "display_name": user.display_name,
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 60 * 8 * 60,  # seconds
        "user_id": user.user_id,
        "clinic_id": user.clinic_id,
        "role": user.role,
        "display_name": user.display_name,
    }


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def list_users_by_clinic(db: AsyncSession, clinic_id: str) -> list[User]:
    result = await db.execute(
        select(User).where(User.clinic_id == clinic_id).order_by(User.created_at.asc(), User.email.asc())
    )
    return list(result.scalars().all())
