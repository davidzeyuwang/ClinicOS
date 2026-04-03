"""API routes — dispatches to Supabase REST or SQLite based on env."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, _IS_SUPABASE
from app.schemas.prototype import (
    AppointmentCreate,
    AppointmentUpdate,
    ClinicalNoteCreate,
    ClinicalNoteSign,
    ClinicalNoteUpdate,
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
    RoomCreate,
    RoomStatusChange,
    RoomUpdate,
    ServiceEnd,
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
else:
    from app.services import db_service

router = APIRouter(prefix="/prototype", tags=["prototype"])


@router.get("/debug/httpx-test")
async def httpx_test():
    """Test endpoint to verify httpx works in Lambda."""
    try:
        import httpx
        client = httpx.AsyncClient()
        resp = await client.get("https://httpbin.org/get")
        await client.aclose()
        return {"status": "ok", "httpx_version": httpx.__version__, "test_status": resp.status_code}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/debug/room-board-steps")
async def room_board_debug():
    """Debug endpoint: test each step of get_room_board separately."""
    if not _IS_SUPABASE:
        return {"skip": "only relevant in Supabase mode"}
    from app.database import get_supabase
    results = {}
    try:
        supa = get_supabase()
        results["client_created"] = True
    except BaseException as e:
        results["client_error"] = str(e)
        return results
    try:
        rooms = await supa.select("rooms", {"active": True})
        results["rooms_count"] = len(rooms)
    except BaseException as e:
        results["rooms_error"] = f"{type(e).__name__}: {e}"
        return results
    try:
        visits = await supa.select("visits", {})
        results["visits_count"] = len(visits)
    except BaseException as e:
        results["visits_error"] = f"{type(e).__name__}: {e}"
        return results
    results["status"] = "both queries succeeded"
    return results


@router.post("/test/reset")
async def reset_test_data(db: AsyncSession = Depends(get_db)):
    """Reset local demo data for browser automation. Disabled on Supabase."""
    if _IS_SUPABASE:
        raise HTTPException(status_code=403, detail="Test reset is disabled outside local SQLite mode")
    await db_service.reset_demo_data(db)
    return {"ok": True}


# ==================== ADMIN ====================

@router.post("/admin/rooms")
async def create_room(payload: RoomCreate, db: AsyncSession = Depends(get_db)):
    return await db_service.create_room(db, actor_id="admin", data=payload.model_dump())


@router.patch("/admin/rooms/{room_id}")
async def update_room(room_id: str, payload: RoomUpdate, db: AsyncSession = Depends(get_db)):
    room = await db_service.update_room(db, room_id=room_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.delete("/admin/rooms/{room_id}")
async def delete_room(room_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db_service.delete_room(db, room_id=room_id, actor_id="admin")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"deleted": True, "room": result}


@router.post("/admin/staff")
async def create_staff(payload: StaffCreate, db: AsyncSession = Depends(get_db)):
    return await db_service.create_staff(db, actor_id="admin", data=payload.model_dump())


@router.patch("/admin/staff/{staff_id}")
async def update_staff(staff_id: str, payload: StaffUpdate, db: AsyncSession = Depends(get_db)):
    staff = await db_service.update_staff(db, staff_id=staff_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.delete("/admin/staff/{staff_id}")
async def delete_staff(staff_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db_service.delete_staff(db, staff_id=staff_id, actor_id="admin")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"deleted": True, "staff": result}


@router.delete("/portal/visits/{visit_id}")
async def delete_visit(visit_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await db_service.delete_visit(db, visit_id=visit_id, actor_id="admin")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Visit not found")
    return {"deleted": True, "visit": result}


# ==================== PORTAL ====================

@router.post("/portal/checkin")
async def patient_checkin(payload: PatientCheckIn, db: AsyncSession = Depends(get_db)):
    return await db_service.patient_checkin(
        db, actor_id=payload.actor_id,
        patient_name=payload.patient_name,
        patient_ref=payload.patient_ref,
        patient_id=payload.patient_id,
        appointment_id=payload.appointment_id,
    )


@router.post("/portal/service/start")
async def service_start(payload: ServiceStart, db: AsyncSession = Depends(get_db)):
    try:
        visit = await db_service.service_start(
            db, visit_id=payload.visit_id, actor_id=payload.actor_id,
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
async def service_end(payload: ServiceEnd, db: AsyncSession = Depends(get_db)):
    visit = await db_service.service_end(db, visit_id=payload.visit_id, actor_id=payload.actor_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found or service not started")
    return visit


@router.post("/portal/checkout")
async def patient_checkout(payload: PatientCheckout, db: AsyncSession = Depends(get_db)):
    visit = await db_service.patient_checkout(
        db, visit_id=payload.visit_id, actor_id=payload.actor_id,
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
async def change_room_status(payload: RoomStatusChange, db: AsyncSession = Depends(get_db)):
    room = await db_service.change_room_status(
        db, room_id=payload.room_id, actor_id=payload.actor_id, status=payload.status,
    )
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


# ==================== PROJECTIONS ====================

@router.get("/projections/room-board")
async def get_room_board(db: AsyncSession = Depends(get_db)):
    try:
        rooms = await db_service.get_room_board(db)
        return {"rooms": rooms}
    except BaseException as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@router.get("/projections/active-visits")
async def get_active_visits(db: AsyncSession = Depends(get_db)):
    return {"visits": await db_service.get_active_visits(db)}


@router.get("/projections/daily-summary")
async def get_daily_summary(date: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return await db_service.get_daily_summary(db, date=date)


@router.get("/projections/staff-hours")
async def get_staff_hours(db: AsyncSession = Depends(get_db)):
    return {"staff": await db_service.get_staff_hours(db)}


# ==================== REPORTS ====================

@router.post("/reports/daily/generate")
async def generate_daily_report(payload: DailyReportGenerate, db: AsyncSession = Depends(get_db)):
    return await db_service.generate_daily_report(db, actor_id=payload.actor_id, report_date=payload.date)


@router.get("/reports/daily")
async def get_daily_report(date: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    report = await db_service.get_daily_report(db, report_date=date)
    if not report:
        raise HTTPException(status_code=404, detail="No report generated for requested date")
    return report


# ==================== EVENTS ====================

@router.get("/events")
async def list_events(db: AsyncSession = Depends(get_db)):
    return await db_service.get_events(db)


# ==================== PATIENTS (§11.1) ====================

@router.post("/patients")
async def create_patient(payload: PatientCreate, force: bool = False, db: AsyncSession = Depends(get_db)):
    try:
        return await db_service.create_patient(db, actor_id="admin", data=payload.model_dump(), force=force)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/patients")
async def list_patients(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if q:
        return {"patients": await db_service.search_patients(db, query=q)}
    return {"patients": await db_service.list_patients(db)}


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    patient = await db_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.patch("/patients/{patient_id}")
async def update_patient(patient_id: str, payload: PatientUpdate, db: AsyncSession = Depends(get_db)):
    patient = await db_service.update_patient(db, patient_id=patient_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    patient = await db_service.delete_patient(db, patient_id=patient_id, actor_id="admin")
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"deleted": True, "patient": patient}


@router.get("/patients/{patient_id}/visits")
async def get_patient_visits(patient_id: str, db: AsyncSession = Depends(get_db)):
    return {"visits": await db_service.get_patient_visits(db, patient_id=patient_id)}


@router.get("/patients/{patient_id}/sign-sheet.pdf")
async def get_patient_sign_sheet(
    patient_id: str, 
    visit_ids: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Generate a printable individual sign sheet PDF (个人签字表) for a patient.
    
    Args:
        patient_id: Patient ID
        visit_ids: Optional comma-separated list of visit IDs to include (default: all visits)
    """
    from app.services import pdf_service
    patient = await db_service.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    visits = await db_service.get_patient_visits(db, patient_id=patient_id)
    
    # Filter visits if visit_ids provided
    if visit_ids:
        selected_ids = set(visit_ids.split(','))
        visits = [v for v in visits if v.get('visit_id') in selected_ids]
    
    policies = await db_service.list_insurance_policies(db, patient_id=patient_id)
    pdf_bytes = pdf_service.generate_sign_sheet(patient, visits, policies)
    filename_suffix = f"_selected_{len(visits)}" if visit_ids else ""
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sign_sheet_{patient_id[:8]}{filename_suffix}.pdf"'},
    )


