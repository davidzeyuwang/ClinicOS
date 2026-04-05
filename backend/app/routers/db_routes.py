"""API routes — dispatches to Supabase REST or SQLite based on env."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, get_current_user, require_role
from app.database import get_db, _IS_SUPABASE
from app.schemas.prototype import (
    AdminUserCreateRequest,
    AppointmentCreate,
    AppointmentUpdate,
    ClinicalNoteCreate,
    ClinicalNoteSign,
    ClinicalNoteUpdate,
    CreateTestUserRequest,
    DailyReportGenerate,
    DocumentCreate,
    DocumentSign,
    DocumentUpdate,
    InsurancePolicyCreate,
    InsurancePolicyUpdate,
    PatientCheckIn,
    PatientCheckout,
    PatientCreate,
    PatientUpdate,
    VisitPaymentSave,
    RoomCreate,
    RoomStatusChange,
    RoomUpdate,
    ServiceEnd,
    ServiceResume,
    ServiceStart,
    ServiceTypeCreate,
    ServiceTypeUpdate,
    StaffCreate,
    StaffUpdate,
    StaffServiceTypesSet,
    TaskCreate,
    TaskUpdate,
    TreatmentAdd,
    TreatmentUpdate,
    TreatmentRecordsFilter,
)

if _IS_SUPABASE:
    from app.services import db_service_supa as db_service
    from app.services import auth_service_supa as auth_service
else:
    from app.services import db_service
    from app.services import auth_service

router = APIRouter(prefix="/prototype", tags=["prototype"])



@router.post("/test/reset")
async def reset_test_data(
    x_test_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Reset local demo data for browser automation. Disabled on Supabase."""
    if _IS_SUPABASE:
        raise HTTPException(status_code=403, detail="Test reset is disabled outside local SQLite mode")
    expected = os.getenv("TEST_ADMIN_TOKEN", "test-admin-secret-fixed-token")
    if x_test_token != expected:
        raise HTTPException(status_code=401, detail="Invalid test token")
    await db_service.reset_demo_data(db)
    return {"ok": True}


