from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PrototypeStore:
    def __init__(self) -> None:
        self.rooms: dict[str, dict[str, Any]] = {}
        self.staff: dict[str, dict[str, Any]] = {}
        self.visits: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.daily_reports: dict[str, dict[str, Any]] = {}

    def _append_event(self, event_type: str, actor_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "occurred_at": _utc_now(),
            "actor_id": actor_id,
            "idempotency_key": str(uuid4()),
            "payload": payload,
        }
        self.events.append(event)
        return event

    def create_room(self, actor_id: str, data: dict[str, Any]) -> dict[str, Any]:
        room_id = str(uuid4())
        room = {
            "room_id": room_id,
            "name": data["name"],
            "code": data["code"],
            "room_type": data.get("room_type", "treatment"),
            "active": data.get("active", True),
            "status": "available",
            "updated_at": _utc_now(),
        }
        self.rooms[room_id] = room
        self._append_event("ROOM_CREATED", actor_id, room)
        return room

    def update_room(self, room_id: str, actor_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        room = self.rooms.get(room_id)
        if not room:
            return None
        for key, value in updates.items():
            if value is not None:
                room[key] = value
        room["updated_at"] = _utc_now()
        self._append_event("ROOM_UPDATED", actor_id, {"room_id": room_id, "updates": updates})
        return room

    def create_staff(self, actor_id: str, data: dict[str, Any]) -> dict[str, Any]:
        staff_id = str(uuid4())
        staff = {
            "staff_id": staff_id,
            "name": data["name"],
            "role": data["role"],
            "license_id": data.get("license_id"),
            "active": data.get("active", True),
            "updated_at": _utc_now(),
        }
        self.staff[staff_id] = staff
        self._append_event("STAFF_CREATED", actor_id, staff)
        return staff

    def update_staff(self, staff_id: str, actor_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        staff = self.staff.get(staff_id)
        if not staff:
            return None
        for key, value in updates.items():
            if value is not None:
                staff[key] = value
        staff["updated_at"] = _utc_now()
        self._append_event("STAFF_UPDATED", actor_id, {"staff_id": staff_id, "updates": updates})
        return staff

    def patient_checkin(self, actor_id: str, patient_name: str, patient_ref: str | None) -> dict[str, Any]:
        visit_id = str(uuid4())
        visit = {
            "visit_id": visit_id,
            "patient_name": patient_name,
            "patient_ref": patient_ref,
            "status": "checked_in",
            "check_in_time": _utc_now(),
            "service_type": None,
            "service_start_time": None,
            "service_end_time": None,
            "check_out_time": None,
            "staff_id": None,
            "room_id": None,
        }
        self.visits[visit_id] = visit
        self._append_event("PATIENT_CHECKIN", actor_id, visit)
        return visit

    def service_start(
        self, visit_id: str, actor_id: str, staff_id: str, room_id: str, service_type: str
    ) -> dict[str, Any] | None:
        visit = self.visits.get(visit_id)
        if not visit or staff_id not in self.staff or room_id not in self.rooms:
            return None
        visit["staff_id"] = staff_id
        visit["room_id"] = room_id
        visit["service_type"] = service_type
        visit["service_start_time"] = _utc_now()
        visit["status"] = "in_service"
        self.rooms[room_id]["status"] = "occupied"
        self.rooms[room_id]["updated_at"] = _utc_now()
        self._append_event(
            "SERVICE_STARTED",
            actor_id,
            {
                "visit_id": visit_id,
                "staff_id": staff_id,
                "room_id": room_id,
                "service_type": service_type,
                "service_start_time": visit["service_start_time"],
            },
        )
        return visit

    def service_end(self, visit_id: str, actor_id: str) -> dict[str, Any] | None:
        visit = self.visits.get(visit_id)
        if not visit or not visit.get("service_start_time"):
            return None
        visit["service_end_time"] = _utc_now()
        visit["status"] = "service_completed"
        duration_minutes = int((visit["service_end_time"] - visit["service_start_time"]).total_seconds() // 60)
        room_id = visit.get("room_id")
        if room_id and room_id in self.rooms:
            self.rooms[room_id]["status"] = "available"
            self.rooms[room_id]["updated_at"] = _utc_now()
        self._append_event(
            "SERVICE_COMPLETED",
            actor_id,
            {
                "visit_id": visit_id,
                "staff_id": visit.get("staff_id"),
                "room_id": room_id,
                "service_type": visit.get("service_type"),
                "duration_minutes": max(duration_minutes, 0),
                "service_end_time": visit["service_end_time"],
            },
        )
        return visit

    def patient_checkout(self, visit_id: str, actor_id: str) -> dict[str, Any] | None:
        visit = self.visits.get(visit_id)
        if not visit:
            return None
        visit["check_out_time"] = _utc_now()
        visit["status"] = "checked_out"
        self._append_event("PATIENT_CHECKOUT", actor_id, {"visit_id": visit_id, "check_out_time": visit["check_out_time"]})
        return visit

    def change_room_status(self, room_id: str, actor_id: str, status: str) -> dict[str, Any] | None:
        room = self.rooms.get(room_id)
        if not room:
            return None
        room["status"] = status
        room["updated_at"] = _utc_now()
        self._append_event("ROOM_STATUS_CHANGED", actor_id, {"room_id": room_id, "status": status})
        return room

    def room_board(self) -> list[dict[str, Any]]:
        active_visits_by_room = {
            visit["room_id"]: visit
            for visit in self.visits.values()
            if visit.get("room_id") and visit["status"] in {"in_service", "checked_in", "service_completed"}
        }
        board = []
        for room in self.rooms.values():
            visit = active_visits_by_room.get(room["room_id"])
            board.append(
                {
                    "room_id": room["room_id"],
                    "code": room["code"],
                    "name": room["name"],
                    "status": room["status"],
                    "patient_name": visit.get("patient_name") if visit else None,
                    "visit_id": visit.get("visit_id") if visit else None,
                }
            )
        return board

    def staff_hours_today(self) -> list:
        today = _utc_now().date().isoformat()
        now = _utc_now()
        per_staff = {}
        for member in self.staff.values():
            per_staff[member["staff_id"]] = {
                "staff_id": member["staff_id"],
                "name": member["name"],
                "role": member["role"],
                "completed_minutes": 0,
                "active_minutes": 0,
                "sessions_completed": 0,
            }

        for visit in self.visits.values():
            staff_id = visit.get("staff_id")
            if not staff_id or staff_id not in per_staff:
                continue
            start = visit.get("service_start_time")
            end = visit.get("service_end_time")
            if start and start.date().isoformat() == today:
                if end:
                    seconds = (end - start).total_seconds()
                    per_staff[staff_id]["completed_minutes"] += max(int(seconds // 60), 0)
                    per_staff[staff_id]["sessions_completed"] += 1
                elif visit.get("status") == "in_service":
                    live_seconds = (now - start).total_seconds()
                    per_staff[staff_id]["active_minutes"] += max(int(live_seconds // 60), 0)

        return list(per_staff.values())

    def generate_daily_report(self, actor_id, report_date=None):
        target_date = report_date or _utc_now().date().isoformat()
        visits = [
            visit
            for visit in self.visits.values()
            if visit.get("check_in_time") and visit["check_in_time"].date().isoformat() == target_date
        ]
        completed = [v for v in visits if v.get("service_end_time")]
        open_sessions = [v for v in visits if v.get("service_start_time") and not v.get("service_end_time")]
        report = {
            "date": target_date,
            "total_check_ins": len(visits),
            "total_check_outs": len([v for v in visits if v.get("check_out_time")]),
            "total_services_completed": len(completed),
            "open_sessions": len(open_sessions),
            "staff_hours": self.staff_hours_today(),
            "room_board_snapshot": self.room_board(),
            "generated_at": _utc_now(),
        }
        self.daily_reports[target_date] = report
        self._append_event("DAILY_REPORT_GENERATED", actor_id, report)
        return report

    def get_daily_report(self, report_date=None):
        target_date = report_date or _utc_now().date().isoformat()
        return self.daily_reports.get(target_date)


prototype_store = PrototypeStore()