# ==================== APPOINTMENTS (§11.2) ====================

@router.post("/appointments")
async def create_appointment(payload: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    return await db_service.create_appointment(db, actor_id="admin", data=payload.model_dump())


@router.get("/appointments")
async def list_appointments(date: Optional[str] = None, patient_id: Optional[str] = None,
                            provider_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return {"appointments": await db_service.list_appointments(db, date=date, patient_id=patient_id, provider_id=provider_id)}


@router.patch("/appointments/{appointment_id}")
async def update_appointment(appointment_id: str, payload: AppointmentUpdate, db: AsyncSession = Depends(get_db)):
    appt = await db_service.update_appointment(db, appointment_id=appointment_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str, reason: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    appt = await db_service.cancel_appointment(db, appointment_id=appointment_id, actor_id="admin", reason=reason)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.post("/appointments/{appointment_id}/no-show")
async def mark_no_show(appointment_id: str, db: AsyncSession = Depends(get_db)):
    appt = await db_service.mark_no_show(db, appointment_id=appointment_id, actor_id="admin")
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


# ==================== CLINICAL NOTES (§11.6) ====================

@router.post("/notes")
async def create_note(payload: ClinicalNoteCreate, db: AsyncSession = Depends(get_db)):
    return await db_service.create_note(db, actor_id="admin", data=payload.model_dump())


@router.get("/notes")
async def list_notes(visit_id: Optional[str] = None, patient_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return {"notes": await db_service.list_notes(db, visit_id=visit_id, patient_id=patient_id)}


@router.patch("/notes/{note_id}")
async def update_note(note_id: str, payload: ClinicalNoteUpdate, db: AsyncSession = Depends(get_db)):
    note = await db_service.update_note(db, note_id=note_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.post("/notes/{note_id}/sign")
async def sign_note(note_id: str, payload: ClinicalNoteSign, db: AsyncSession = Depends(get_db)):
    note = await db_service.sign_note(db, note_id=note_id, actor_id=payload.actor_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


# ==================== INSURANCE (§11.7) ====================

@router.post("/insurance")
async def create_insurance_policy(payload: InsurancePolicyCreate, db: AsyncSession = Depends(get_db)):
    return await db_service.create_insurance_policy(db, actor_id="admin", data=payload.model_dump())


@router.get("/insurance/{patient_id}")
async def list_insurance_policies(patient_id: str, db: AsyncSession = Depends(get_db)):
    return {"policies": await db_service.list_insurance_policies(db, patient_id=patient_id)}


@router.patch("/insurance/{policy_id}/update")
async def update_insurance_policy(policy_id: str, payload: InsurancePolicyUpdate, db: AsyncSession = Depends(get_db)):
    policy = await db_service.update_insurance_policy(db, policy_id=policy_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not policy:
        raise HTTPException(status_code=404, detail="Insurance policy not found")
    return policy


# ==================== DOCUMENTS (§11.4) ====================

@router.post("/documents")
async def create_document(payload: DocumentCreate, db: AsyncSession = Depends(get_db)):
    return await db_service.create_document(db, actor_id="admin", data=payload.model_dump())


@router.get("/documents/{patient_id}")
async def list_documents(patient_id: str, document_type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    return {"documents": await db_service.list_documents(db, patient_id=patient_id, document_type=document_type)}


@router.patch("/documents/{document_id}/update")
async def update_document(document_id: str, payload: DocumentUpdate, db: AsyncSession = Depends(get_db)):
    doc = await db_service.update_document(db, document_id=document_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/documents/{document_id}/sign")
async def sign_document(document_id: str, payload: DocumentSign, db: AsyncSession = Depends(get_db)):
    doc = await db_service.sign_document(db, document_id=document_id, actor_id=payload.actor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# ==================== TASKS (§11.9) ====================

@router.post("/tasks")
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await db_service.create_task(db, actor_id="admin", data=payload.model_dump())


@router.get("/tasks")
async def list_tasks(patient_id: Optional[str] = None, assignee_id: Optional[str] = None,
                     status: Optional[str] = None, task_type: Optional[str] = None,
                     db: AsyncSession = Depends(get_db)):
    return {"tasks": await db_service.list_tasks(db, patient_id=patient_id, assignee_id=assignee_id, status=status, task_type=task_type)}


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db_service.update_task(db, task_id=task_id, actor_id="admin", updates=payload.model_dump(exclude_none=True))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ==================== TREATMENTS (PRD-005) ====================

@router.post("/visits/{visit_id}/treatments/add")
async def add_treatment_to_visit(visit_id: str, payload: TreatmentAdd, db: AsyncSession = Depends(get_db)):
    """Add a treatment modality to an active visit."""
    try:
        return await db_service.add_treatment(
            db,
            visit_id=visit_id,
            modality=payload.modality,
            actor_id=payload.actor_id,
            therapist_id=payload.therapist_id,
            duration_minutes=payload.duration_minutes,
            notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/visits/{visit_id}/treatments")
async def get_visit_treatments(visit_id: str, db: AsyncSession = Depends(get_db)):
    """List all treatments for a visit."""
    return {"treatments": await db_service.list_visit_treatments(db, visit_id=visit_id)}


@router.patch("/visits/{visit_id}/treatments/{treatment_id}/update")
async def update_treatment(visit_id: str, treatment_id: str, payload: TreatmentUpdate, db: AsyncSession = Depends(get_db)):
    """Update treatment duration and notes."""
    try:
        return await db_service.update_treatment(
            db,
            treatment_id=treatment_id,
            actor_id="admin",  # TODO: get from auth context
            duration_minutes=payload.duration_minutes,
            notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/visits/{visit_id}/treatments/{treatment_id}/delete")
async def delete_treatment(visit_id: str, treatment_id: str, db: AsyncSession = Depends(get_db)):
    """Remove a treatment from a visit."""
    try:
        return await db_service.delete_treatment(db, treatment_id=treatment_id, actor_id="admin")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/treatment-records")
async def get_treatment_records(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    modality: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Query all treatments with filters."""
    return {
        "treatments": await db_service.list_treatment_records(
            db,
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
    db: AsyncSession = Depends(get_db),
):
    """Return visits grouped with treatments organized by modality (A/PT/CP/TN) for 诊疗记录表 view."""
    return {
        "visits": await db_service.list_visits_with_treatments(
            db,
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
    db: AsyncSession = Depends(get_db),
):
    """List all service types (active only by default)."""
    return {"service_types": await db_service.list_service_types(db, include_inactive=include_inactive)}


@router.post("/admin/service-types", status_code=201)
async def create_service_type(payload: ServiceTypeCreate, db: AsyncSession = Depends(get_db)):
    """Create a new service type."""
    return await db_service.create_service_type(db, actor_id="admin", name=payload.name)


@router.patch("/admin/service-types/{service_type_id}")
async def update_service_type(
    service_type_id: str, payload: ServiceTypeUpdate, db: AsyncSession = Depends(get_db)
):
    """Update name or active status of a service type."""
    result = await db_service.update_service_type(
        db, service_type_id=service_type_id, actor_id="admin",
        updates=payload.model_dump(exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Service type not found")
    return result


@router.delete("/admin/service-types/{service_type_id}", status_code=204)
async def retire_service_type(service_type_id: str, db: AsyncSession = Depends(get_db)):
    """Retire (soft-delete) a service type by setting is_active=False."""
    result = await db_service.update_service_type(
        db, service_type_id=service_type_id, actor_id="admin", updates={"is_active": False}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Service type not found")


@router.get("/admin/staff/{staff_id}/service-types")
async def get_staff_service_types(staff_id: str, db: AsyncSession = Depends(get_db)):
    """Get service types a staff member is qualified to perform."""
    return {"service_types": await db_service.get_staff_service_types(db, staff_id=staff_id)}


@router.put("/admin/staff/{staff_id}/service-types")
async def set_staff_service_types(
    staff_id: str, payload: StaffServiceTypesSet, db: AsyncSession = Depends(get_db)
):
    """Replace-all: set the exact list of service types a staff member is qualified for."""
    try:
        return await db_service.set_staff_service_types(
            db, staff_id=staff_id,
            service_type_ids=payload.service_type_ids,
            actor_id="admin",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/admin/service-types/{service_type_id}/staff")
async def get_service_type_staff(service_type_id: str, db: AsyncSession = Depends(get_db)):
    """Get staff qualified to perform a given service type."""
    return {"staff": await db_service.get_service_type_staff(db, service_type_id=service_type_id)}
