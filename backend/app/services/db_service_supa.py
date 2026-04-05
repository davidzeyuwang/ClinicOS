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

async def create_room(db, actor_id: str, data: dict, **_) -> dict:
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


async def update_room(db, room_id: str, actor_id: str, updates: dict, **_) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("rooms", "room_id", room_id, updates)
    if not result:
        return None
    await _append_event("ROOM_UPDATED", actor_id, {"room_id": room_id, "updates": updates})
    return result


async def delete_room(db, room_id: str, actor_id: str, **_) -> Optional[dict]:
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


async def change_room_status(db, room_id: str, actor_id: str, status: str, **_) -> Optional[dict]:
    supa = get_supabase()
    result = await supa.update("rooms", "room_id", room_id, {"status": status, "updated_at": _utc_now()})
    if not result:
        return None
    await _append_event("ROOM_STATUS_CHANGED", actor_id, {"room_id": room_id, "status": status})
    return result


async def get_room_board(db, **_) -> list:
    """Room board projection - parallel fetch: rooms + active visits concurrently."""
    supa = get_supabase()

    # Fetch rooms and active visits concurrently to minimize latency
    all_rooms, active_visits = await asyncio.gather(
        supa.select("rooms", {}),
        supa.select("visits", status_in=["in_service"], limit=500),
    )
    rooms = [r for r in all_rooms if r.get("active") is True]
    active_visits = [v for v in active_visits if v.get("room_id")]

    # Build room -> visit mapping
    visits_by_room = {v["room_id"]: v for v in active_visits}

    for room in rooms:
        v = visits_by_room.get(room["room_id"])
        if v:
            room["visit_id"] = v.get("visit_id")
            room["patient_id"] = v.get("patient_id")
            room["patient_name"] = v.get("patient_name")
            room["service_type"] = v.get("service_type")
            room["visit_status"] = v.get("status")
            room["service_start_time"] = v.get("service_start_time")
        else:
            room["visit_id"] = None
            room["patient_id"] = None
            room["patient_name"] = None
            room["service_type"] = None
            room["visit_status"] = None
            room["service_start_time"] = None

    return rooms


# ==================== STAFF ====================

async def create_staff(db, actor_id: str, data: dict, **_) -> dict:
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


async def update_staff(db, staff_id: str, actor_id: str, updates: dict, **_) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("staff", "staff_id", staff_id, updates)
    if not result:
        return None
    await _append_event("STAFF_UPDATED", actor_id, {"staff_id": staff_id})
    return result


async def delete_staff(db, staff_id: str, actor_id: str, **_) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("staff", {"staff_id": staff_id})
    if not rows:
        return None
    await supa.delete("staff", "staff_id", staff_id)
    await _append_event("STAFF_DELETED", actor_id, {"staff_id": staff_id})
    return rows[0]


