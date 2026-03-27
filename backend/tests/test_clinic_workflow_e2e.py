"""Workflow-oriented E2E test mapped from docs/clinic-workflow.md.

This test covers the portions of the 18-step current-state clinic workflow
that ClinicOS currently implements:

1. Patient intake -> patient master + intake document
2-4. Eligibility task + insurance verification
5. Structured insurance ledger replacement
7. Appointment creation
8-10. Check-in, room board, clinical note
11. Back-office follow-up task as current claim-prep placeholder
18. Day-end reporting and audit trail

Claim submission / EOB reconciliation steps (12-17) are not yet implemented in
the current prototype, so they are intentionally not asserted here.
"""

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


def test_current_clinic_workflow_supported_path(client: TestClient):
    # Step 1: patient intake -> patient master + intake document
    patient = post_json(
        client,
        "/patients",
        {
            "first_name": "Workflow",
            "last_name": "Patient",
            "date_of_birth": "1988-02-14",
            "phone": "555-2222",
            "mrn": "MRN-WF-1001",
        },
    )
    assert patient["full_name"] == "Workflow Patient"

    intake_doc = post_json(
        client,
        "/documents",
        {
            "patient_id": patient["patient_id"],
            "document_type": "intake",
        },
    )
    assert intake_doc["status"] == "draft"

    signed_intake = post_json(
        client,
        f"/documents/{intake_doc['document_id']}/sign",
        {"document_id": intake_doc["document_id"], "actor_id": "patient-workflow"},
    )
    assert signed_intake["status"] == "signed"

    # Steps 2-3: front desk creates eligibility task and assigns specialist
    eligibility_task = post_json(
        client,
        "/tasks",
        {
            "patient_id": patient["patient_id"],
            "task_type": "eligibility_verification",
            "title": "Verify insurance eligibility for Workflow Patient",
            "priority": "high",
            "assignee_id": "eligibility-specialist-1",
        },
    )
    assert eligibility_task["task_type"] == "eligibility_verification"
    assert eligibility_task["assignee_id"] == "eligibility-specialist-1"

    task_in_progress = patch_json(
        client,
        f"/tasks/{eligibility_task['task_id']}",
        {"status": "in_progress"},
    )
    assert task_in_progress["status"] == "in_progress"

    # Steps 4-5: insurance portal query -> structured insurance record
    policy = post_json(
        client,
        "/insurance",
        {
            "patient_id": patient["patient_id"],
            "carrier_name": "Blue Cross",
            "member_id": "BC-WF-1001",
            "group_number": "GRP-WF-2001",
            "copay_amount": 35.0,
            "deductible": 500.0,
            "visits_authorized": 24,
        },
    )
    assert policy["eligibility_status"] == "unknown"

    verified_policy = patch_json(
        client,
        f"/insurance/{policy['policy_id']}/update",
        {
            "eligibility_status": "verified",
            "eligibility_notes": "Portal verified: 24 visits authorized, $35 copay",
            "visits_used": 4,
        },
    )
    assert verified_policy["eligibility_status"] == "verified"
    assert verified_policy["visits_used"] == 4

    policy_list = get_json(client, f"/insurance/{patient['patient_id']}")
    assert len(policy_list["policies"]) == 1
    assert policy_list["policies"][0]["copay_amount"] == 35.0

    task_done = patch_json(
        client,
        f"/tasks/{eligibility_task['task_id']}",
        {"status": "completed"},
    )
    assert task_done["status"] == "completed"

    # Step 7: appointment creation
    therapist = post_json(
        client,
        "/admin/staff",
        {"name": "Alice PT", "role": "therapist", "license_id": "PT-WF-1"},
    )
    room = post_json(
        client,
        "/admin/rooms",
        {"name": "Room 1", "code": "R1", "room_type": "treatment"},
    )

    appointment = post_json(
        client,
        "/appointments",
        {
            "patient_id": patient["patient_id"],
            "provider_id": therapist["staff_id"],
            "appointment_date": date.today().isoformat(),
            "appointment_time": "10:30",
            "appointment_type": "regular",
        },
    )
    assert appointment["status"] == "scheduled"

    # Steps 8-9: check-in + room board replacement
    visit = post_json(
        client,
        "/portal/checkin",
        {
            "patient_name": patient["full_name"],
            "patient_ref": patient["mrn"],
            "patient_id": patient["patient_id"],
            "appointment_id": appointment["appointment_id"],
            "actor_id": "frontdesk-1",
        },
    )
    assert visit["status"] == "checked_in"

    started = post_json(
        client,
        "/portal/service/start",
        {
            "visit_id": visit["visit_id"],
            "staff_id": therapist["staff_id"],
            "room_id": room["room_id"],
            "service_type": "PT",
            "actor_id": "therapist-1",
        },
    )
    assert started["status"] == "in_service"

    board = get_json(client, "/projections/room-board")
    room_row = [item for item in board["rooms"] if item["room_id"] == room["room_id"]][0]
    assert room_row["status"] == "occupied"
    assert room_row["patient_name"] == patient["full_name"]

    # Step 10: doctor writes note
    ended = post_json(
        client,
        "/portal/service/end",
        {"visit_id": visit["visit_id"], "actor_id": "therapist-1"},
    )
    assert ended["status"] == "service_completed"

    note = post_json(
        client,
        "/notes",
        {
            "visit_id": visit["visit_id"],
            "patient_id": patient["patient_id"],
            "provider_id": therapist["staff_id"],
            "template_type": "SOAP",
            "content": {
                "subjective": "Patient reports improvement",
                "objective": "Therapeutic exercise completed",
                "assessment": "Progressing as expected",
                "plan": "Continue PT next week",
            },
        },
    )
    assert note["status"] == "draft"

    signed_note = post_json(
        client,
        f"/notes/{note['note_id']}/sign",
        {"note_id": note["note_id"], "actor_id": therapist["staff_id"]},
    )
    assert signed_note["status"] == "signed"

    # Step 11: back office claim-prep placeholder task
    claim_task = post_json(
        client,
        "/tasks",
        {
            "patient_id": patient["patient_id"],
            "visit_id": visit["visit_id"],
            "task_type": "claim_followup",
            "title": "Prepare claim package for Workflow Patient visit",
            "priority": "high",
            "assignee_id": "backoffice-1",
        },
    )
    assert claim_task["task_type"] == "claim_followup"

    checked_out = post_json(
        client,
        "/portal/checkout",
        {
            "visit_id": visit["visit_id"],
            "payment_status": "copay_collected",
            "payment_amount": 35.0,
            "payment_method": "card",
            "copay_collected": 35.0,
            "wd_verified": True,
            "patient_signed": True,
            "actor_id": "frontdesk-1",
        },
    )
    assert checked_out["status"] == "checked_out"

    claim_task_done = patch_json(
        client,
        f"/tasks/{claim_task['task_id']}",
        {"status": "completed"},
    )
    assert claim_task_done["status"] == "completed"

    # Step 18: day-end report + audit trail
    summary = get_json(client, f"/projections/daily-summary?date={date.today().isoformat()}")
    assert summary["total_check_ins"] >= 1
    assert summary["total_checked_out"] >= 1
    assert summary["copay_total"] >= 35.0

    report = post_json(client, "/reports/daily/generate", {"actor_id": "manager-1"})
    assert report["total_check_ins"] >= 1
    assert report["total_check_outs"] >= 1
    assert report["total_services_completed"] >= 1

    events = get_json(client, "/events")
    event_types = {event["event_type"] for event in events["events"]}
    expected = {
        "PATIENT_CREATED",
        "DOCUMENT_CREATED",
        "DOCUMENT_SIGNED",
        "TASK_CREATED",
        "TASK_UPDATED",
        "INSURANCE_POLICY_CREATED",
        "INSURANCE_POLICY_UPDATED",
        "APPOINTMENT_CREATED",
        "PATIENT_CHECKIN",
        "SERVICE_STARTED",
        "SERVICE_COMPLETED",
        "NOTE_CREATED",
        "NOTE_SIGNED",
        "PATIENT_CHECKOUT",
        "PAYMENT_RECORDED",
        "DAILY_REPORT_GENERATED",
    }
    assert expected.issubset(event_types)