@router.post("/test/create-user")
async def create_test_user(
    payload: CreateTestUserRequest,
    x_test_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a user in the test clinic for RBAC smoke testing. Local SQLite only."""
    if _IS_SUPABASE:
        raise HTTPException(status_code=403, detail="Test endpoint disabled in production")
    expected = os.getenv("TEST_ADMIN_TOKEN", "test-admin-secret-fixed-token")
    if x_test_token != expected:
        raise HTTPException(status_code=401, detail="Invalid test token")
    from sqlalchemy import select as sa_select
    from app.models.tables import Clinic
    from app.services import auth_service
    result = await db.execute(sa_select(Clinic).limit(1))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(status_code=500, detail="No clinic found — run /test/reset first")
    user = await auth_service.create_user(
        db, clinic.clinic_id, payload.email, payload.password,
        display_name=payload.display_name or payload.email,
        role=payload.role,
        username=payload.username or None,
    )
    await db.commit()
    return {"user_id": user.user_id, "clinic_id": user.clinic_id, "role": user.role}


# ==================== ADMIN ====================

@router.post("/admin/rooms")
async def create_room(
    payload: RoomCreate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await db_service.create_room(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump())


@router.patch("/admin/rooms/{room_id}")
async def update_room(
    room_id: str,
    payload: RoomUpdate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    room = await db_service.update_room(db, clinic_id=current_user["clinic_id"], room_id=room_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.delete("/admin/rooms/{room_id}")
async def delete_room(
    room_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db_service.delete_room(db, clinic_id=current_user["clinic_id"], room_id=room_id, actor_id=current_user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"deleted": True, "room": result}


@router.post("/admin/staff")
async def create_staff(
    payload: StaffCreate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    return await db_service.create_staff(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump())


@router.patch("/admin/staff/{staff_id}")
async def update_staff(
    staff_id: str,
    payload: StaffUpdate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    staff = await db_service.update_staff(db, clinic_id=current_user["clinic_id"], staff_id=staff_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.delete("/admin/staff/{staff_id}")
async def delete_staff(
    staff_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db_service.delete_staff(db, clinic_id=current_user["clinic_id"], staff_id=staff_id, actor_id=current_user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"deleted": True, "staff": result}


@router.get("/admin/users")
async def list_users(
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    users = await auth_service.list_users_by_clinic(db, current_user["clinic_id"])
    return {
        "users": [
            {
                "user_id": user.user_id,
                "clinic_id": user.clinic_id,
                "email": user.email,
                "username": user.username,
                "display_name": user.display_name,
                "role": user.role,
                "is_active": getattr(user, "is_active", True),
            }
            for user in users
        ]
    }


@router.post("/admin/users")
async def create_user(
    payload: AdminUserCreateRequest,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.create_user(
            db,
            current_user["clinic_id"],
            payload.email,
            payload.password,
            display_name=payload.display_name or payload.email,
            role=payload.role,
            username=payload.username or None,
        )
        if not _IS_SUPABASE:
            await db.commit()
    except ValueError as e:
        if not _IS_SUPABASE and db is not None:
            await db.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    return {
        "user_id": user.user_id,
        "clinic_id": user.clinic_id,
        "email": user.email,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": getattr(user, "is_active", True),
    }


@router.delete("/portal/visits/{visit_id}")
async def delete_visit(
    visit_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db_service.delete_visit(db, clinic_id=current_user["clinic_id"], visit_id=visit_id, actor_id=current_user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Visit not found")
    return {"deleted": True, "visit": result}


# ==================== PORTAL ====================

@router.post("/portal/checkin")
async def patient_checkin(
    payload: PatientCheckIn,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await db_service.patient_checkin(
        db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"],
        patient_name=payload.patient_name,
        patient_ref=payload.patient_ref,
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id,
    )


@router.post("/portal/service/start")
async def service_start(
    payload: ServiceStart,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        visit = await db_service.service_start(
            db, clinic_id=current_user["clinic_id"], visit_id=payload.visit_id, actor_id=current_user["user_id"],
            staff_id=payload.staff_id, room_id=payload.room_id,
            service_type=payload.service_type,
            supervising_staff_id=payload.supervising_staff_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not visit:
        raise HTTPException(status_code=404, detail="Visit, staff, or room not found")
    return visit


@router.post("/portal/service/end")
async def service_end(
    payload: ServiceEnd,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    visit = await db_service.service_end(db, clinic_id=current_user["clinic_id"], visit_id=payload.visit_id, actor_id=current_user["user_id"])
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found or service not started")
    return visit


@router.post("/portal/service/resume")
async def service_resume(
    payload: ServiceResume,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        visit = await db_service.service_resume(
            db, clinic_id=current_user["clinic_id"], visit_id=payload.visit_id, actor_id=current_user["user_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found or prior service details missing")
    return visit


@router.post("/portal/checkout")
async def patient_checkout(
    payload: PatientCheckout,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not payload.patient_signed:
        raise HTTPException(status_code=400, detail="Patient signature required before checkout")
    visit = await db_service.patient_checkout(
        db, clinic_id=current_user["clinic_id"], visit_id=payload.visit_id, actor_id=current_user["user_id"],
        payment_status=payload.payment_status,
        payment_amount=payload.payment_amount,
        payment_method=payload.payment_method,
        copay_collected=payload.copay_collected,
        wd_verified=payload.wd_verified,
        patient_signed=payload.patient_signed,
    )
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


@router.post("/portal/payment/save")
async def save_visit_payment(
    payload: VisitPaymentSave,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    visit = await db_service.save_visit_payment(
        db, clinic_id=current_user["clinic_id"], visit_id=payload.visit_id, actor_id=current_user["user_id"],
        payment_status=payload.payment_status,
        payment_amount=payload.payment_amount,
        payment_method=payload.payment_method,
        copay_collected=payload.copay_collected,
        wd_verified=payload.wd_verified,
        patient_signed=payload.patient_signed,
    )
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


@router.post("/portal/room-status")
async def change_room_status(
    payload: RoomStatusChange,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    room = await db_service.change_room_status(
        db, clinic_id=current_user["clinic_id"], room_id=payload.room_id, actor_id=current_user["user_id"], status=payload.status,
    )
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


# ==================== PROJECTIONS ====================

@router.get("/projections/room-board")
async def get_room_board(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        rooms = await db_service.get_room_board(db, clinic_id=current_user["clinic_id"])
        return {"rooms": rooms}
    except BaseException as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/projections/active-visits")
async def get_active_visits(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"visits": await db_service.get_active_visits(db, clinic_id=current_user["clinic_id"])}


@router.get("/visits/{visit_id}")
async def get_visit(
    visit_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    visit = await db_service.get_visit(db, clinic_id=current_user["clinic_id"], visit_id=visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


@router.get("/projections/daily-summary")
async def get_daily_summary(
    date: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await db_service.get_daily_summary(db, clinic_id=current_user["clinic_id"], date=date)


@router.get("/projections/staff-hours")
async def get_staff_hours(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"staff": await db_service.get_staff_hours(db, clinic_id=current_user["clinic_id"])}


# ==================== REPORTS ====================

@router.post("/reports/daily/generate")
async def generate_daily_report(
    payload: DailyReportGenerate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await db_service.generate_daily_report(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], report_date=payload.date)


@router.get("/reports/daily")
async def get_daily_report(
    date: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    report = await db_service.get_daily_report(db, clinic_id=current_user["clinic_id"], report_date=date)
    if not report:
        raise HTTPException(status_code=404, detail="No report generated for requested date")
    return report


# ==================== EVENTS ====================

@router.get("/events")
async def list_events(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await db_service.get_events(db, clinic_id=current_user["clinic_id"])


# ==================== PATIENTS (§11.1) ====================

@router.post("/patients")
async def create_patient(
    payload: PatientCreate,
    force: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        return await db_service.create_patient(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump(), force=force)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/patients")
async def list_patients(
    q: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if q:
        return {"patients": await db_service.search_patients(db, clinic_id=current_user["clinic_id"], query=q)}
    return {"patients": await db_service.list_patients(db, clinic_id=current_user["clinic_id"])}


@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    patient = await db_service.get_patient(db, patient_id, clinic_id=current_user["clinic_id"])
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.patch("/patients/{patient_id}")
async def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    patient = await db_service.update_patient(db, clinic_id=current_user["clinic_id"], patient_id=patient_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.delete("/patients/{patient_id}")
async def delete_patient(
    patient_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    patient = await db_service.delete_patient(db, clinic_id=current_user["clinic_id"], patient_id=patient_id, actor_id=current_user["user_id"])
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"deleted": True, "patient": patient}


@router.get("/patients/{patient_id}/visits")
async def get_patient_visits(
    patient_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"visits": await db_service.get_patient_visits(db, clinic_id=current_user["clinic_id"], patient_id=patient_id)}


@router.get("/patients/{patient_id}/sign-sheet.pdf")
async def get_patient_sign_sheet(
    patient_id: str,
    visit_ids: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a printable individual sign sheet PDF (个人签字表) for a patient.

    Args:
        patient_id: Patient ID
        visit_ids: Optional comma-separated list of visit IDs to include (default: all visits)
    """
    from app.services import pdf_service
    patient = await db_service.get_patient(db, patient_id, clinic_id=current_user["clinic_id"])
    if not patient:
        # Try searching by name if patient_id doesn't look like a UUID
        if len(patient_id) < 32 and '-' not in patient_id[:12]:
            try:
                matches = await db_service.search_patients(db, clinic_id=current_user["clinic_id"], query=patient_id)
                if matches:
                    patient = matches[0]
                    patient_id = patient["patient_id"]
            except Exception:
                pass
    if not patient:
        # Walk-in patient — build a minimal patient dict from visit data
        if visit_ids:
            selected_ids = set(visit_ids.split(','))
        else:
            selected_ids = None
        all_visits = await db_service.get_patient_visits(db, clinic_id=current_user["clinic_id"], patient_id=patient_id)
        if not all_visits:
            raise HTTPException(status_code=404, detail="Patient not found")
        visits = [v for v in all_visits if v.get('visit_id') in selected_ids] if selected_ids else all_visits
        patient = {
            "patient_id": patient_id,
            "first_name": all_visits[0].get("patient_name") or patient_id,
            "last_name": "",
            "full_name": all_visits[0].get("patient_name") or patient_id,
            "date_of_birth": None, "phone": None, "email": None, "mrn": None,
        }
        policies = []
    else:
        visits = await db_service.get_patient_visits(db, clinic_id=current_user["clinic_id"], patient_id=patient_id)
        if visit_ids:
            selected_ids = set(visit_ids.split(','))
            visits = [v for v in visits if v.get('visit_id') in selected_ids]
        policies = await db_service.list_insurance_policies(db, clinic_id=current_user["clinic_id"], patient_id=patient_id)
    pdf_bytes = pdf_service.generate_sign_sheet(patient, visits, policies)
    filename_suffix = f"_selected_{len(visits)}" if visit_ids else ""
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sign_sheet_{patient_id[:8]}{filename_suffix}.pdf"'},
    )


