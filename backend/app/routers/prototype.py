from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.prototype import (
    DailyReportGenerate,
    PatientCheckIn,
    PatientCheckout,
    RoomCreate,
    RoomStatusChange,
    RoomUpdate,
    ServiceEnd,
    ServiceStart,
    StaffCreate,
    StaffUpdate,
)
from app.services.prototype_store import prototype_store

router = APIRouter(prefix="/prototype", tags=["prototype"])


@router.post("/admin/rooms")
async def create_room(payload: RoomCreate):
    return prototype_store.create_room(actor_id="admin", data=payload.model_dump())


@router.patch("/admin/rooms/{room_id}")
async def update_room(room_id: str, payload: RoomUpdate):
    room = prototype_store.update_room(room_id=room_id, actor_id="admin", updates=payload.model_dump())
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("/admin/staff")
async def create_staff(payload: StaffCreate):
    return prototype_store.create_staff(actor_id="admin", data=payload.model_dump())


@router.patch("/admin/staff/{staff_id}")
async def update_staff(staff_id: str, payload: StaffUpdate):
    staff = prototype_store.update_staff(staff_id=staff_id, actor_id="admin", updates=payload.model_dump())
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff


@router.post("/portal/checkin")
async def patient_checkin(payload: PatientCheckIn):
    return prototype_store.patient_checkin(
        actor_id=payload.actor_id,
        patient_name=payload.patient_name,
        patient_ref=payload.patient_ref,
    )


@router.post("/portal/service/start")
async def service_start(payload: ServiceStart):
    visit = prototype_store.service_start(
        visit_id=payload.visit_id,
        actor_id=payload.actor_id,
        staff_id=payload.staff_id,
        room_id=payload.room_id,
        service_type=payload.service_type,
    )
    if not visit:
        raise HTTPException(status_code=404, detail="Visit, staff, or room not found")
    return visit


@router.post("/portal/service/end")
async def service_end(payload: ServiceEnd):
    visit = prototype_store.service_end(visit_id=payload.visit_id, actor_id=payload.actor_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found or service not started")
    return visit


@router.post("/portal/checkout")
async def patient_checkout(payload: PatientCheckout):
    visit = prototype_store.patient_checkout(visit_id=payload.visit_id, actor_id=payload.actor_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


@router.post("/portal/room-status")
async def change_room_status(payload: RoomStatusChange):
    room = prototype_store.change_room_status(
        room_id=payload.room_id,
        actor_id=payload.actor_id,
        status=payload.status,
    )
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.get("/projections/room-board")
async def get_room_board():
    return {"rooms": prototype_store.room_board()}


@router.get("/projections/staff-hours")
async def get_staff_hours():
    return {"staff": prototype_store.staff_hours_today()}


@router.post("/reports/daily/generate")
async def generate_daily_report(payload: DailyReportGenerate):
    report = prototype_store.generate_daily_report(actor_id=payload.actor_id, report_date=payload.date)
    return report


@router.get("/reports/daily")
async def get_daily_report(date: Optional[str] = None):
    report = prototype_store.get_daily_report(report_date=date)
    if not report:
        raise HTTPException(status_code=404, detail="No report generated for requested date")
    return report


@router.get("/events")
async def list_events():
    return {"count": len(prototype_store.events), "events": prototype_store.events}
