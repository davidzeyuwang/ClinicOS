"""Pytest E2E coverage for the ClinicOS prototype API."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        response = test_client.post("/prototype/test/reset")
        assert response.status_code == 200
        yield test_client


def post_json(client: TestClient, path: str, payload: dict) -> dict:
    response = client.post(f"/prototype{path}", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def get_json(client: TestClient, path: str) -> dict:
    response = client.get(f"/prototype{path}")
    assert response.status_code == 200, response.text
    return response.json()


def patch_json(client: TestClient, path: str, payload: dict) -> dict:
    response = client.patch(f"/prototype{path}", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_prd_v2_e2e_domain_flow(client: TestClient):
    # ==================== ROOMS & STAFF (§11.3) ====================
    r1 = post_json(client, "/admin/rooms", {"name": "Room 1", "code": "R1", "room_type": "treatment"})
    r2 = post_json(client, "/admin/rooms", {"name": "Room 2", "code": "R2", "room_type": "treatment"})
    assert r1["status"] == "available"
    assert r2["status"] == "available"

    s1 = post_json(client, "/admin/staff", {"name": "Bob OT", "role": "therapist", "license_id": "OT-002"})
    assert s1["active"] is True
    assert s1["role"] == "therapist"

    # ==================== PATIENT (§11.1) ====================
    p1 = post_json(
        client,
        "/patients",
        {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1985-06-15",
            "phone": "555-0101",
            "mrn": "MRN-1001",
        },
    )
    assert p1["first_name"] == "John"
    assert p1["intake_status"] == "pending"

    search = get_json(client, "/patients?q=Doe")
    assert len(search["patients"]) >= 1
    assert search["patients"][0]["last_name"] == "Doe"

    # ==================== INSURANCE (§11.7) ====================
    ins1 = post_json(
        client,
        "/insurance",
        {
            "patient_id": p1["patient_id"],
            "carrier_name": "Blue Cross",
            "member_id": "BC-123456",
            "group_number": "GRP-789",
            "copay_amount": 30.0,
            "visits_authorized": 24,
        },
    )
    assert ins1["carrier_name"] == "Blue Cross"
    assert ins1["eligibility_status"] == "unknown"

    ins1_updated = patch_json(
        client,
        f"/insurance/{ins1['policy_id']}/update",
        {
            "eligibility_status": "verified",
            "eligibility_notes": "Verified via portal - 24 visits authorized",
            "visits_used": 3,
        },
    )
    assert ins1_updated["eligibility_status"] == "verified"
    assert ins1_updated["eligibility_verified_at"] is not None

    # ==================== APPOINTMENT (§11.2) ====================
    today = date.today().isoformat()
    appt1 = post_json(
        client,
        "/appointments",
        {
            "patient_id": p1["patient_id"],
            "provider_id": s1["staff_id"],
            "appointment_date": today,
            "appointment_time": "10:00",
            "appointment_type": "regular",
        },
    )
    assert appt1["status"] == "scheduled"

    appts = get_json(client, f"/appointments?date={today}")
    assert len(appts["appointments"]) >= 1

    # ==================== CHECK-IN + VISIT (§11.3, §11.5) ====================
    v1 = post_json(
        client,
        "/portal/checkin",
        {
            "patient_name": "John Doe",
            "patient_ref": "MRN-1001",
            "patient_id": p1["patient_id"],
            "appointment_id": appt1["appointment_id"],
            "actor_id": "frontdesk-1",
        },
    )
    assert v1["status"] == "checked_in"
    assert v1["patient_id"] == p1["patient_id"]
    assert v1["appointment_id"] == appt1["appointment_id"]

    # ==================== DOCUMENT (§11.4) ====================
    doc1 = post_json(
        client,
        "/documents",
        {
            "patient_id": p1["patient_id"],
            "visit_id": v1["visit_id"],
            "document_type": "intake",
        },
    )
    assert doc1["document_type"] == "intake"
    assert doc1["sequence_number"] == 1
    assert doc1["status"] == "draft"

    doc1_signed = post_json(
        client,
        f"/documents/{doc1['document_id']}/sign",
        {"document_id": doc1["document_id"], "actor_id": "patient-john"},
    )
    assert doc1_signed["status"] == "signed"

    doc2 = post_json(client, "/documents", {"patient_id": p1["patient_id"], "document_type": "consent"})
    assert doc2["sequence_number"] == 1

    doc3 = post_json(client, "/documents", {"patient_id": p1["patient_id"], "document_type": "intake"})
    assert doc3["sequence_number"] == 2

    # ==================== SERVICE (§11.3) ====================
    svc = post_json(
        client,
        "/portal/service/start",
        {
            "visit_id": v1["visit_id"],
            "staff_id": s1["staff_id"],
            "room_id": r1["room_id"],
            "service_type": "PT",
            "actor_id": "therapist-1",
        },
    )
    assert svc["status"] == "in_service"

    board = get_json(client, "/projections/room-board")
    r1_board = [r for r in board["rooms"] if r["room_id"] == r1["room_id"]][0]
    assert r1_board["status"] == "occupied"
    assert r1_board["patient_name"] == "John Doe"

    end = post_json(client, "/portal/service/end", {"visit_id": v1["visit_id"], "actor_id": "therapist-1"})
    assert end["status"] == "service_completed"

    # ==================== CLINICAL NOTE (§11.6) ====================
    note1 = post_json(
        client,
        "/notes",
        {
            "visit_id": v1["visit_id"],
            "patient_id": p1["patient_id"],
            "provider_id": s1["staff_id"],
            "template_type": "SOAP",
            "content": {
                "subjective": "Patient reports lower back pain",
                "objective": "ROM limited, tenderness L4-L5",
                "assessment": "Lumbar strain",
                "plan": "Continue PT 2x/week",
            },
        },
    )
    assert note1["status"] == "draft"

    note1_signed = post_json(
        client,
        f"/notes/{note1['note_id']}/sign",
        {"note_id": note1["note_id"], "actor_id": s1["staff_id"]},
    )
    assert note1_signed["status"] == "signed"

    # ==================== CHECKOUT WITH PAYMENT (§11.3) ====================
    co = post_json(
        client,
        "/portal/checkout",
        {
            "visit_id": v1["visit_id"],
            "payment_status": "copay_collected",
            "payment_amount": 30.0,
            "payment_method": "card",
            "actor_id": "frontdesk-1",
        },
    )
    assert co["status"] == "checked_out"
    assert co["payment_status"] == "copay_collected"
    assert co["payment_amount"] == 30.0

    # ==================== TASK (§11.9) ====================
    task1 = post_json(
        client,
        "/tasks",
        {
            "patient_id": p1["patient_id"],
            "visit_id": v1["visit_id"],
            "task_type": "insurance_followup",
            "title": "Submit claim for John Doe PT session",
            "priority": "high",
            "assignee_id": "backoffice-1",
        },
    )
    assert task1["status"] == "open"
    assert task1["priority"] == "high"

    task1_done = patch_json(client, f"/tasks/{task1['task_id']}", {"status": "completed"})
    assert task1_done["status"] == "completed"
    assert task1_done["completed_at"] is not None

    # ==================== STAFF HOURS + REPORT ====================
    hours = get_json(client, "/projections/staff-hours")
    bob_hours = [st for st in hours["staff"] if st["staff_id"] == s1["staff_id"]][0]
    assert bob_hours["sessions_completed"] >= 1

    report = post_json(client, "/reports/daily/generate", {"actor_id": "manager-1"})
    assert report["total_check_ins"] >= 1
    assert report["total_check_outs"] >= 1
    assert report["total_services_completed"] >= 1

    # ==================== EVENT LOG ====================
    events = get_json(client, "/events")
    event_types = {event["event_type"] for event in events["events"]}
    expected_types = {
        "ROOM_CREATED",
        "STAFF_CREATED",
        "PATIENT_CREATED",
        "PATIENT_CHECKIN",
        "SERVICE_STARTED",
        "SERVICE_COMPLETED",
        "PATIENT_CHECKOUT",
        "NOTE_CREATED",
        "NOTE_SIGNED",
        "DOCUMENT_CREATED",
        "DOCUMENT_SIGNED",
        "TASK_CREATED",
        "TASK_UPDATED",
        "APPOINTMENT_CREATED",
        "INSURANCE_POLICY_CREATED",
        "INSURANCE_POLICY_UPDATED",
        "PAYMENT_RECORDED",
        "DAILY_REPORT_GENERATED",
    }
    assert expected_types.issubset(event_types)