# ==================== APPOINTMENTS (§11.2) ====================

@router.post("/appointments")
async def create_appointment(
    payload: AppointmentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await db_service.create_appointment(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump())


@router.get("/appointments")
async def list_appointments(
    date: Optional[str] = None,
    patient_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"appointments": await db_service.list_appointments(db, clinic_id=current_user["clinic_id"], date=date, patient_id=patient_id, provider_id=provider_id)}


@router.patch("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appt = await db_service.update_appointment(db, clinic_id=current_user["clinic_id"], appointment_id=appointment_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    reason: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appt = await db_service.cancel_appointment(db, clinic_id=current_user["clinic_id"], appointment_id=appointment_id, actor_id=current_user["user_id"], reason=reason)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.post("/appointments/{appointment_id}/no-show")
async def mark_no_show(
    appointment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    appt = await db_service.mark_no_show(db, clinic_id=current_user["clinic_id"], appointment_id=appointment_id, actor_id=current_user["user_id"])
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


# ==================== CLINICAL NOTES (§11.6) ====================

@router.post("/notes")
async def create_note(
    payload: ClinicalNoteCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await db_service.create_note(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump())


@router.get("/notes")
async def list_notes(
    visit_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"notes": await db_service.list_notes(db, clinic_id=current_user["clinic_id"], visit_id=visit_id, patient_id=patient_id)}


@router.patch("/notes/{note_id}")
async def update_note(
    note_id: str,
    payload: ClinicalNoteUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db_service.update_note(db, clinic_id=current_user["clinic_id"], note_id=note_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/notes/{note_id}/sign")
async def sign_note(
    note_id: str,
    payload: ClinicalNoteSign,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db_service.sign_note(db, clinic_id=current_user["clinic_id"], note_id=note_id, actor_id=payload.actor_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


# ==================== INSURANCE (§11.7) ====================

@router.post("/insurance")
async def create_insurance_policy(
    payload: InsurancePolicyCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await db_service.create_insurance_policy(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump())


@router.get("/insurance/{patient_id}")
async def list_insurance_policies(
    patient_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"policies": await db_service.list_insurance_policies(db, clinic_id=current_user["clinic_id"], patient_id=patient_id)}


@router.patch("/insurance/{policy_id}/update")
async def update_insurance_policy(
    policy_id: str,
    payload: InsurancePolicyUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    policy = await db_service.update_insurance_policy(db, clinic_id=current_user["clinic_id"], policy_id=policy_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not policy:
        raise HTTPException(status_code=404, detail="Insurance policy not found")
    return policy


# ==================== DOCUMENTS (§11.4) ====================

@router.post("/documents")
async def create_document(
    payload: DocumentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await db_service.create_document(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump())


@router.get("/documents/{patient_id}")
async def list_documents(
    patient_id: str,
    document_type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"documents": await db_service.list_documents(db, clinic_id=current_user["clinic_id"], patient_id=patient_id, document_type=document_type)}


@router.patch("/documents/{document_id}/update")
async def update_document(
    document_id: str,
    payload: DocumentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db_service.update_document(db, clinic_id=current_user["clinic_id"], document_id=document_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/documents/{document_id}/sign")
async def sign_document(
    document_id: str,
    payload: DocumentSign,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db_service.sign_document(db, clinic_id=current_user["clinic_id"], document_id=document_id, actor_id=payload.actor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# ==================== TASKS (§11.9) ====================

@router.post("/tasks")
async def create_task(
    payload: TaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await db_service.create_task(db, clinic_id=current_user["clinic_id"], actor_id=current_user["user_id"], data=payload.model_dump())


@router.get("/tasks")
async def list_tasks(
    patient_id: Optional[str] = None,
    assignee_id: Optional[str] = None,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"tasks": await db_service.list_tasks(db, clinic_id=current_user["clinic_id"], patient_id=patient_id, assignee_id=assignee_id, status=status, task_type=task_type)}


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db_service.update_task(db, clinic_id=current_user["clinic_id"], task_id=task_id, actor_id=current_user["user_id"], updates=payload.model_dump(exclude_none=True))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ==================== TREATMENTS (PRD-005) ====================

@router.post("/visits/{visit_id}/treatments/add")
async def add_treatment_to_visit(
    visit_id: str,
    payload: TreatmentAdd,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a treatment modality to an active visit."""
    try:
        return await db_service.add_treatment(
            db,
            clinic_id=current_user["clinic_id"],
            visit_id=visit_id,
            modality=payload.modality,
            actor_id=payload.actor_id or current_user["user_id"],
            therapist_id=payload.therapist_id,
            duration_minutes=payload.duration_minutes,
            notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/visits/{visit_id}/treatments")
async def get_visit_treatments(
    visit_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all treatments for a visit."""
    return {"treatments": await db_service.list_visit_treatments(db, clinic_id=current_user["clinic_id"], visit_id=visit_id)}


@router.patch("/visits/{visit_id}/treatments/{treatment_id}/update")
async def update_treatment(
    visit_id: str,
    treatment_id: str,
    payload: TreatmentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update treatment duration and notes."""
    try:
        return await db_service.update_treatment(
            db,
            clinic_id=current_user["clinic_id"],
            treatment_id=treatment_id,
            actor_id=current_user["user_id"],
            duration_minutes=payload.duration_minutes,
            notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/visits/{visit_id}/treatments/{treatment_id}/delete")
async def delete_treatment(
    visit_id: str,
    treatment_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a treatment from a visit."""
    try:
        return await db_service.delete_treatment(db, clinic_id=current_user["clinic_id"], treatment_id=treatment_id, actor_id=current_user["user_id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/treatment-records")
async def get_treatment_records(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    modality: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query all treatments with filters."""
    return {
        "treatments": await db_service.list_treatment_records(
            db,
            clinic_id=current_user["clinic_id"],
            date_from=date_from,
            date_to=date_to,
            patient_id=patient_id,
            staff_id=staff_id,
            modality=modality
        )
    }


@router.get("/visit-records")
async def get_visit_records(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return visits grouped with treatments organized by modality (A/PT/CP/TN) for 诊疗记录表 view."""
    return {
        "visits": await db_service.list_visits_with_treatments(
            db,
            clinic_id=current_user["clinic_id"],
            date_from=date_from,
            date_to=date_to,
            patient_id=patient_id,
            staff_id=staff_id,
        )
    }


# ==================== SERVICE TYPES ====================

@router.get("/admin/service-types")
async def list_service_types(
    include_inactive: bool = False,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all service types (active only by default)."""
    return {"service_types": await db_service.list_service_types(db, include_inactive=include_inactive)}


@router.post("/admin/service-types", status_code=201)
async def create_service_type(
    payload: ServiceTypeCreate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new service type."""
    return await db_service.create_service_type(db, actor_id=current_user["user_id"], name=payload.name)


@router.patch("/admin/service-types/{service_type_id}")
async def update_service_type(
    service_type_id: str,
    payload: ServiceTypeUpdate,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update name or active status of a service type."""
    result = await db_service.update_service_type(
        db, service_type_id=service_type_id, actor_id=current_user["user_id"],
        updates=payload.model_dump(exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Service type not found")
    return result


@router.delete("/admin/service-types/{service_type_id}", status_code=204)
async def retire_service_type(
    service_type_id: str,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Retire (soft-delete) a service type by setting is_active=False."""
    result = await db_service.update_service_type(
        db, service_type_id=service_type_id, actor_id=current_user["user_id"], updates={"is_active": False}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Service type not found")


@router.get("/admin/staff/{staff_id}/service-types")
async def get_staff_service_types(
    staff_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get service types a staff member is qualified to perform."""
    return {"service_types": await db_service.get_staff_service_types(db, staff_id=staff_id)}


@router.put("/admin/staff/{staff_id}/service-types")
async def set_staff_service_types(
    staff_id: str,
    payload: StaffServiceTypesSet,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Replace-all: set the exact list of service types a staff member is qualified for."""
    try:
        return await db_service.set_staff_service_types(
            db, clinic_id=current_user["clinic_id"], staff_id=staff_id,
            service_type_ids=payload.service_type_ids,
            actor_id=current_user["user_id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/admin/service-types/{service_type_id}/staff")
async def get_service_type_staff(
    service_type_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get staff qualified to perform a given service type."""
    return {"staff": await db_service.get_service_type_staff(db, service_type_id=service_type_id)}
