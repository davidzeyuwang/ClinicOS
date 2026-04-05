"""Auth endpoints: login, me, register-clinic."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, get_current_user, require_role
from app.database import get_db, _IS_SUPABASE
from app.schemas.prototype import LoginRequest, RegisterClinicRequest, TokenResponse

if _IS_SUPABASE:
    from app.services import auth_service_supa as auth_service
else:
    from app.services import auth_service

router = APIRouter(prefix="/prototype/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not payload.email and not payload.username:
        raise HTTPException(status_code=422, detail="Provide email or username")
    result = await auth_service.authenticate_user(db, payload.identifier, payload.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


@router.get("/me")
async def me(current_user: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = await auth_service.get_user_by_id(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.user_id,
        "clinic_id": user.clinic_id,
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
    }


@router.post("/register-clinic")
async def register_clinic(
    payload: RegisterClinicRequest,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    # Duplicate slug check — SQLite uses SQLAlchemy; Supabase uses REST via auth_service
    if _IS_SUPABASE:
        from app.database import get_supabase
        supa = get_supabase()
        rows = await supa.select("clinics", {"slug": payload.slug})
        if rows:
            raise HTTPException(status_code=409, detail="Clinic slug already exists")
    else:
        from sqlalchemy import select
        from app.models.tables import Clinic
        existing = await db.execute(select(Clinic).where(Clinic.slug == payload.slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Clinic slug already exists")
    clinic = await auth_service.create_clinic(db, payload.clinic_name, payload.slug)
    user = await auth_service.create_user(
        db, clinic.clinic_id, payload.admin_email, payload.admin_password,
        display_name=payload.admin_display_name or payload.admin_email,
        role="admin",
        username=payload.admin_username or None,
    )
    if not _IS_SUPABASE:
        await db.commit()
    return {"clinic_id": clinic.clinic_id, "user_id": user.user_id}