async def get_staff_hours(db, **_) -> list:
    supa = get_supabase()
    today = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc)

    all_staff, all_visits, all_links, all_types = await asyncio.gather(
        supa.select("staff", {"active": True}),
        supa.select("visits", {}),
        supa.select("staff_service_types", {}),
        supa.select("service_types", {}),
    )

    # Build lookup: service_type_id → name
    type_name_map = {t["service_type_id"]: t["name"] for t in all_types}
    # Build lookup: staff_id → [service_type_names]
    staff_type_names: dict = {}
    for lnk in all_links:
        sid = lnk["staff_id"]
        name = type_name_map.get(lnk["service_type_id"], "")
        staff_type_names.setdefault(sid, []).append(name)

    # Filter today's visits with a staff_id
    today_visits = [
        v for v in all_visits
        if v.get("staff_id") and (v.get("service_start_time") or "")[:10] == today
    ]

    per_staff = {}
    for member in all_staff:
        per_staff[member["staff_id"]] = {
            "staff_id": member["staff_id"],
            "name": member["name"],
            "role": member["role"],
            "completed_minutes": 0,
            "active_minutes": 0,
            "sessions_completed": 0,
            "service_type_names": staff_type_names.get(member["staff_id"], []),
        }

    for visit in today_visits:
        sid = visit.get("staff_id")
        if sid not in per_staff:
            continue
        start_str = visit.get("service_start_time")
        end_str = visit.get("service_end_time")
        if not start_str:
            continue
        try:
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end_str:
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                seconds = (end - start).total_seconds()
                per_staff[sid]["completed_minutes"] += max(int(seconds // 60), 0)
                per_staff[sid]["sessions_completed"] += 1
            elif visit.get("status") == "in_service":
                live_seconds = (now - start).total_seconds()
                per_staff[sid]["active_minutes"] += max(int(live_seconds // 60), 0)
        except (ValueError, TypeError):
            pass

    return list(per_staff.values())



# ==================== SERVICE TYPES ====================

_DEFAULT_SERVICE_TYPES = [
    "PT", "OT", "Eval", "Re-eval", "Acupuncture", "Cupping",
    "Massage", "E-stim", "Speech", "Heat Therapy", "Cold Therapy",
]


async def ensure_default_service_types(db) -> None:
    """Idempotent seed: insert 11 defaults only if table is empty."""
    supa = get_supabase()
    existing = await supa.select("service_types", {})
    if existing:
        return
    for name in _DEFAULT_SERVICE_TYPES:
        await supa.insert("service_types", {
            "service_type_id": _new_id(),
            "name": name,
            "is_active": True,
            "created_at": _utc_now(),
        })


async def list_service_types(db, include_inactive: bool = False) -> list:
    supa = get_supabase()
    filters = {} if include_inactive else {"is_active": True}
    rows = await supa.select("service_types", filters)
    rows.sort(key=lambda r: r.get("name") or "")
    return rows


async def create_service_type(db, actor_id: str, name: str) -> dict:
    supa = get_supabase()
    row = {
        "service_type_id": _new_id(),
        "name": name,
        "is_active": True,
        "created_at": _utc_now(),
    }
    result = await supa.insert("service_types", row)
    await _append_event("SERVICE_TYPE_CREATED", actor_id, {"service_type_id": result["service_type_id"], "name": name})
    return result


async def update_service_type(db, service_type_id: str, actor_id: str, updates: dict) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("service_types", {"service_type_id": service_type_id})
    if not rows:
        return None
    result = await supa.update("service_types", "service_type_id", service_type_id, updates)
    await _append_event("SERVICE_TYPE_UPDATED", actor_id, {"service_type_id": service_type_id, "updates": updates})
    return result


async def get_staff_service_types(db, staff_id: str) -> list:
    """Return list of ServiceType dicts for the given staff member."""
    supa = get_supabase()
    links = await supa.select("staff_service_types", {"staff_id": staff_id})
    if not links:
        return []
    ids = [lnk["service_type_id"] for lnk in links]
    all_types = await supa.select("service_types", {})
    return [t for t in all_types if t["service_type_id"] in ids]


async def set_staff_service_types(db, staff_id: str, service_type_ids: list, actor_id: str, **_) -> dict:
    """Replace all service type qualifications for a staff member (delete + insert)."""
    supa = get_supabase()
    # Delete all existing links for this staff member in one call
    # SupabaseClient.delete(table, pk_col, pk_val) → DELETE /table?pk_col=eq.pk_val
    await supa.delete("staff_service_types", "staff_id", staff_id)
    for sid in service_type_ids:
        await supa.insert("staff_service_types", {
            "staff_id": staff_id,
            "service_type_id": sid,
        })
    await _append_event("STAFF_SERVICE_TYPES_UPDATED", actor_id, {
        "staff_id": staff_id,
        "service_type_ids": service_type_ids,
    })
    return {"staff_id": staff_id, "service_type_ids": service_type_ids}



async def get_service_type_staff(db, service_type_id: str) -> list:
    """Reverse lookup: staff qualified for a service type."""
    supa = get_supabase()
    links = await supa.select("staff_service_types", {"service_type_id": service_type_id})
    if not links:
        return []
    staff_ids = [lnk["staff_id"] for lnk in links]
    all_staff = await supa.select("staff", {"active": True})
    return [s for s in all_staff if s["staff_id"] in staff_ids]



async def patient_checkin(db, actor_id: str, patient_name: str, patient_ref: Optional[str] = None,
                          patient_id: Optional[str] = None, appointment_id: Optional[str] = None, **_) -> dict:
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
    await _append_event("PATIENT_CHECKIN", actor_id, result)
    return result


async def service_start(db, visit_id: str, actor_id: str, staff_id: Optional[str] = None,
                        room_id: Optional[str] = None, service_type: Optional[str] = None,
                        supervising_staff_id: Optional[str] = None, **_) -> Optional[dict]:
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
    updates["supervising_staff_id"] = supervising_staff_id
    result = await supa.update("visits", "visit_id", visit_id, updates)
    if room_id:
        await supa.update("rooms", "room_id", room_id, {"status": "occupied", "updated_at": _utc_now()})
    await _append_event("SERVICE_STARTED", actor_id, {"visit_id": visit_id, **updates})
    return result


async def service_end(db, visit_id: str, actor_id: str, **_) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    visit = rows[0]
    if visit["status"] != "in_service":
        return None
    updates = {"status": "checked_in", "service_end_time": _utc_now()}
    result = await supa.update("visits", "visit_id", visit_id, updates)
    if visit.get("room_id"):
        await supa.update("rooms", "room_id", visit["room_id"], {"status": "available", "updated_at": _utc_now()})
    await _append_event("SERVICE_COMPLETED", actor_id, {"visit_id": visit_id})
    return result


async def service_resume(db, visit_id: str, actor_id: str, **_) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    visit = rows[0]
    if visit.get("status") != "checked_in" or not visit.get("service_start_time"):
        raise ValueError("Visit is not resumable")
    if not visit.get("staff_id") or not visit.get("room_id") or not visit.get("service_type"):
        return None

    room_rows = await supa.select("rooms", {"room_id": visit["room_id"]}, limit=1)
    if not room_rows:
        return None
    room = room_rows[0]
    if room.get("status") == "occupied":
        occupying_rows = await supa.select("visits", {"room_id": visit["room_id"], "status": "in_service"})
        occupying = next((row for row in occupying_rows if row.get("visit_id") != visit_id), None)
        if occupying:
            raise ValueError(f"Room {room.get('code') or visit['room_id']} is already occupied by another patient")

    now = _utc_now()
    updates = {
        "status": "in_service",
        "service_end_time": None,
    }
    result = await supa.update("visits", "visit_id", visit_id, updates)
    await supa.update("rooms", "room_id", visit["room_id"], {"status": "occupied", "updated_at": now})
    await _append_event("SERVICE_RESUMED", actor_id, {
        "visit_id": visit_id,
        "staff_id": visit.get("staff_id"),
        "room_id": visit.get("room_id"),
        "service_type": visit.get("service_type"),
        "service_start_time": visit.get("service_start_time"),
        "resumed_at": now,
    })
    return result


def _payment_updates(
    payment_status: Optional[str] = None,
    payment_amount: Optional[float] = None,
    payment_method: Optional[str] = None,
    copay_collected: Optional[float] = None,
    wd_verified: bool = False,
    patient_signed: bool = False,
) -> dict:
    updates = {}
    if payment_status:
        updates["payment_status"] = payment_status
    if payment_amount is not None:
        updates["payment_amount"] = payment_amount
    if payment_method is not None:
        updates["payment_method"] = payment_method
    if copay_collected is not None:
        updates["copay_collected"] = copay_collected
    updates["wd_verified"] = wd_verified
    updates["patient_signed"] = patient_signed
    return updates


async def save_visit_payment(db, visit_id: str, actor_id: str, payment_status: Optional[str] = None,
                             payment_amount: Optional[float] = None, payment_method: Optional[str] = None,
                             copay_collected: Optional[float] = None, wd_verified: bool = False,
                             patient_signed: bool = False, **_) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    updates = _payment_updates(
        payment_status=payment_status,
        payment_amount=payment_amount,
        payment_method=payment_method,
        copay_collected=copay_collected,
        wd_verified=wd_verified,
        patient_signed=patient_signed,
    )
    try:
        result = await supa.update("visits", "visit_id", visit_id, updates)
    except Exception:
        core = {k: v for k, v in updates.items()
                if k in ("payment_status", "payment_amount", "payment_method",
                         "copay_collected", "wd_verified", "patient_signed")}
        result = await supa.update("visits", "visit_id", visit_id, core)
    await _append_event("PAYMENT_INFO_SAVED", actor_id, {"visit_id": visit_id, **updates})
    return result


async def patient_checkout(db, visit_id: str, actor_id: str, payment_status: Optional[str] = None,
                           payment_amount: Optional[float] = None, payment_method: Optional[str] = None,
                           copay_collected: Optional[float] = None, wd_verified: bool = False,
                           patient_signed: bool = False, **_) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id})
    if not rows:
        return None
    updates = {
        "status": "checked_out",
        "check_out_time": _utc_now(),
    }
    updates.update(_payment_updates(
        payment_status=payment_status or "pending",
        payment_amount=payment_amount,
        payment_method=payment_method,
        copay_collected=copay_collected,
        wd_verified=wd_verified,
        patient_signed=patient_signed,
    ))

    try:
        result = await supa.update("visits", "visit_id", visit_id, updates)
    except Exception:
        # Fallback: some columns may not exist yet (pending migration) — retry with core fields
        core = {k: v for k, v in updates.items()
                if k in ("status", "check_out_time", "payment_status", "payment_amount",
                         "payment_method", "copay_collected", "wd_verified", "patient_signed")}
        result = await supa.update("visits", "visit_id", visit_id, core)
    await _append_event("PATIENT_CHECKOUT", actor_id, {"visit_id": visit_id})
    return result


async def delete_visit(db, visit_id: str, actor_id: str, **_) -> Optional[dict]:
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


async def get_active_visits(db, **_) -> list:
    """Fetch only active visits using server-side filtering."""
    supa = get_supabase()
    return await supa.select(
        "visits",
        status_in=["checked_in", "in_service", "service_completed"],
        limit=500
    )


async def get_visit(db, visit_id: str, **_) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("visits", {"visit_id": visit_id}, limit=1)
    return rows[0] if rows else None


async def get_patient_visits(db, patient_id: str, **_) -> list:
    """All visits for a patient, newest first. Includes treatments for PDF generation."""
    supa = get_supabase()
    rows = await supa.select("visits", {"patient_id": patient_id})
    sorted_visits = sorted(rows, key=lambda v: v.get("check_in_time") or "", reverse=True)
    
    # Enrich each visit with treatments
    for visit in sorted_visits:
        treatments = await supa.select("visit_treatments", {"visit_id": visit["visit_id"]})
        visit["treatments"] = treatments or []
    
    return sorted_visits


async def get_daily_summary(db, date: Optional[str] = None, **_) -> dict:
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

async def create_patient(db, actor_id: str, data: dict, force: bool = False, clinic_id: str = None) -> dict:
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


async def list_patients(db, clinic_id: str = None) -> list:
    supa = get_supabase()
    all_patients = await supa.select("patients", limit=5000)
    rows = [p for p in all_patients if p.get("active") is True]
    return [_with_full_name(p) for p in rows]


async def search_patients(db, query: str, clinic_id: str = None) -> list:
    supa = get_supabase()
    # Use PostgREST full-text search via ilike
    import httpx
    client = supa._get_client()
    url = f"{supa._url}/rest/v1/patients"
    params = {
        "select": "*",
        "active": "eq.true",
        "or": f"(first_name.ilike.*{query}*,last_name.ilike.*{query}*,phone.ilike.*{query}*,mrn.ilike.*{query}*)",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    return [_with_full_name(p) for p in r.json()]


async def get_patient(db, patient_id: str, clinic_id: str = None) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("patients", {"patient_id": patient_id})
    return _with_full_name(rows[0]) if rows else None


async def update_patient(db, patient_id: str, actor_id: str, updates: dict, clinic_id: str = None) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("patients", "patient_id", patient_id, updates)
    if not result:
        return None
    await _append_event("PATIENT_UPDATED", actor_id, {"patient_id": patient_id})
    return _with_full_name(result)


async def delete_patient(db, patient_id: str, actor_id: str, clinic_id: str = None) -> Optional[dict]:
    supa = get_supabase()
    rows = await supa.select("patients", {"patient_id": patient_id})
    if not rows:
        return None
    await supa.update("patients", "patient_id", patient_id, {"active": False, "updated_at": _utc_now()})
    await _append_event("PATIENT_DELETED", actor_id, {"patient_id": patient_id})
    return _with_full_name(rows[0])


# ==================== APPOINTMENTS ====================

async def create_appointment(db, actor_id: str, data: dict, **_) -> dict:
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
                            provider_id: Optional[str] = None, **_) -> list:
    supa = get_supabase()
    filters = {}
    if date:
        filters["appointment_date"] = date
    if patient_id:
        filters["patient_id"] = patient_id
    if provider_id:
        filters["provider_id"] = provider_id
    return await supa.select("appointments", filters)


async def update_appointment(db, appointment_id: str, actor_id: str, updates: dict, **_) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("appointments", "appointment_id", appointment_id, updates)
    if not result:
        return None
    await _append_event("APPOINTMENT_UPDATED", actor_id, {"appointment_id": appointment_id})
    return result


async def cancel_appointment(db, appointment_id: str, actor_id: str, reason: Optional[str] = None, **_) -> Optional[dict]:
    return await update_appointment(db, appointment_id, actor_id, {"status": "cancelled", "cancellation_reason": reason})


async def mark_no_show(db, appointment_id: str, actor_id: str, **_) -> Optional[dict]:
    return await update_appointment(db, appointment_id, actor_id, {"status": "no_show"})


# ==================== CLINICAL NOTES ====================

async def create_note(db, actor_id: str, data: dict, **_) -> dict:
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


async def list_notes(db, visit_id: Optional[str] = None, patient_id: Optional[str] = None, **_) -> list:
    supa = get_supabase()
    filters = {}
    if visit_id:
        filters["visit_id"] = visit_id
    if patient_id:
        filters["patient_id"] = patient_id
    return await supa.select("clinical_notes", filters)


async def update_note(db, note_id: str, actor_id: str, updates: dict, **_) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("clinical_notes", "note_id", note_id, updates)
    if not result:
        return None
    await _append_event("NOTE_UPDATED", actor_id, {"note_id": note_id})
    return result


async def sign_note(db, note_id: str, actor_id: str, **_) -> Optional[dict]:
    return await update_note(db, note_id, actor_id, {"status": "signed", "signed_at": _utc_now(), "signed_by": actor_id})


# ==================== INSURANCE ====================

async def create_insurance_policy(db, actor_id: str, data: dict, **_) -> dict:
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


async def list_insurance_policies(db, patient_id: str, **_) -> list:
    supa = get_supabase()
    all_policies = await supa.select("insurance_policies", {"patient_id": patient_id}, limit=50)
    return [p for p in all_policies if p.get("active") is True]


async def update_insurance_policy(db, policy_id: str, actor_id: str, updates: dict, **_) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("insurance_policies", "policy_id", policy_id, updates)
    if not result:
        return None
    await _append_event("INSURANCE_UPDATED", actor_id, {"policy_id": policy_id})
    return result


# ==================== DOCUMENTS ====================

async def create_document(db, actor_id: str, data: dict, **_) -> dict:
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


async def list_documents(db, patient_id: str, document_type: Optional[str] = None, **_) -> list:
    supa = get_supabase()
    filters = {"patient_id": patient_id}
    if document_type:
        filters["document_type"] = document_type
    return await supa.select("documents", filters)


async def update_document(db, document_id: str, actor_id: str, updates: dict, **_) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("documents", "document_id", document_id, updates)
    if not result:
        return None
    await _append_event("DOCUMENT_UPDATED", actor_id, {"document_id": document_id})
    return result


async def sign_document(db, document_id: str, actor_id: str, **_) -> Optional[dict]:
    return await update_document(db, document_id, actor_id, {"status": "signed", "signed_at": _utc_now(), "signed_by": actor_id})


# ==================== TASKS ====================

async def create_task(db, actor_id: str, data: dict, **_) -> dict:
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
                     status: Optional[str] = None, task_type: Optional[str] = None, **_) -> list:
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


async def update_task(db, task_id: str, actor_id: str, updates: dict, **_) -> Optional[dict]:
    supa = get_supabase()
    updates["updated_at"] = _utc_now()
    result = await supa.update("tasks", "task_id", task_id, updates)
    if not result:
        return None
    await _append_event("TASK_UPDATED", actor_id, {"task_id": task_id})
    return result


# ==================== EVENTS ====================

async def get_events(db, **_) -> dict:
    supa = get_supabase()
    # Return most-recent 500 events so tests always see latest activity
    client = supa._get_client()
    r = await client.get(
        f"{supa._url}/rest/v1/event_log",
        params={"select": "*", "order": "occurred_at.desc", "limit": 500},
    )
    r.raise_for_status()
    events = r.json()
    return {"count": len(events), "events": events}


# ==================== REPORTS ====================

async def generate_daily_report(db, actor_id: str, report_date: Optional[str] = None, **_) -> dict:
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


async def get_daily_report(db, report_date: Optional[str] = None, **_) -> Optional[dict]:
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
    notes: Optional[str] = None,
    **_,
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
        "therapist_id": therapist_id,
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


async def delete_treatment(db, treatment_id: str, actor_id: str, **_) -> dict:
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


async def list_visit_treatments(db, visit_id: str, **_) -> list:
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
    modality: Optional[str] = None,
    **_,
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


def _modality_to_col(modality: str) -> str:
    m = (modality or "").lower()
    if "acupuncture" in m or m == "a":
        return "A"
    if any(x in m for x in ["pt", "ot", "eval", "physical", "occupational", "speech"]):
        return "PT"
    if any(x in m for x in ["cupping", "cup", "cp"]):
        return "CP"
    if any(x in m for x in ["massage", "tui", "tn"]):
        return "TN"
    return "other"


async def list_visits_with_treatments(
    db,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    patient_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    **_,
) -> list:
    """Return one record per visit with treatments organized by modality column (A/PT/CP/TN)."""
    supa = get_supabase()

    filters: Dict[str, Any] = {}
    if patient_id:
        filters["patient_id"] = patient_id

    visits_raw, all_staff, all_rooms = await asyncio.gather(
        supa.select("visits", filters, limit=2000),
        supa.select("staff", {}),
        supa.select("rooms", {}),
    )

    staff_map = {s["staff_id"]: s["name"] for s in all_staff}
    room_map = {r["room_id"]: r["name"] for r in all_rooms}

    if date_from:
        visits_raw = [v for v in visits_raw if (v.get("check_in_time") or "") >= date_from]
    if date_to:
        visits_raw = [v for v in visits_raw if (v.get("check_in_time") or "") <= date_to + " 23:59:59"]

    visits_raw.sort(key=lambda v: v.get("check_in_time") or "", reverse=True)

    all_treatments = await supa.select("visit_treatments", {}, limit=5000)
    tx_by_visit: Dict[str, list] = {}
    for t in all_treatments:
        vid = t.get("visit_id")
        if vid:
            tx_by_visit.setdefault(vid, []).append(t)

    records = []
    for v in visits_raw:
        treatments = tx_by_visit.get(v["visit_id"], [])

        if staff_id:
            if v.get("staff_id") != staff_id and not any(t.get("therapist_id") == staff_id for t in treatments):
                continue

        col_therapist: Dict[str, str] = {"A": "", "PT": "", "CP": "", "TN": ""}
        col_minutes: Dict[str, int] = {"A": 0, "PT": 0, "CP": 0, "TN": 0}
        other_modalities: list = []
        notes_parts: list = []
        total_minutes = 0

        for t in treatments:
            col = _modality_to_col(t.get("modality") or "")
            tname = staff_map.get(t.get("therapist_id") or "", "")
            dur = t.get("duration_minutes") or 0
            if col == "other":
                other_modalities.append(t.get("modality") or "")
            else:
                if not col_therapist[col]:
                    col_therapist[col] = tname
                col_minutes[col] += dur
            if t.get("notes"):
                notes_parts.append(t["notes"])
            total_minutes += dur

        if not treatments and v.get("service_type"):
            col = _modality_to_col(v["service_type"])
            primary = staff_map.get(v.get("staff_id") or "", "")
            if col in col_therapist:
                col_therapist[col] = primary

        def _col_display(col_key: str) -> str:
            name = col_therapist[col_key]
            mins = col_minutes[col_key]
            if not name and not mins:
                return ""
            if not name:
                return str(mins) + "m"
            return (name + " / " + str(mins) + "m") if mins else name

        records.append({
            "visit_id": v["visit_id"],
            "patient_id": v.get("patient_id"),
            "patient_name": v.get("patient_name") or "",
            "check_in_time": v.get("check_in_time"),
            "status": v.get("status"),
            "supervising_doctor": staff_map.get(v.get("supervising_staff_id") or "", ""),
            "primary_therapist": staff_map.get(v.get("staff_id") or "", ""),
            "room_name": room_map.get(v.get("room_id") or "", ""),
            "service_type": v.get("service_type") or "",
            "A": _col_display("A"),
            "PT": _col_display("PT"),
            "CP": _col_display("CP"),
            "TN": _col_display("TN"),
            "other_modalities": ", ".join(other_modalities),
            "notes": "; ".join(notes_parts),
            "total_minutes": total_minutes,
        })

    return records
