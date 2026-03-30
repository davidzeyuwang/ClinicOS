"""
Supabase REST-backed service layer.
Same function signatures as db_service.py but uses SupabaseClient instead of SQLAlchemy.
Active when SUPABASE_URL + SUPABASE_SERVICE_KEY env vars are set.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database import get_supabase


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


async def _append_event(event_type: str, actor_id: str, payload: dict) -> None:
    supa = get_supabase()
    await supa.insert("event_log", {
        "event_id": _new_id(),
        "event_type": event_type,
        "occurred_at": _utc_now(),
        "actor_id": actor_id,
        "idempotency_key": _new_id(),
        "schema_version": 1,
        "payload": _serialize(payload),
    })


def _serialize(payload: dict) -> dict:
    result = {}
    for k, v in payload.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, dict):
            result[k] = _serialize(v)
        else:
            result[k] = v
    return result


def _with_full_name(patient: dict) -> dict:
    """Inject full_name so the frontend doesn't need to concatenate."""
    if patient and "full_name" not in patient:
        patient = dict(patient)
        patient["full_name"] = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    return patient


# ==================== ROOMS ====================

async def create_room(db, actor_id: str, data: dict) -> dict:
    supa = get_supabase()
    room = {
        "room_id": _new_id(),
        "name": data["name"],
        "code": data["code"],
        "room_type": data.get("room_type", "treatment"),
        "branch": data.get("branch", "Main"),
        "floor": data.get("floor", "1F"),
        "active": data.get("active", True),
        "status": "available",
        "updated_at": _utc_now(),
    }
    result = await supa.insert("rooms", room)
    await _append_event("ROOM_CREATED", actor_id, result)
    return result


