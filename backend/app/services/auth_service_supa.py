"""Auth service — Supabase REST mode (production).

Mirrors auth_service.py interface but uses SupabaseClient instead of SQLAlchemy.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.auth.jwt_utils import create_access_token
from app.auth.password import hash_password, verify_password
from app.database import get_supabase


def _new_id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_clinic(db, name: str, slug: str, timezone_str: str = "America/New_York"):
    supa = get_supabase()
    row = await supa.insert("clinics", {
        "clinic_id": _new_id(),
        "name": name,
        "slug": slug,
        "timezone": timezone_str,
        "is_active": True,
    })
    return _ClinicProxy(row)


async def create_user(
    db,
    clinic_id: str,
    email: str,
    plain_password: str,
    display_name: str = "",
    role: str = "frontdesk",
    username: Optional[str] = None,
):
    supa = get_supabase()
    data = {
        "user_id": _new_id(),
        "clinic_id": clinic_id,
        "email": email,
        "hashed_password": hash_password(plain_password),
        "display_name": display_name or email,
        "role": role,
        "is_active": True,
    }
    if username:
        data["username"] = username
    row = await supa.insert("users", data)
    return _UserProxy(row)


async def authenticate_user(db, identifier: str, password: str) -> Optional[dict]:
    supa = get_supabase()
    # Try email first, then username
    rows = await supa.select("users", {"email": identifier, "is_active": True})
    if not rows:
        rows = await supa.select("users", {"username": identifier, "is_active": True})
    if not rows:
        return None
    user = rows[0]
    if not verify_password(password, user["hashed_password"]):
        return None
    token = create_access_token({
        "sub": user["user_id"],
        "clinic_id": user["clinic_id"],
        "role": user["role"],
        "display_name": user["display_name"],
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 60 * 8 * 60,
        "user_id": user["user_id"],
        "clinic_id": user["clinic_id"],
        "role": user["role"],
        "display_name": user["display_name"],
    }


async def get_user_by_id(db, user_id: str) -> Optional["_UserProxy"]:
    supa = get_supabase()
    rows = await supa.select("users", {"user_id": user_id})
    if not rows:
        return None
    return _UserProxy(rows[0])


class _ClinicProxy:
    """Dict-backed proxy matching the SQLAlchemy Clinic interface."""
    def __init__(self, row: dict):
        self._row = row

    @property
    def clinic_id(self) -> str:
        return self._row["clinic_id"]


class _UserProxy:
    """Dict-backed proxy matching the SQLAlchemy User interface."""
    def __init__(self, row: dict):
        self._row = row

    @property
    def user_id(self) -> str:
        return self._row["user_id"]

    @property
    def clinic_id(self) -> str:
        return self._row["clinic_id"]

    @property
    def email(self) -> str:
        return self._row["email"]

    @property
    def username(self) -> Optional[str]:
        return self._row.get("username")

    @property
    def display_name(self) -> str:
        return self._row.get("display_name", "")

    @property
    def role(self) -> str:
        return self._row["role"]
