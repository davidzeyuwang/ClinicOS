"""Database-backed service layer — aligned with PRD v2.0 domain model."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, or_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import (
    Appointment, ClinicalNote, DailyReport, Document, EventLog,
    InsurancePolicy, Patient, Room, Staff, Task, Visit, VisitTreatment,
)


DEFAULT_STAFF = (
    {"name": "Alice PT",    "role": "therapist",  "license_id": "PT-001"},
    {"name": "Sylvia Chen", "role": "therapist",  "license_id": "PT-002"},
    {"name": "Dr. Gao",     "role": "therapist",  "license_id": "MD-001"},
    {"name": "Xu",          "role": "therapist",  "license_id": "PT-003"},
    {"name": "Front Desk",  "role": "front_desk", "license_id": None},
)

DEFAULT_ROOMS = (
    {"name": "Room A", "code": "A", "room_type": "treatment"},
    {"name": "Room B", "code": "B", "room_type": "treatment"},
    {"name": "Room C", "code": "C", "room_type": "treatment"},
    {"name": "Room D", "code": "D", "room_type": "treatment"},
)

DEFAULT_PATIENTS = (
    {"first_name": "Demo",   "last_name": "Patient",  "phone": "555-0001", "mrn": "MRN-DEMO-1"},
    {"first_name": "Walk-in","last_name": "Example",  "phone": "555-0002", "mrn": "MRN-DEMO-2"},
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


async def _append_event(db: AsyncSession, event_type: str, actor_id: str, payload: dict) -> EventLog:
    """Append an immutable event to the event log."""
    event = EventLog(
        event_id=_new_id(),
        event_type=event_type,
        occurred_at=_utc_now(),
        actor_id=actor_id,
        idempotency_key=_new_id(),
        payload=_serialize_payload(payload),
    )
    db.add(event)
    return event


def _serialize_payload(payload: dict) -> dict:
    """Convert datetime objects in payload to ISO strings for JSON storage."""
    result = {}
    for k, v in payload.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize_payload(v)
        else:
            result[k] = v
    return result


async def reset_demo_data(db: AsyncSession) -> None:
    """Clear all data and seed default entities for a clean local deploy."""
    for model in (
        DailyReport,
        Task,
        Document,
        InsurancePolicy,
        ClinicalNote,
        Visit,
        Appointment,
        Patient,
        Staff,
        Room,
        EventLog,
    ):
        await db.execute(delete(model))
    await db.commit()
    await _seed_demo_entities(db)


async def _seed_demo_entities(db: AsyncSession) -> None:
    """Seed default staff, rooms, and patients for local testing."""
    now = _utc_now()

    for item in DEFAULT_STAFF:
        member = Staff(
            staff_id=_new_id(),
            name=item["name"],
            role=item["role"],
            license_id=item["license_id"],
            active=True,
            updated_at=now,
        )
        db.add(member)
        await _append_event(db, "STAFF_CREATED", "system_seed", _staff_to_dict(member))

    for item in DEFAULT_ROOMS:
        room = Room(
            room_id=_new_id(),
            name=item["name"],
            code=item["code"],
            room_type=item.get("room_type", "treatment"),
            branch="Main",
            floor="1F",
            active=True,
            status="available",
            updated_at=now,
        )
        db.add(room)
        await _append_event(db, "ROOM_CREATED", "system_seed", _room_to_dict(room))

    for item in DEFAULT_PATIENTS:
        patient = Patient(
            patient_id=_new_id(),
            first_name=item["first_name"],
            last_name=item["last_name"],
            phone=item.get("phone"),
            mrn=item.get("mrn"),
            active=True,
            updated_at=now,
        )
        db.add(patient)
        await _append_event(db, "PATIENT_CREATED", "system_seed", _patient_to_dict(patient))

    await db.commit()


async def ensure_default_demo_staff(db: AsyncSession) -> None:
    """Seed default local staff if none exist (non-destructive startup seed)."""
    existing = await db.execute(select(Staff.staff_id).limit(1))
    if existing.scalar_one_or_none():
        return
    await _seed_demo_entities(db)


# ==================== ROOMS ====================

async def create_room(db: AsyncSession, actor_id: str, data: dict) -> dict:
    room = Room(
        room_id=_new_id(),
        name=data["name"],
        code=data["code"],
        room_type=data.get("room_type", "treatment"),
        branch=data.get("branch", "Main"),
        floor=data.get("floor", "1F"),
        active=data.get("active", True),
        status="available",
        updated_at=_utc_now(),
    )
    db.add(room)
    await _append_event(db, "ROOM_CREATED", actor_id, _room_to_dict(room))
    await db.commit()
    return _room_to_dict(room)


async def update_room(db: AsyncSession, room_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    room = await db.get(Room, room_id)
    if not room:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(room, key):
            setattr(room, key, value)
    room.updated_at = _utc_now()
    await _append_event(db, "ROOM_UPDATED", actor_id, {"room_id": room_id, "updates": updates})
    await db.commit()
    return _room_to_dict(room)


def _room_to_dict(room: Room) -> dict:
    return {
        "room_id": room.room_id,
        "name": room.name,
        "code": room.code,
        "room_type": room.room_type,
        "branch": room.branch or "Main",
        "floor": room.floor or "1F",
        "active": room.active,
        "status": room.status,
        "updated_at": room.updated_at.isoformat() if room.updated_at else None,
    }


# ==================== STAFF ====================

async def create_staff(db: AsyncSession, actor_id: str, data: dict) -> dict:
    member = Staff(
        staff_id=_new_id(),
        name=data["name"],
        role=data["role"],
        license_id=data.get("license_id"),
        active=data.get("active", True),
        updated_at=_utc_now(),
    )
    db.add(member)
    await _append_event(db, "STAFF_CREATED", actor_id, _staff_to_dict(member))
    await db.commit()
    return _staff_to_dict(member)


async def update_staff(db: AsyncSession, staff_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    member = await db.get(Staff, staff_id)
    if not member:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(member, key):
            setattr(member, key, value)
    member.updated_at = _utc_now()
    await _append_event(db, "STAFF_UPDATED", actor_id, {"staff_id": staff_id, "updates": updates})
    await db.commit()
    return _staff_to_dict(member)


def _staff_to_dict(member: Staff) -> dict:
    return {
        "staff_id": member.staff_id,
        "name": member.name,
        "role": member.role,
        "license_id": member.license_id,
        "active": member.active,
        "updated_at": member.updated_at.isoformat() if member.updated_at else None,
    }


# ==================== VISITS ====================

async def patient_checkin(db: AsyncSession, actor_id: str, patient_name: str, patient_ref: Optional[str],
                          patient_id: Optional[str] = None, appointment_id: Optional[str] = None) -> dict:
    now = _utc_now()
    visit = Visit(
        visit_id=_new_id(),
        patient_id=patient_id,
        appointment_id=appointment_id,
        patient_name=patient_name,
        patient_ref=patient_ref,
        status="checked_in",
        check_in_time=now,
    )
    db.add(visit)

    # Update appointment status if linked
    if appointment_id:
        appt = await db.get(Appointment, appointment_id)
        if appt:
            appt.status = "checked_in"
            appt.updated_at = now

    await _append_event(db, "PATIENT_CHECKIN", actor_id, _visit_to_dict(visit))
    await db.commit()
    return _visit_to_dict(visit)


async def service_start(
    db: AsyncSession, visit_id: str, actor_id: str,
    staff_id: str, room_id: str, service_type: str,
    supervising_staff_id: Optional[str] = None,
) -> Optional[dict]:
    visit = await db.get(Visit, visit_id)
    staff_member = await db.get(Staff, staff_id)
    room = await db.get(Room, room_id)
    if not visit or not staff_member or not room:
        return None

    # Prevent double-booking: check if room is already occupied
    if room.status == "occupied":
        existing = await db.execute(
            select(Visit).where(Visit.room_id == room_id, Visit.status == "in_service")
        )
        if existing.scalars().first():
            raise ValueError(f"Room {room.code} is already occupied by another patient")

    now = _utc_now()
    visit.staff_id = staff_id
    visit.room_id = room_id
    visit.service_type = service_type
    visit.service_start_time = now
    visit.status = "in_service"
    if supervising_staff_id:
        visit.supervising_staff_id = supervising_staff_id

    room.status = "occupied"
    room.updated_at = now

    await _append_event(db, "SERVICE_STARTED", actor_id, {
        "visit_id": visit_id,
        "staff_id": staff_id,
        "room_id": room_id,
        "service_type": service_type,
        "service_start_time": now,
    })
    await db.commit()
    return _visit_to_dict(visit)


async def service_end(db: AsyncSession, visit_id: str, actor_id: str) -> Optional[dict]:
    visit = await db.get(Visit, visit_id)
    if not visit or not visit.service_start_time:
        return None

    now = _utc_now()
    visit.service_end_time = now
    visit.status = "service_completed"
    start_time = _ensure_utc(visit.service_start_time)
    duration_seconds = (now - start_time).total_seconds() if start_time else 0

    if visit.room_id:
        room = await db.get(Room, visit.room_id)
        if room:
            room.status = "available"
            room.updated_at = now

    await _append_event(db, "SERVICE_COMPLETED", actor_id, {
        "visit_id": visit_id,
        "staff_id": visit.staff_id,
        "room_id": visit.room_id,
        "service_type": visit.service_type,
        "duration_minutes": max(int(duration_seconds // 60), 0),
        "service_end_time": now,
    })
    await db.commit()
    return _visit_to_dict(visit)


async def patient_checkout(db: AsyncSession, visit_id: str, actor_id: str,
                           payment_status: Optional[str] = None,
                           payment_amount: Optional[float] = None,
                           payment_method: Optional[str] = None,
                           copay_collected: Optional[float] = None,
                           wd_verified: bool = False,
                           patient_signed: bool = False) -> Optional[dict]:
    visit = await db.get(Visit, visit_id)
    if not visit:
        return None

    now = _utc_now()
    visit.check_out_time = now
    visit.status = "checked_out"

    if payment_status:
        visit.payment_status = payment_status
    if payment_amount is not None:
        visit.payment_amount = payment_amount
    if payment_method:
        visit.payment_method = payment_method
    if copay_collected is not None:
        visit.copay_collected = copay_collected
    visit.wd_verified = wd_verified
    visit.patient_signed = patient_signed

    # Update linked appointment
    if visit.appointment_id:
        appt = await db.get(Appointment, visit.appointment_id)
        if appt:
            appt.status = "completed"
            appt.updated_at = now

    payload = {
        "visit_id": visit_id,
        "check_out_time": now,
        "payment_status": payment_status,
        "payment_amount": payment_amount,
        "payment_method": payment_method,
    }
    await _append_event(db, "PATIENT_CHECKOUT", actor_id, payload)

    # Record payment event separately if payment info provided
    if payment_amount is not None and payment_method:
        await _append_event(db, "PAYMENT_RECORDED", actor_id, {
            "visit_id": visit_id,
            "patient_id": visit.patient_id,
            "amount": payment_amount,
            "method": payment_method,
            "recorded_by": actor_id,
        })

    await db.commit()
    return _visit_to_dict(visit)


async def change_room_status(db: AsyncSession, room_id: str, actor_id: str, status: str) -> Optional[dict]:
    room = await db.get(Room, room_id)
    if not room:
        return None
    room.status = status
    room.updated_at = _utc_now()
    await _append_event(db, "ROOM_STATUS_CHANGED", actor_id, {"room_id": room_id, "status": status})
    await db.commit()
    return _room_to_dict(room)


def _visit_to_dict(visit: Visit) -> dict:
    return {
        "visit_id": visit.visit_id,
        "patient_id": visit.patient_id,
        "appointment_id": visit.appointment_id,
        "patient_name": visit.patient_name,
        "patient_ref": visit.patient_ref,
        "status": visit.status,
        "check_in_time": visit.check_in_time.isoformat() if visit.check_in_time else None,
        "service_type": visit.service_type,
        "service_start_time": visit.service_start_time.isoformat() if visit.service_start_time else None,
        "service_end_time": visit.service_end_time.isoformat() if visit.service_end_time else None,
        "check_out_time": visit.check_out_time.isoformat() if visit.check_out_time else None,
        "staff_id": visit.staff_id,
        "room_id": visit.room_id,
        "note_status": visit.note_status,
        "payment_status": visit.payment_status,
        "payment_amount": visit.payment_amount,
        "payment_method": visit.payment_method,
        "copay_collected": visit.copay_collected,
        "wd_verified": visit.wd_verified,
        "patient_signed": visit.patient_signed,
        "supervising_staff_id": visit.supervising_staff_id,
    }


# ==================== PROJECTIONS ====================

async def get_room_board(db: AsyncSession) -> list:
    rooms_result = await db.execute(select(Room).where(Room.active == True).order_by(Room.code))
    rooms = rooms_result.scalars().all()

    today = _utc_now().date().isoformat()
    visits_result = await db.execute(
        select(Visit).where(
            Visit.room_id.isnot(None),
            Visit.status.in_(["in_service", "checked_in", "service_completed"]),
        )
    )
    active_visits = {v.room_id: v for v in visits_result.scalars().all()}

    board = []
    for room in rooms:
        visit = active_visits.get(room.room_id)
        board.append({
            "room_id": room.room_id,
            "code": room.code,
            "name": room.name,
            "branch": room.branch or "Main",
            "floor": room.floor or "1F",
            "room_type": room.room_type,
            "status": room.status,
            "patient_name": visit.patient_name if visit else None,
            "visit_id": visit.visit_id if visit else None,
            "visit_status": visit.status if visit else None,
            "service_type": visit.service_type if visit else None,
            "staff_id": visit.staff_id if visit else None,
        })
    return board


async def get_active_visits(db: AsyncSession) -> list:
    result = await db.execute(
        select(Visit).where(
            Visit.status.in_(["checked_in", "in_service", "service_completed"])
        ).order_by(Visit.check_in_time)
    )
    return [_visit_to_dict(v) for v in result.scalars().all()]


async def get_patient_visits(db: AsyncSession, patient_id: str) -> list:
    """All visits for a patient, newest first. Includes room, staff, and treatment names for PDF."""
    result = await db.execute(
        select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.check_in_time.desc())
    )
    visits = result.scalars().all()

    enriched = []
    for v in visits:
        visit_dict = _visit_to_dict(v)

        if v.staff_id:
            staff = await db.get(Staff, v.staff_id)
            if staff:
                visit_dict["staff_name"] = staff.name

        if v.room_id:
            room = await db.get(Room, v.room_id)
            if room:
                visit_dict["room_name"] = room.name
                visit_dict["room_code"] = room.code

        # Fetch all treatments for this visit
        tx_result = await db.execute(
            select(VisitTreatment).where(VisitTreatment.visit_id == v.visit_id)
        )
        txs = tx_result.scalars().all()
        tx_list = []
        for t in txs:
            tx_dict = _treatment_to_dict(t)
            if t.therapist_id:
                therapist = await db.get(Staff, t.therapist_id)
                if therapist:
                    tx_dict["therapist_name"] = therapist.name
            tx_list.append(tx_dict)
        visit_dict["treatments"] = tx_list

        enriched.append(visit_dict)

    return enriched


async def get_daily_summary(db: AsyncSession, date: Optional[str] = None) -> dict:
    """Summary of all visits for a given date with copay totals."""
    target_date = date or _utc_now().date().isoformat()
    all_visits = (await db.execute(select(Visit))).scalars().all()
    today_visits = [
        v for v in all_visits
        if v.check_in_time and _ensure_utc(v.check_in_time).date().isoformat() == target_date
    ]
    checked_out = [v for v in today_visits if v.status == "checked_out"]
    active = [v for v in today_visits if v.status in ("checked_in", "in_service", "service_completed")]
    copay_total = sum((v.copay_collected or 0) for v in checked_out)
    payment_total = sum((v.payment_amount or 0) for v in checked_out if v.payment_amount)

    by_service: dict = {}
    for v in today_visits:
        svc = v.service_type or "unknown"
        by_service[svc] = by_service.get(svc, 0) + 1

    all_staff_result = await db.execute(select(Staff).where(Staff.active == True))
    staff_map = {s.staff_id: s.name for s in all_staff_result.scalars().all()}

    return {
        "date": target_date,
        "total_check_ins": len(today_visits),
        "total_checked_out": len(checked_out),
        "active_visits": len(active),
        "copay_total": round(copay_total, 2),
        "payment_total": round(payment_total, 2),
        "by_service_type": by_service,
        "visits": [
            {
                **_visit_to_dict(v),
                "staff_name": staff_map.get(v.staff_id, "-") if v.staff_id else "-",
            }
            for v in sorted(today_visits, key=lambda x: x.check_in_time or _utc_now())
        ],
    }


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime is timezone-aware UTC (SQLite strips tzinfo)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def get_staff_hours(db: AsyncSession) -> list:
    now = _utc_now()
    today = now.date().isoformat()

    staff_result = await db.execute(select(Staff).where(Staff.active == True).order_by(Staff.name))
    all_staff = staff_result.scalars().all()

    visits_result = await db.execute(select(Visit).where(Visit.staff_id.isnot(None)))
    all_visits = visits_result.scalars().all()

    per_staff = {}
    for member in all_staff:
        per_staff[member.staff_id] = {
            "staff_id": member.staff_id,
            "name": member.name,
            "role": member.role,
            "completed_minutes": 0,
            "active_minutes": 0,
            "sessions_completed": 0,
        }

    for visit in all_visits:
        sid = visit.staff_id
        if sid not in per_staff:
            continue
        start = _ensure_utc(visit.service_start_time)
        end = _ensure_utc(visit.service_end_time)
        if start and start.date().isoformat() == today:
            if end:
                seconds = (end - start).total_seconds()
                per_staff[sid]["completed_minutes"] += max(int(seconds // 60), 0)
                per_staff[sid]["sessions_completed"] += 1
            elif visit.status == "in_service":
                live_seconds = (now - start).total_seconds()
                per_staff[sid]["active_minutes"] += max(int(live_seconds // 60), 0)

    return list(per_staff.values())


# ==================== REPORTS ====================

async def generate_daily_report(db: AsyncSession, actor_id: str, report_date: Optional[str] = None) -> dict:
    target_date = report_date or _utc_now().date().isoformat()

    visits_result = await db.execute(select(Visit))
    all_visits = visits_result.scalars().all()
    today_visits = [v for v in all_visits if v.check_in_time and _ensure_utc(v.check_in_time).date().isoformat() == target_date]

    completed = [v for v in today_visits if v.service_end_time]
    open_sessions = [v for v in today_visits if v.service_start_time and not v.service_end_time]

    # Appointment stats
    appt_result = await db.execute(
        select(Appointment).where(Appointment.appointment_date == target_date)
    )
    today_appts = appt_result.scalars().all()
    no_shows = [a for a in today_appts if a.status == "no_show"]

    staff_hours = await get_staff_hours(db)
    room_board = await get_room_board(db)
    now = _utc_now()

    report_data = {
        "date": target_date,
        "total_check_ins": len(today_visits),
        "total_check_outs": len([v for v in today_visits if v.check_out_time]),
        "total_services_completed": len(completed),
        "total_appointments": len(today_appts),
        "no_shows": len(no_shows),
        "open_sessions": len(open_sessions),
        "staff_hours": staff_hours,
        "room_board_snapshot": room_board,
        "generated_at": now.isoformat(),
    }

    report = DailyReport(
        report_date=target_date,
        total_check_ins=report_data["total_check_ins"],
        total_check_outs=report_data["total_check_outs"],
        total_services_completed=report_data["total_services_completed"],
        total_appointments=report_data["total_appointments"],
        no_shows=report_data["no_shows"],
        open_sessions=report_data["open_sessions"],
        report_data=report_data,
        generated_at=now,
    )
    db.add(report)
    await _append_event(db, "DAILY_REPORT_GENERATED", actor_id, report_data)
    await db.commit()
    return report_data


async def get_daily_report(db: AsyncSession, report_date: Optional[str] = None) -> Optional[dict]:
    target_date = report_date or _utc_now().date().isoformat()
    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.report_date == target_date)
        .order_by(DailyReport.generated_at.desc())
    )
    report = result.scalars().first()
    if not report:
        return None
    return report.report_data


# ==================== DELETE ====================

async def delete_room(db: AsyncSession, room_id: str, actor_id: str) -> Optional[dict]:
    room = await db.get(Room, room_id)
    if not room:
        return None
    # Check no active visit in this room
    result = await db.execute(
        select(Visit).where(Visit.room_id == room_id, Visit.status.in_(["in_service", "checked_in"]))
    )
    if result.scalars().first():
        raise ValueError("Cannot delete room with active patients")
    room_dict = _room_to_dict(room)
    await db.delete(room)
    await _append_event(db, "ROOM_DELETED", actor_id, room_dict)
    await db.commit()
    return room_dict


async def delete_staff(db: AsyncSession, staff_id: str, actor_id: str) -> Optional[dict]:
    member = await db.get(Staff, staff_id)
    if not member:
        return None
    # Check no active service by this staff
    result = await db.execute(
        select(Visit).where(Visit.staff_id == staff_id, Visit.status == "in_service")
    )
    if result.scalars().first():
        raise ValueError("Cannot delete staff with active sessions")
    staff_dict = _staff_to_dict(member)
    await db.delete(member)
    await _append_event(db, "STAFF_DELETED", actor_id, staff_dict)
    await db.commit()
    return staff_dict


async def delete_visit(db: AsyncSession, visit_id: str, actor_id: str) -> Optional[dict]:
    visit = await db.get(Visit, visit_id)
    if not visit:
        return None
    # Free the room if occupied
    if visit.room_id and visit.status == "in_service":
        room = await db.get(Room, visit.room_id)
        if room:
            room.status = "available"
            room.updated_at = _utc_now()
    visit_dict = _visit_to_dict(visit)
    await db.delete(visit)
    await _append_event(db, "VISIT_DELETED", actor_id, visit_dict)
    await db.commit()
    return visit_dict


# ==================== EVENTS ====================

async def get_events(db: AsyncSession) -> dict:
    result = await db.execute(select(EventLog).order_by(EventLog.id))
    events = result.scalars().all()
    return {
        "count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "actor_id": e.actor_id,
                "idempotency_key": e.idempotency_key,
                "payload": e.payload,
            }
            for e in events
        ],
    }


# ==================== PATIENT (§11.1) ====================

def _patient_to_dict(p: Patient) -> dict:
    return {
        "patient_id": p.patient_id,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "full_name": f"{p.first_name} {p.last_name}",
        "date_of_birth": p.date_of_birth,
        "gender": p.gender,
        "phone": p.phone,
        "email": p.email,
        "address": p.address,
        "mrn": p.mrn,
        "intake_status": p.intake_status,
        "consent_status": p.consent_status,
        "notes": p.notes,
        "active": p.active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


async def create_patient(db: AsyncSession, actor_id: str, data: dict, force: bool = False) -> dict:
    # Duplicate check: case-insensitive name match + DOB (if provided)
    if not force:
        conditions = [
            func.lower(Patient.first_name) == data["first_name"].lower(),
            func.lower(Patient.last_name) == data["last_name"].lower(),
        ]
        if data.get("date_of_birth"):
            conditions.append(Patient.date_of_birth == data["date_of_birth"])

        existing = await db.execute(select(Patient).where(*conditions))
        dup = existing.scalars().first()
        if dup:
            detail = f"{dup.first_name} {dup.last_name}"
            if dup.date_of_birth:
                detail += f" DOB {dup.date_of_birth}"
            if dup.mrn:
                detail += f" MRN {dup.mrn}"
            if dup.phone:
                detail += f" Phone {dup.phone}"
            raise ValueError(f"Possible duplicate: {detail}. Add anyway?")

    patient = Patient(
        patient_id=_new_id(),
        first_name=data["first_name"],
        last_name=data["last_name"],
        date_of_birth=data.get("date_of_birth"),
        gender=data.get("gender"),
        phone=data.get("phone"),
        email=data.get("email"),
        address=data.get("address"),
        mrn=data.get("mrn"),
        notes=data.get("notes"),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(patient)
    await _append_event(db, "PATIENT_CREATED", actor_id, _patient_to_dict(patient))
    await db.commit()
    return _patient_to_dict(patient)


async def update_patient(db: AsyncSession, patient_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    patient = await db.get(Patient, patient_id)
    if not patient:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(patient, key):
            setattr(patient, key, value)
    patient.updated_at = _utc_now()
    await _append_event(db, "PATIENT_UPDATED", actor_id, {"patient_id": patient_id, "updates": updates})
    await db.commit()
    return _patient_to_dict(patient)


async def delete_patient(db: AsyncSession, patient_id: str, actor_id: str) -> Optional[dict]:
    patient = await db.get(Patient, patient_id)
    if not patient:
        return None
    if not patient.active:
        return _patient_to_dict(patient)

    patient.active = False
    patient.updated_at = _utc_now()
    payload = {
        "patient_id": patient.patient_id,
        "full_name": f"{patient.first_name} {patient.last_name}",
        "mrn": patient.mrn,
        "date_of_birth": patient.date_of_birth,
        "active": False,
    }
    await _append_event(db, "PATIENT_DELETED", actor_id, payload)
    await db.commit()
    return _patient_to_dict(patient)


async def get_patient(db: AsyncSession, patient_id: str) -> Optional[dict]:
    patient = await db.get(Patient, patient_id)
    if not patient:
        return None
    return _patient_to_dict(patient)


async def search_patients(db: AsyncSession, query: str) -> list:
    pattern = f"%{query}%"
    result = await db.execute(
        select(Patient).where(
            Patient.active == True,
            or_(
                Patient.first_name.ilike(pattern),
                Patient.last_name.ilike(pattern),
                Patient.mrn.ilike(pattern),
                Patient.phone.ilike(pattern),
                Patient.email.ilike(pattern),
            )
        ).order_by(Patient.last_name, Patient.first_name)
    )
    return [_patient_to_dict(p) for p in result.scalars().all()]


async def list_patients(db: AsyncSession) -> list:
    result = await db.execute(select(Patient).where(Patient.active == True).order_by(Patient.last_name, Patient.first_name))
    return [_patient_to_dict(p) for p in result.scalars().all()]


# ==================== APPOINTMENT (§11.2) ====================

def _appointment_to_dict(a: Appointment) -> dict:
    return {
        "appointment_id": a.appointment_id,
        "patient_id": a.patient_id,
        "provider_id": a.provider_id,
        "appointment_date": a.appointment_date,
        "appointment_time": a.appointment_time,
        "appointment_type": a.appointment_type,
        "status": a.status,
        "cancellation_reason": a.cancellation_reason,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


async def create_appointment(db: AsyncSession, actor_id: str, data: dict) -> dict:
    appt = Appointment(
        appointment_id=_new_id(),
        patient_id=data["patient_id"],
        provider_id=data.get("provider_id"),
        appointment_date=data["appointment_date"],
        appointment_time=data.get("appointment_time"),
        appointment_type=data.get("appointment_type", "regular"),
        notes=data.get("notes"),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(appt)
    await _append_event(db, "APPOINTMENT_CREATED", actor_id, _appointment_to_dict(appt))
    await db.commit()
    return _appointment_to_dict(appt)


async def update_appointment(db: AsyncSession, appointment_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(appt, key):
            setattr(appt, key, value)
    appt.updated_at = _utc_now()
    await _append_event(db, "APPOINTMENT_UPDATED", actor_id, {"appointment_id": appointment_id, "updates": updates})
    await db.commit()
    return _appointment_to_dict(appt)


async def cancel_appointment(db: AsyncSession, appointment_id: str, actor_id: str, reason: Optional[str] = None) -> Optional[dict]:
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        return None
    appt.status = "cancelled"
    appt.cancellation_reason = reason
    appt.updated_at = _utc_now()
    await _append_event(db, "APPOINTMENT_CANCELLED", actor_id, {"appointment_id": appointment_id, "reason": reason})
    await db.commit()
    return _appointment_to_dict(appt)


async def mark_no_show(db: AsyncSession, appointment_id: str, actor_id: str) -> Optional[dict]:
    appt = await db.get(Appointment, appointment_id)
    if not appt:
        return None
    appt.status = "no_show"
    appt.updated_at = _utc_now()
    await _append_event(db, "NO_SHOW_MARKED", actor_id, {"appointment_id": appointment_id, "patient_id": appt.patient_id})
    await db.commit()
    return _appointment_to_dict(appt)


async def list_appointments(db: AsyncSession, date: Optional[str] = None, patient_id: Optional[str] = None, provider_id: Optional[str] = None) -> list:
    query = select(Appointment)
    if date:
        query = query.where(Appointment.appointment_date == date)
    if patient_id:
        query = query.where(Appointment.patient_id == patient_id)
    if provider_id:
        query = query.where(Appointment.provider_id == provider_id)
    query = query.order_by(Appointment.appointment_date, Appointment.appointment_time)
    result = await db.execute(query)
    return [_appointment_to_dict(a) for a in result.scalars().all()]


# ==================== CLINICAL NOTE (§11.6) ====================

def _note_to_dict(n: ClinicalNote) -> dict:
    return {
        "note_id": n.note_id,
        "visit_id": n.visit_id,
        "patient_id": n.patient_id,
        "provider_id": n.provider_id,
        "template_type": n.template_type,
        "status": n.status,
        "content": n.content,
        "raw_input": n.raw_input,
        "signed_at": n.signed_at.isoformat() if n.signed_at else None,
        "signed_by": n.signed_by,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


async def create_note(db: AsyncSession, actor_id: str, data: dict) -> dict:
    note = ClinicalNote(
        note_id=_new_id(),
        visit_id=data["visit_id"],
        patient_id=data.get("patient_id"),
        provider_id=data.get("provider_id"),
        template_type=data.get("template_type"),
        content=data.get("content"),
        raw_input=data.get("raw_input"),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(note)
    await _append_event(db, "NOTE_CREATED", actor_id, _note_to_dict(note))
    await db.commit()
    return _note_to_dict(note)


async def update_note(db: AsyncSession, note_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    note = await db.get(ClinicalNote, note_id)
    if not note:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(note, key):
            setattr(note, key, value)
    note.updated_at = _utc_now()
    await _append_event(db, "NOTE_UPDATED", actor_id, {"note_id": note_id, "updates": updates})
    await db.commit()
    return _note_to_dict(note)


async def sign_note(db: AsyncSession, note_id: str, actor_id: str) -> Optional[dict]:
    note = await db.get(ClinicalNote, note_id)
    if not note:
        return None
    now = _utc_now()
    note.status = "signed"
    note.signed_at = now
    note.signed_by = actor_id
    note.updated_at = now

    # Update visit note_status
    if note.visit_id:
        visit = await db.get(Visit, note.visit_id)
        if visit:
            visit.note_status = "signed"

    await _append_event(db, "NOTE_SIGNED", actor_id, {"note_id": note_id, "signed_at": now})
    await db.commit()
    return _note_to_dict(note)


async def list_notes(db: AsyncSession, visit_id: Optional[str] = None, patient_id: Optional[str] = None) -> list:
    query = select(ClinicalNote)
    if visit_id:
        query = query.where(ClinicalNote.visit_id == visit_id)
    if patient_id:
        query = query.where(ClinicalNote.patient_id == patient_id)
    query = query.order_by(ClinicalNote.created_at.desc())
    result = await db.execute(query)
    return [_note_to_dict(n) for n in result.scalars().all()]


# ==================== INSURANCE POLICY (§11.7) ====================

def _policy_to_dict(p: InsurancePolicy) -> dict:
    return {
        "policy_id": p.policy_id,
        "patient_id": p.patient_id,
        "carrier_name": p.carrier_name,
        "member_id": p.member_id,
        "group_number": p.group_number,
        "plan_type": p.plan_type,
        "copay_amount": p.copay_amount,
        "deductible": p.deductible,
        "priority": p.priority,
        "eligibility_status": p.eligibility_status,
        "eligibility_verified_at": p.eligibility_verified_at.isoformat() if p.eligibility_verified_at else None,
        "eligibility_notes": p.eligibility_notes,
        "visits_authorized": p.visits_authorized,
        "visits_used": p.visits_used,
        "active": p.active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


async def create_insurance_policy(db: AsyncSession, actor_id: str, data: dict) -> dict:
    policy = InsurancePolicy(
        policy_id=_new_id(),
        patient_id=data["patient_id"],
        carrier_name=data["carrier_name"],
        member_id=data.get("member_id"),
        group_number=data.get("group_number"),
        plan_type=data.get("plan_type"),
        copay_amount=data.get("copay_amount"),
        deductible=data.get("deductible"),
        priority=data.get("priority", "primary"),
        visits_authorized=data.get("visits_authorized"),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(policy)
    await _append_event(db, "INSURANCE_POLICY_CREATED", actor_id, _policy_to_dict(policy))
    await db.commit()
    return _policy_to_dict(policy)


async def update_insurance_policy(db: AsyncSession, policy_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    policy = await db.get(InsurancePolicy, policy_id)
    if not policy:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(policy, key):
            setattr(policy, key, value)
    # If eligibility_status is being updated, record verification time
    if "eligibility_status" in updates and updates["eligibility_status"] in ("verified", "denied"):
        policy.eligibility_verified_at = _utc_now()
    policy.updated_at = _utc_now()
    await _append_event(db, "INSURANCE_POLICY_UPDATED", actor_id, {"policy_id": policy_id, "updates": updates})
    await db.commit()
    return _policy_to_dict(policy)


async def list_insurance_policies(db: AsyncSession, patient_id: str) -> list:
    result = await db.execute(
        select(InsurancePolicy).where(InsurancePolicy.patient_id == patient_id).order_by(InsurancePolicy.priority)
    )
    return [_policy_to_dict(p) for p in result.scalars().all()]


# ==================== DOCUMENT (§11.4) ====================

def _document_to_dict(d: Document) -> dict:
    return {
        "document_id": d.document_id,
        "patient_id": d.patient_id,
        "visit_id": d.visit_id,
        "document_type": d.document_type,
        "template_id": d.template_id,
        "sequence_number": d.sequence_number,
        "status": d.status,
        "version": d.version,
        "file_ref": d.file_ref,
        "metadata": d.metadata_,
        "signed_at": d.signed_at.isoformat() if d.signed_at else None,
        "signed_by": d.signed_by,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


async def create_document(db: AsyncSession, actor_id: str, data: dict) -> dict:
    # Auto-increment sequence_number per patient + document_type
    result = await db.execute(
        select(func.max(Document.sequence_number)).where(
            Document.patient_id == data["patient_id"],
            Document.document_type == data["document_type"],
        )
    )
    max_seq = result.scalar() or 0

    doc = Document(
        document_id=_new_id(),
        patient_id=data["patient_id"],
        visit_id=data.get("visit_id"),
        document_type=data["document_type"],
        template_id=data.get("template_id"),
        sequence_number=max_seq + 1,
        file_ref=data.get("file_ref"),
        metadata_=data.get("metadata"),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(doc)
    await _append_event(db, "DOCUMENT_CREATED", actor_id, _document_to_dict(doc))
    await db.commit()
    return _document_to_dict(doc)


async def update_document(db: AsyncSession, document_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    doc = await db.get(Document, document_id)
    if not doc:
        return None
    for key, value in updates.items():
        if value is not None:
            if key == "metadata":
                doc.metadata_ = value
            elif hasattr(doc, key):
                setattr(doc, key, value)
    doc.updated_at = _utc_now()
    await _append_event(db, "DOCUMENT_UPDATED", actor_id, {"document_id": document_id, "updates": updates})
    await db.commit()
    return _document_to_dict(doc)


async def sign_document(db: AsyncSession, document_id: str, actor_id: str) -> Optional[dict]:
    doc = await db.get(Document, document_id)
    if not doc:
        return None
    now = _utc_now()
    doc.status = "signed"
    doc.signed_at = now
    doc.signed_by = actor_id
    doc.updated_at = now
    await _append_event(db, "DOCUMENT_SIGNED", actor_id, {"document_id": document_id, "signed_at": now})
    await db.commit()
    return _document_to_dict(doc)


async def list_documents(db: AsyncSession, patient_id: str, document_type: Optional[str] = None) -> list:
    query = select(Document).where(Document.patient_id == patient_id)
    if document_type:
        query = query.where(Document.document_type == document_type)
    query = query.order_by(Document.document_type, Document.sequence_number)
    result = await db.execute(query)
    return [_document_to_dict(d) for d in result.scalars().all()]


# ==================== TASK (§11.9) ====================

def _task_to_dict(t: Task) -> dict:
    return {
        "task_id": t.task_id,
        "patient_id": t.patient_id,
        "visit_id": t.visit_id,
        "claim_id": t.claim_id,
        "task_type": t.task_type,
        "title": t.title,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "assignee_id": t.assignee_id,
        "due_date": t.due_date,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


async def create_task(db: AsyncSession, actor_id: str, data: dict) -> dict:
    task = Task(
        task_id=_new_id(),
        patient_id=data.get("patient_id"),
        visit_id=data.get("visit_id"),
        claim_id=data.get("claim_id"),
        task_type=data.get("task_type", "general"),
        title=data["title"],
        description=data.get("description"),
        priority=data.get("priority", "normal"),
        assignee_id=data.get("assignee_id"),
        due_date=data.get("due_date"),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(task)
    await _append_event(db, "TASK_CREATED", actor_id, _task_to_dict(task))
    await db.commit()
    return _task_to_dict(task)


async def update_task(db: AsyncSession, task_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    task = await db.get(Task, task_id)
    if not task:
        return None
    for key, value in updates.items():
        if value is not None and hasattr(task, key):
            setattr(task, key, value)
    # If status changed to completed, set completed_at
    if updates.get("status") == "completed" and not task.completed_at:
        task.completed_at = _utc_now()
    task.updated_at = _utc_now()
    await _append_event(db, "TASK_UPDATED", actor_id, {"task_id": task_id, "updates": updates})
    await db.commit()
    return _task_to_dict(task)


async def list_tasks(db: AsyncSession, patient_id: Optional[str] = None,
                     assignee_id: Optional[str] = None,
                     status: Optional[str] = None,
                     task_type: Optional[str] = None) -> list:
    query = select(Task)
    if patient_id:
        query = query.where(Task.patient_id == patient_id)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if status:
        query = query.where(Task.status == status)
    if task_type:
        query = query.where(Task.task_type == task_type)
    query = query.order_by(Task.priority.desc(), Task.created_at.desc())
    result = await db.execute(query)
    return [_task_to_dict(t) for t in result.scalars().all()]


# ===================== TREATMENTS (PRD-005) =====================

async def add_treatment(
    db: AsyncSession,
    visit_id: str,
    modality: str,
    actor_id: str,
    therapist_id: Optional[str] = None,
    duration_minutes: Optional[int] = 30,
    notes: Optional[str] = None
) -> dict:
    """Add a treatment modality to a visit."""
    # Verify visit exists and is active
    visit_result = await db.execute(select(Visit).where(Visit.visit_id == visit_id))
    visit = visit_result.scalar_one_or_none()
    if not visit:
        raise ValueError(f"Visit {visit_id} not found")
    if visit.status not in ("checked_in", "in_service", "service_completed"):
        raise ValueError(f"Cannot add treatment to visit with status {visit.status}")
    
    treatment = VisitTreatment(
        treatment_id=_new_id(),
        visit_id=visit_id,
        modality=modality,
        therapist_id=therapist_id or actor_id,
        duration_minutes=duration_minutes,
        notes=notes,
        started_at=_utc_now(),
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    db.add(treatment)
    
    await _append_event(db, "TREATMENT_ADDED", actor_id, {
        "treatment_id": treatment.treatment_id,
        "visit_id": visit_id,
        "modality": modality,
        "therapist_id": therapist_id,
        "duration_minutes": duration_minutes,
    })
    
    await db.commit()
    return _treatment_to_dict(treatment)


async def update_treatment(
    db: AsyncSession,
    treatment_id: str,
    actor_id: str,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> dict:
    """Update treatment duration and notes."""
    result = await db.execute(select(VisitTreatment).where(VisitTreatment.treatment_id == treatment_id))
    treatment = result.scalar_one_or_none()
    if not treatment:
        raise ValueError(f"Treatment {treatment_id} not found")
    
    updates = {}
    if duration_minutes is not None:
        treatment.duration_minutes = duration_minutes
        updates["duration_minutes"] = duration_minutes
    if notes is not None:
        treatment.notes = notes
        updates["notes"] = notes
    
    treatment.updated_at = _utc_now()
    
    await _append_event(db, "TREATMENT_UPDATED", actor_id, {
        "treatment_id": treatment_id,
        "updates": updates,
    })
    
    await db.commit()
    return _treatment_to_dict(treatment)


async def delete_treatment(
    db: AsyncSession,
    treatment_id: str,
    actor_id: str
) -> dict:
    """Soft delete a treatment."""
    result = await db.execute(select(VisitTreatment).where(VisitTreatment.treatment_id == treatment_id))
    treatment = result.scalar_one_or_none()
    if not treatment:
        raise ValueError(f"Treatment {treatment_id} not found")
    
    await _append_event(db, "TREATMENT_DELETED", actor_id, {
        "treatment_id": treatment_id,
        "visit_id": treatment.visit_id,
    })
    
    await db.execute(delete(VisitTreatment).where(VisitTreatment.treatment_id == treatment_id))
    await db.commit()
    
    return {"deleted": True, "treatment_id": treatment_id}


async def list_visit_treatments(db: AsyncSession, visit_id: str) -> list:
    """List all treatments for a visit."""
    result = await db.execute(
        select(VisitTreatment)
        .where(VisitTreatment.visit_id == visit_id)
        .order_by(VisitTreatment.started_at)
    )
    treatments = result.scalars().all()
    
    # Enrich with therapist names
    enriched = []
    for t in treatments:
        t_dict = _treatment_to_dict(t)
        if t.therapist_id:
            staff = await db.get(Staff, t.therapist_id)
            if staff:
                t_dict["therapist_name"] = staff.name
        enriched.append(t_dict)
    
    return enriched


async def list_treatment_records(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    modality: Optional[str] = None
) -> list:
    """Query treatment records with filters."""
    query = select(VisitTreatment).join(Visit, Visit.visit_id == VisitTreatment.visit_id)
    
    if date_from:
        query = query.where(Visit.check_in_time >= date_from)
    if date_to:
        query = query.where(Visit.check_in_time <= date_to + " 23:59:59")
    if patient_id:
        query = query.where(Visit.patient_id == patient_id)
    if staff_id:
        query = query.where(VisitTreatment.therapist_id == staff_id)
    if modality:
        query = query.where(VisitTreatment.modality == modality)
    
    query = query.order_by(Visit.check_in_time.desc())
    result = await db.execute(query)
    treatments = result.scalars().all()
    
    # Enrich with visit, patient, therapist, room details
    enriched = []
    for t in treatments:
        t_dict = _treatment_to_dict(t)
        
        visit_result = await db.execute(select(Visit).where(Visit.visit_id == t.visit_id))
        visit = visit_result.scalar_one_or_none()
        if visit:
            t_dict["check_in_time"] = visit.check_in_time.isoformat() if visit.check_in_time else None
            t_dict["visit_status"] = visit.status
            t_dict["service_type"] = visit.service_type
            if visit.supervising_staff_id:
                supervisor = await db.get(Staff, visit.supervising_staff_id)
                t_dict["supervising_doctor"] = supervisor.name if supervisor else None
            else:
                t_dict["supervising_doctor"] = None
            
            # Get patient name — prefer Patient record, fall back to visit.patient_name (walk-ins)
            patient = await db.get(Patient, visit.patient_id) if visit.patient_id else None
            if patient:
                t_dict["patient_name"] = f"{patient.first_name} {patient.last_name}"
            elif visit.patient_name:
                t_dict["patient_name"] = visit.patient_name
            
            # Get room name
            if visit.room_id:
                room = await db.get(Room, visit.room_id)
                if room:
                    t_dict["room_name"] = room.name
                    t_dict["room_code"] = room.code
        
        # Get therapist name
        if t.therapist_id:
            staff = await db.get(Staff, t.therapist_id)
            if staff:
                t_dict["therapist_name"] = staff.name
        
        enriched.append(t_dict)
    
    return enriched


def _modality_to_col(modality: str) -> str:
    """Map treatment modality string to one of the 4 display columns."""
    m = (modality or "").lower()
    if "acupuncture" in m or m == "a":
        return "A"
    if any(x in m for x in ["pt", "ot", "eval", "physical", "occupational", "speech"]):
        return "PT"
    if any(x in m for x in ["cupping", "cup", "cp"]):
        return "CP"
    if any(x in m for x in ["massage", "tui", "tn"]):
        return "TN"
    return "other"  # E-stim, Heat, Cold, etc. — shown in notes column


async def list_visits_with_treatments(
    db: AsyncSession,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_id: Optional[str] = None,
    staff_id: Optional[str] = None,
) -> list:
    """Return one record per visit with treatments organized by modality column (A/PT/CP/TN).
    Used for the 诊疗记录表 Treatment Records tab.
    """
    query = select(Visit).order_by(Visit.check_in_time.desc())
    if date_from:
        query = query.where(Visit.check_in_time >= date_from)
    if date_to:
        query = query.where(Visit.check_in_time <= date_to + " 23:59:59")
    if patient_id:
        query = query.where(Visit.patient_id == patient_id)

    visits = (await db.execute(query)).scalars().all()

    # Bulk-load lookup maps (avoid N+1)
    staff_map = {s.staff_id: s.name for s in (await db.execute(select(Staff))).scalars().all()}
    patient_map = {p.patient_id: f"{p.first_name} {p.last_name}" for p in (await db.execute(select(Patient))).scalars().all()}
    room_map = {r.room_id: r.name for r in (await db.execute(select(Room))).scalars().all()}

    # Bulk-load all treatments for these visits
    visit_ids = [v.visit_id for v in visits]
    if visit_ids:
        tx_result = await db.execute(
            select(VisitTreatment).where(VisitTreatment.visit_id.in_(visit_ids))
        )
        all_treatments = tx_result.scalars().all()
    else:
        all_treatments = []

    from collections import defaultdict
    tx_by_visit: dict = defaultdict(list)
    for t in all_treatments:
        tx_by_visit[t.visit_id].append(t)

    records = []
    for v in visits:
        treatments = tx_by_visit.get(v.visit_id, [])

        # Apply staff_id filter — include visit if primary therapist OR any treatment therapist matches
        if staff_id:
            if v.staff_id != staff_id and not any(t.therapist_id == staff_id for t in treatments):
                continue

        # Map each treatment to a column; cell = therapist name (first match wins per column)
        col_therapist: dict = {"A": "", "PT": "", "CP": "", "TN": ""}
        other_modalities: list = []
        notes_parts: list = []
        total_minutes = 0
        for t in treatments:
            col = _modality_to_col(t.modality or "")
            tname = staff_map.get(t.therapist_id, "") if t.therapist_id else ""
            if col == "other":
                other_modalities.append(t.modality or "")
            elif not col_therapist[col]:
                col_therapist[col] = tname
            if t.notes:
                notes_parts.append(t.notes)
            if t.duration_minutes:
                total_minutes += t.duration_minutes

        # Fallback: if no explicit treatments but service_type is set, populate the right column
        if not treatments and v.service_type:
            col = _modality_to_col(v.service_type)
            primary = staff_map.get(v.staff_id, "") if v.staff_id else ""
            if col in col_therapist:
                col_therapist[col] = primary

        patient_name = patient_map.get(v.patient_id, "") if v.patient_id else (v.patient_name or "")

        records.append({
            "visit_id": v.visit_id,
            "patient_id": v.patient_id,
            "patient_name": patient_name,
            "check_in_time": v.check_in_time.isoformat() if v.check_in_time else None,
            "status": v.status,
            "supervising_doctor": staff_map.get(v.supervising_staff_id, "") if v.supervising_staff_id else "",
            "primary_therapist": staff_map.get(v.staff_id, "") if v.staff_id else "",
            "room_name": room_map.get(v.room_id, "") if v.room_id else "",
            "service_type": v.service_type or "",
            "A": col_therapist["A"],
            "PT": col_therapist["PT"],
            "CP": col_therapist["CP"],
            "TN": col_therapist["TN"],
            "other_modalities": ", ".join(other_modalities),
            "total_minutes": total_minutes,
            "notes": " | ".join(notes_parts),
            "copay_collected": v.copay_collected,
        })

    return records


def _treatment_to_dict(treatment: VisitTreatment) -> dict:
    """Convert VisitTreatment ORM object to dict."""
    return {
        "treatment_id": treatment.treatment_id,
        "visit_id": treatment.visit_id,
        "modality": treatment.modality,
        "therapist_id": treatment.therapist_id,
        "duration_minutes": treatment.duration_minutes,
        "started_at": treatment.started_at.isoformat() if treatment.started_at else None,
        "completed_at": treatment.completed_at.isoformat() if treatment.completed_at else None,
        "notes": treatment.notes,
        "created_at": treatment.created_at.isoformat() if treatment.created_at else None,
        "updated_at": treatment.updated_at.isoformat() if treatment.updated_at else None,
    }