async def update_room(db, room_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("rooms", "room_id", room_id, updates)
    if not result:
        return None
    await _append_event("ROOM_UPDATED", actor_id, {"room_id": room_id, "updates": updates})
    return result


async def delete_room(db, room_id: str, actor_id: str) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("rooms", {"room_id": room_id})
    if not rows:
        return None
    room = rows[0]
    # Check if room has active visits
    visits = await supa.select("visits", {"room_id": room_id})
    active = [v for v in visits if v.get("status") in ("checked_in", "in_service")]
    if active:
        raise ValueError(f"Room {room_id} has active visits")
    await supa.delete("rooms", "room_id", room_id)
    await _append_event("ROOM_DELETED", actor_id, {"room_id": room_id})
    return room


async def change_room_status(db, room_id: str, actor_id: str, status: str) -> Optional[dict]:
    supa = get_supabase()
    result = await supa.update("rooms", "room_id", room_id, {"status": status, "updated_at": _utc_now()})
    if not result:
        return None
    await _append_event("ROOM_STATUS_CHANGED", actor_id, {"room_id": room_id, "status": status})
    return result


async def get_room_board(db) -> list:
    supa = get_supabase()
    import httpx
    client = supa._client

    # Fetch rooms and active visits in parallel
    rooms_url = f"{supa._url}/rest/v1/rooms"
    visits_url = f"{supa._url}/rest/v1/visits"

    rooms_r, visits_r = await asyncio.gather(
        client.get(rooms_url, params={"select": "*", "active": "eq.true"}),
        client.get(visits_url, params={
            "select": "visit_id,patient_id,patient_name,service_type,status,staff_id,room_id",
            "status": "neq.checked_out",
            "room_id": "not.is.null",
        }),
    )
    rooms_r.raise_for_status()
    visits_r.raise_for_status()

    rooms = rooms_r.json()
    active_visits = {v["room_id"]: v for v in visits_r.json() if v.get("room_id")}

    for room in rooms:
        v = active_visits.get(room["room_id"])
        if v:
            room["visit_id"] = v["visit_id"]
            room["patient_id"] = v["patient_id"]
            room["patient_name"] = v["patient_name"]
            room["service_type"] = v["service_type"]
            room["visit_status"] = v["status"]
        else:
            room["visit_id"] = None
            room["patient_id"] = None
            room["patient_name"] = None
            room["service_type"] = None
            room["visit_status"] = None

    return rooms


# ==================== STAFF ====================

async def create_staff(db, actor_id: str, data: dict) -> dict:
    supa = get_supabase()
    staff = {
        "staff_id": _new_id(),
        "name": data["name"],
        "role": data["role"],
        "license_id": data.get("license_id"),
        "active": data.get("active", True),
        "updated_at": _utc_now(),
    }
    result = await supa.insert("staff", staff)
    await _append_event("STAFF_CREATED", actor_id, result)
    return result


async def update_staff(db, staff_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("staff", "staff_id", staff_id, updates)
    if not result:
        return None
    await _append_event("STAFF_UPDATED", actor_id, {"staff_id": staff_id})
    return result


async def delete_staff(db, staff_id: str, actor_id: str) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("staff", {"staff_id": staff_id})
    if not rows:
        return None
    await supa.delete("staff", "staff_id", staff_id)
    await _append_event("STAFF_DELETED", actor_id, {"staff_id": staff_id})
    return rows[0]


async def get_staff_hours(db) -> list:
    supa = get_supabase()
    return await supa.select("staff", {"active": True})


# ==================== VISITS ====================

async def patient_checkin(db, actor_id: str, patient_name: str, patient_ref: Optional[str] = None,
                          patient_id: Optional[str] = None, appointment_id: Optional[str] = None) -> dict:
    supa = get_supabase()
    now = _utc_now()
    visit = {
        "visit_id": _new_id(),
        "patient_id": patient_id,
        "appointment_id": appointment_id,
        "patient_name": patient_name,
        "patient_ref": patient_ref,
        "status": "checked_in",
        "check_in_time": now,
        "note_status": "pending",
        "payment_status": "pending",
    }
    result = await supa.insert("visits", visit)
    await _append_event("PATIENT_CHECKED_IN", actor_id, result)
    return result


async def service_start(db, visit_id: str, actor_id: str, staff_id: Optional[str] = None,
                        room_id: Optional[str] = None, service_type: Optional[str] = None) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    visit = rows[0]
    if visit["status"] != "checked_in":
        raise ValueError(f"Visit status is {visit['status']}, cannot start service")
    updates = {
        "status": "in_service",
        "staff_id": staff_id,
        "room_id": room_id,
        "service_type": service_type,
        "service_start_time": _utc_now(),
    }
    result = await supa.update("visits", "visit_id", visit_id, updates)
    if room_id:
        await supa.update("rooms", "room_id", room_id, {"status": "occupied", "updated_at": _utc_now()})
    await _append_event("SERVICE_STARTED", actor_id, {"visit_id": visit_id, **updates})
    return result


async def service_end(db, visit_id: str, actor_id: str) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    visit = rows[0]
    if visit["status"] != "in_service":
        return None
    updates = {"status": "service_completed", "service_end_time": _utc_now()}
    result = await supa.update("visits", "visit_id", visit_id, updates)
    if visit.get("room_id"):
        await supa.update("rooms", "room_id", visit["room_id"], {"status": "cleaning", "updated_at": _utc_now()})
    await _append_event("SERVICE_ENDED", actor_id, {"visit_id": visit_id})
    return result


async def patient_checkout(db, visit_id: str, actor_id: str, payment_status: Optional[str] = None,
                           payment_amount: Optional[float] = None, payment_method: Optional[str] = None,
                           copay_collected: Optional[float] = None, wd_verified: bool = False,
                           patient_signed: bool = False) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    updates = {
        "status": "checked_out",
        "check_out_time": _utc_now(),
        "payment_status": payment_status or "pending",
        "payment_amount": payment_amount,
        "payment_method": payment_method,
        "copay_collected": copay_collected,
        "wd_verified": wd_verified,
        "patient_signed": patient_signed,
    }
    result = await supa.update("visits", "visit_id", visit_id, updates)
    await _append_event("PATIENT_CHECKED_OUT", actor_id, {"visit_id": visit_id, **updates})
    return result


async def delete_visit(db, visit_id: str, actor_id: str) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    visit = rows[0]
    if visit["status"] in ("checked_in", "in_service"):
        raise ValueError("Cannot delete active visit")
    await supa.delete("visits", "visit_id", visit_id)
    await _append_event("VISIT_DELETED", actor_id, {"visit_id": visit_id})
    return visit


async def get_active_visits(db) -> list:
    supa = get_supabase()
    rows = await supa.select("visits", {})
    return [v for v in rows if v.get("status") in ("checked_in", "in_service", "service_completed")]


async def get_patient_visits(db, patient_id: str) -> list:
    """All visits for a patient, newest first. Includes treatments for PDF generation."""
    supa = get_supabase()
    rows = await supa.select("visits", {"patient_id": patient_id})
    sorted_visits = sorted(rows, key=lambda v: v.get("check_in_time") or "", reverse=True)
    
    # Enrich each visit with treatments
    for visit in sorted_visits:
        treatments = await supa.select("visit_treatments", {"visit_id": visit["visit_id"]})
        visit["treatments"] = treatments or []
    
    return sorted_visits


async def get_daily_summary(db, date: Optional[str] = None) -> dict:
    """Summary of all visits for a given date with copay totals."""
    from datetime import datetime, timezone
    target_date = date or datetime.now(timezone.utc).date().isoformat()
    supa = get_supabase()
    all_visits = await supa.select("visits", {})
    today_visits = [
        v for v in all_visits
        if (v.get("check_in_time") or "")[:10] == target_date
    ]
    checked_out = [v for v in today_visits if v.get("status") == "checked_out"]
    active = [v for v in today_visits if v.get("status") in ("checked_in", "in_service", "service_completed")]
    copay_total = sum((v.get("copay_collected") or 0) for v in checked_out)
    payment_total = sum((v.get("payment_amount") or 0) for v in checked_out if v.get("payment_amount"))

    by_service: dict = {}
    for v in today_visits:
        svc = v.get("service_type") or "unknown"
        by_service[svc] = by_service.get(svc, 0) + 1

    all_staff = await supa.select("staff", {})
    staff_map = {s["staff_id"]: s["name"] for s in all_staff}

    for v in today_visits:
        v["staff_name"] = staff_map.get(v.get("staff_id"), "-")

    return {
        "date": target_date,
        "total_check_ins": len(today_visits),
        "total_checked_out": len(checked_out),
        "active_visits": len(active),
        "copay_total": round(float(copay_total), 2),
        "payment_total": round(float(payment_total), 2),
        "by_service_type": by_service,
        "visits": sorted(today_visits, key=lambda v: v.get("check_in_time") or ""),
    }


# ==================== PATIENTS ====================

async def create_patient(db, actor_id: str, data: dict, force: bool = False) -> dict:
    supa = get_supabase()
    patient = {
        "patient_id": _new_id(),
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "date_of_birth": data.get("date_of_birth"),
        "gender": data.get("gender"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "address": data.get("address"),
        "mrn": data.get("mrn"),
        "intake_status": data.get("intake_status", "pending"),
        "consent_status": data.get("consent_status", "pending"),
        "notes": data.get("notes"),
        "active": True,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    result = await supa.insert("patients", patient)
    await _append_event("PATIENT_CREATED", actor_id, {"patient_id": result["patient_id"]})
    return _with_full_name(result)


async def list_patients(db) -> list:
    supa = get_supabase()
    rows = await supa.select("patients", {"active": True})
    return [_with_full_name(p) for p in rows]


async def search_patients(db, query: str) -> list:
    supa = get_supabase()
    # Use PostgREST full-text search via ilike
    import httpx
    client = supa._client
    url = f"{supa._url}/rest/v1/patients"
    params = {
        "select": "*",
        "active": "eq.true",
        "or": f"(first_name.ilike.*{query}*,last_name.ilike.*{query}*,phone.ilike.*{query}*,mrn.ilike.*{query}*)",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    return [_with_full_name(p) for p in r.json()]


async def get_patient(db, patient_id: str) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("patients", {"patient_id": patient_id})
    return _with_full_name(rows[0]) if rows else None


async def update_patient(db, patient_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("patients", "patient_id", patient_id, updates)
    if not result:
        return None
    await _append_event("PATIENT_UPDATED", actor_id, {"patient_id": patient_id})
    return _with_full_name(result)


async def delete_patient(db, patient_id: str, actor_id: str) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("patients", {"patient_id": patient_id})
    if not rows:
        return None
    await supa.update("patients", "patient_id", patient_id, {"active": False, "updated_at": _utc_now()})
    await _append_event("PATIENT_DELETED", actor_id, {"patient_id": patient_id})
    return _with_full_name(rows[0])


# ==================== APPOINTMENTS ====================

async def create_appointment(db, actor_id: str, data: dict) -> dict:
    supa = get_supabase()
    appt = {
        "appointment_id": _new_id(),
        "patient_id": data["patient_id"],
        "provider_id": data.get("provider_id"),
        "appointment_date": data["appointment_date"],
        "appointment_time": data.get("appointment_time"),
        "appointment_type": data.get("appointment_type", "regular"),
        "status": data.get("status", "scheduled"),
        "notes": data.get("notes"),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    result = await supa.insert("appointments", appt)
    await _append_event("APPOINTMENT_CREATED", actor_id, {"appointment_id": result["appointment_id"]})
    return result


async def list_appointments(db, date: Optional[str] = None, patient_id: Optional[str] = None,
                            provider_id: Optional[str] = None) -> list:
    supa = get_supabase()
    filters = {}
    if date:
        filters["appointment_date"] = date
    if patient_id:
        filters["patient_id"] = patient_id
    if provider_id:
        filters["provider_id"] = provider_id
    return await supa.select("appointments", filters)


async def update_appointment(db, appointment_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("appointments", "appointment_id", appointment_id, updates)
    if not result:
        return None
    await _append_event("APPOINTMENT_UPDATED", actor_id, {"appointment_id": appointment_id})
    return result


async def cancel_appointment(db, appointment_id: str, actor_id: str, reason: Optional[str] = None) -> Optional[dict]:
    return await update_appointment(db, appointment_id, actor_id, {"status": "cancelled", "cancellation_reason": reason})


async def mark_no_show(db, appointment_id: str, actor_id: str) -> Optional[dict]:
    return await update_appointment(db, appointment_id, actor_id, {"status": "no_show"})


# ==================== CLINICAL NOTES ====================

async def create_note(db, actor_id: str, data: dict) -> dict:
    supa = get_supabase()
    note = {
        "note_id": _new_id(),
        "visit_id": data["visit_id"],
        "patient_id": data.get("patient_id"),
        "provider_id": data.get("provider_id"),
        "template_type": data.get("template_type"),
        "status": "draft",
        "content": data.get("content"),
        "raw_input": data.get("raw_input"),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    result = await supa.insert("clinical_notes", note)
    await _append_event("NOTE_CREATED", actor_id, {"note_id": result["note_id"]})
    return result


async def list_notes(db, visit_id: Optional[str] = None, patient_id: Optional[str] = None) -> list:
    supa = get_supabase()
    filters = {}
    if visit_id:
        filters["visit_id"] = visit_id
    if patient_id:
        filters["patient_id"] = patient_id
    return await supa.select("clinical_notes", filters)


async def update_note(db, note_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("clinical_notes", "note_id", note_id, updates)
    if not result:
        return None
    await _append_event("NOTE_UPDATED", actor_id, {"note_id": note_id})
    return result


async def sign_note(db, note_id: str, actor_id: str) -> Optional[dict]:
    return await update_note(db, note_id, actor_id, {"status": "signed", "signed_at": _utc_now(), "signed_by": actor_id})


# ==================== INSURANCE ====================

async def create_insurance_policy(db, actor_id: str, data: dict) -> dict:
    supa = get_supabase()
    policy = {
        "policy_id": _new_id(),
        "patient_id": data["patient_id"],
        "carrier_name": data["carrier_name"],
        "member_id": data.get("member_id"),
        "group_number": data.get("group_number"),
        "plan_type": data.get("plan_type"),
        "copay_amount": data.get("copay_amount"),
        "deductible": data.get("deductible"),
        "priority": data.get("priority", "primary"),
        "eligibility_status": data.get("eligibility_status", "unknown"),
        "visits_authorized": data.get("visits_authorized"),
        "visits_used": data.get("visits_used"),
        "active": True,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    result = await supa.insert("insurance_policies", policy)
    await _append_event("INSURANCE_CREATED", actor_id, {"policy_id": result["policy_id"]})
    return result


async def list_insurance_policies(db, patient_id: str) -> list:
    supa = get_supabase()
    return await supa.select("insurance_policies", {"patient_id": patient_id, "active": True})


async def update_insurance_policy(db, policy_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("insurance_policies", "policy_id", policy_id, updates)
    if not result:
        return None
    await _append_event("INSURANCE_UPDATED", actor_id, {"policy_id": policy_id})
    return result


# ==================== DOCUMENTS ====================

async def create_document(db, actor_id: str, data: dict) -> dict:
    supa = get_supabase()
    doc = {
        "document_id": _new_id(),
        "patient_id": data["patient_id"],
        "visit_id": data.get("visit_id"),
        "document_type": data["document_type"],
        "template_id": data.get("template_id"),
        "sequence_number": data.get("sequence_number", 1),
        "status": "draft",
        "version": 1,
        "file_ref": data.get("file_ref"),
        "metadata": data.get("metadata_"),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    result = await supa.insert("documents", doc)
    await _append_event("DOCUMENT_CREATED", actor_id, {"document_id": result["document_id"]})
    return result


async def list_documents(db, patient_id: str, document_type: Optional[str] = None) -> list:
    supa = get_supabase()
    filters = {"patient_id": patient_id}
    if document_type:
        filters["document_type"] = document_type
    return await supa.select("documents", filters)


async def update_document(db, document_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("documents", "document_id", document_id, updates)
    if not result:
        return None
    await _append_event("DOCUMENT_UPDATED", actor_id, {"document_id": document_id})
    return result


async def sign_document(db, document_id: str, actor_id: str) -> Optional[dict]:
    return await update_document(db, document_id, actor_id, {"status": "signed", "signed_at": _utc_now(), "signed_by": actor_id})


# ==================== TASKS ====================

async def create_task(db, actor_id: str, data: dict) -> dict:
    supa = get_supabase()
    task = {
        "task_id": _new_id(),
        "patient_id": data.get("patient_id"),
        "visit_id": data.get("visit_id"),
        "claim_id": data.get("claim_id"),
        "task_type": data["task_type"],
        "title": data["title"],
        "description": data.get("description"),
        "status": data.get("status", "open"),
        "priority": data.get("priority", "normal"),
        "assignee_id": data.get("assignee_id"),
        "due_date": data.get("due_date"),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    result = await supa.insert("tasks", task)
    await _append_event("TASK_CREATED", actor_id, {"task_id": result["task_id"]})
    return result


async def list_tasks(db, patient_id: Optional[str] = None, assignee_id: Optional[str] = None,
                     status: Optional[str] = None, task_type: Optional[str] = None) -> list:
    supa = get_supabase()
    filters = {}
    if patient_id:
        filters["patient_id"] = patient_id
    if assignee_id:
        filters["assignee_id"] = assignee_id
    if status:
        filters["status"] = status
    if task_type:
        filters["task_type"] = task_type
    return await supa.select("tasks", filters)


async def update_task(db, task_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("tasks", "task_id", task_id, updates)
    if not result:
        return None
    await _append_event("TASK_UPDATED", actor_id, {"task_id": task_id})
    return result


# ==================== EVENTS ====================

async def get_events(db) -> list:
    supa = get_supabase()
    return await supa.select("event_log")


# ==================== REPORTS ====================

async def generate_daily_report(db, actor_id: str, report_date: Optional[str] = None) -> dict:
    from datetime import date as _date
    supa = get_supabase()
    today = report_date or _date.today().isoformat()

    visits = await supa.select("visits")
    today_visits = [v for v in visits if (v.get("check_in_time") or "").startswith(today)]

    appts = await supa.select("appointments", {"appointment_date": today})

    report_data = {
        "date": today,
        "visits": [v["visit_id"] for v in today_visits],
        "appointments_count": len(appts),
    }

    report = {
        "report_date": today,
        "total_check_ins": len([v for v in today_visits if v.get("check_in_time")]),
        "total_check_outs": len([v for v in today_visits if v.get("status") == "checked_out"]),
        "total_services_completed": len([v for v in today_visits if v.get("service_end_time")]),
        "total_appointments": len(appts),
        "no_shows": len([a for a in appts if a.get("status") == "no_show"]),
        "open_sessions": len([v for v in today_visits if v.get("status") in ("checked_in", "in_service")]),
        "report_data": report_data,
        "generated_at": _utc_now(),
    }
    result = await supa.insert("daily_reports", report)
    await _append_event("REPORT_GENERATED", actor_id, {"date": today})
    return result


async def get_daily_report(db, report_date: Optional[str] = None) -> Optional[dict]:
    from datetime import date as _date
    supa = get_supabase()
    today = report_date or _date.today().isoformat()
    rows = await supa.select("daily_reports", {"report_date": today})
    return rows[-1] if rows else None


# ===================== TREATMENTS (PRD-005) =====================

async def add_treatment(
    db,
    visit_id: str,
    modality: str,
    actor_id: str,
    therapist_id: Optional[str] = None,
    duration_minutes: Optional[int] = 30,
    notes: Optional[str] = None
) -> dict:
    """Add a treatment modality to a visit."""
    supa = get_supabase()
    
    # Verify visit exists and is active
    visits = await supa.select("visits", {"visit_id": visit_id})
    if not visits:
        raise ValueError(f"Visit {visit_id} not found")
    visit = visits[0]
    if visit.get("status") not in ("checked_in", "in_service", "service_completed"):
        raise ValueError(f"Cannot add treatment to visit with status {visit.get('status')}")
    
    treatment = {
        "treatment_id": _new_id(),
        "visit_id": visit_id,
        "modality": modality,
        "therapist_id": therapist_id or actor_id,
        "duration_minutes": duration_minutes,
        "notes": notes,
        "started_at": _utc_now(),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }
    
    result = await supa.insert("visit_treatments", treatment)
    
    await _append_event("TREATMENT_ADDED", actor_id, {
        "treatment_id": treatment["treatment_id"],
        "visit_id": visit_id,
        "modality": modality,
        "therapist_id": therapist_id,
        "duration_minutes": duration_minutes,
    })
    
    return result


async def update_treatment(
    db,
    treatment_id: str,
    actor_id: str,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None
) -> dict:
    """Update treatment duration and notes."""
    supa = get_supabase()
    
    treatments = await supa.select("visit_treatments", {"treatment_id": treatment_id})
    if not treatments:
        raise ValueError(f"Treatment {treatment_id} not found")
    
    updates = {"updated_at": _utc_now()}
    payload_updates = {}
    
    if duration_minutes is not None:
        updates["duration_minutes"] = duration_minutes
        payload_updates["duration_minutes"] = duration_minutes
    if notes is not None:
        updates["notes"] = notes
        payload_updates["notes"] = notes
    
    result = await supa.update("visit_treatments", {"treatment_id": treatment_id}, updates)
    
    await _append_event("TREATMENT_UPDATED", actor_id, {
        "treatment_id": treatment_id,
        "updates": payload_updates,
    })
    
    return result


async def delete_treatment(db, treatment_id: str, actor_id: str) -> dict:
    """Soft delete a treatment."""
    supa = get_supabase()
    
    treatments = await supa.select("visit_treatments", {"treatment_id": treatment_id})
    if not treatments:
        raise ValueError(f"Treatment {treatment_id} not found")
    
    treatment = treatments[0]
    
    await _append_event("TREATMENT_DELETED", actor_id, {
        "treatment_id": treatment_id,
        "visit_id": treatment.get("visit_id"),
    })
    
    await supa.delete("visit_treatments", {"treatment_id": treatment_id})
    
    return {"deleted": True, "treatment_id": treatment_id}


async def list_visit_treatments(db, visit_id: str) -> list:
    """List all treatments for a visit."""
    supa = get_supabase()
    
    treatments = await supa.select("visit_treatments", {"visit_id": visit_id})
    
    # Enrich with therapist names
    enriched = []
    for t in treatments:
        if t.get("therapist_id"):
            staff_rows = await supa.select("staff", {"staff_id": t["therapist_id"]})
            if staff_rows:
                t["therapist_name"] = staff_rows[0].get("name")
        enriched.append(t)
    
    return enriched


async def list_treatment_records(
    db,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    modality: Optional[str] = None
) -> list:
    """Query treatment records with filters."""
    supa = get_supabase()
    
    # Get all treatments first
    treatments = await supa.select("visit_treatments", {})
    
    # Filter and enrich
    enriched = []
    for t in treatments:
        # Get visit details
        visit_rows = await supa.select("visits", {"visit_id": t["visit_id"]})
        if not visit_rows:
            continue
        visit = visit_rows[0]
        
        # Apply filters
        if date_from and visit.get("check_in_time", "") < date_from:
            continue
        if date_to and visit.get("check_in_time", "") > date_to + " 23:59:59":
            continue
        if patient_id and visit.get("patient_id") != patient_id:
            continue
        if staff_id and t.get("therapist_id") != staff_id:
            continue
        if modality and t.get("modality") != modality:
            continue
        
        # Enrich with related data
        t["visit_date"] = visit.get("check_in_time")
        t["visit_status"] = visit.get("status")
        
        # Get patient name
        if visit.get("patient_id"):
            patient_rows = await supa.select("patients", {"patient_id": visit["patient_id"]})
            if patient_rows:
                p = patient_rows[0]
                t["patient_name"] = f"{p.get('first_name', '')} {p.get('last_name', '')}"
        
        # Get room name
        if visit.get("room_id"):
            room_rows = await supa.select("rooms", {"room_id": visit["room_id"]})
            if room_rows:
                t["room_name"] = room_rows[0].get("name")
                t["room_code"] = room_rows[0].get("code")
        
        # Get therapist name
        if t.get("therapist_id"):
            staff_rows = await supa.select("staff", {"staff_id": t["therapist_id"]})
            if staff_rows:
                t["therapist_name"] = staff_rows[0].get("name")
        
        enriched.append(t)
    
    # Sort by visit date descending
    enriched.sort(key=lambda x: x.get("visit_date", ""), reverse=True)
    
    return enriched
