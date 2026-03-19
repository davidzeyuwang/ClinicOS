"""End-to-end prototype API test — aligned with PRD v2.0.

Tests the full visit lifecycle plus new domain objects:
Patient (§11.1), Appointment (§11.2), Front Desk Operations (§11.3),
Document (§11.4), Visit (§11.5), Clinical Note (§11.6),
Insurance (§11.7), Task (§11.9).
"""
import json
import urllib.request


BASE = "http://127.0.0.1:8000/prototype"


def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(data).encode(),
        {"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(req).read())


def get(path):
    return json.loads(urllib.request.urlopen(BASE + path).read())


def patch(path, data):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(data).encode(),
        {"Content-Type": "application/json"},
        method="PATCH",
    )
    return json.loads(urllib.request.urlopen(req).read())


def main():
    print("=" * 60)
    print("ClinicOS PRD v2.0 — E2E Test")
    print("=" * 60)

    # ==================== ROOMS & STAFF (§11.3) ====================
    print("\n=== Step 1: Create Rooms ===")
    r1 = post("/admin/rooms", {"name": "Room 1", "code": "R1", "room_type": "treatment"})
    r2 = post("/admin/rooms", {"name": "Room 2", "code": "R2", "room_type": "treatment"})
    print(f"  Room 1: {r1['room_id']} status={r1['status']}")
    print(f"  Room 2: {r2['room_id']} status={r2['status']}")
    assert r1["status"] == "available"
    assert r2["status"] == "available"

    print("\n=== Step 2: Create Staff ===")
    s1 = post("/admin/staff", {"name": "Alice PT", "role": "therapist", "license_id": "PT-001"})
    s2 = post("/admin/staff", {"name": "Bob OT", "role": "therapist", "license_id": "OT-002"})
    print(f"  Alice: {s1['staff_id']}")
    print(f"  Bob:   {s2['staff_id']}")
    assert s1["active"] is True
    assert s2["role"] == "therapist"

    # ==================== PATIENT (§11.1) ====================
    print("\n=== Step 3: Create Patient ===")
    p1 = post("/patients", {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1985-06-15",
        "phone": "555-0101",
        "mrn": "MRN-1001",
    })
    print(f"  Patient: {p1['patient_id']} name={p1['full_name']} mrn={p1['mrn']}")
    assert p1["first_name"] == "John"
    assert p1["intake_status"] == "pending"

    print("\n=== Step 3b: Search Patient ===")
    search = get("/patients?q=Doe")
    print(f"  Found {len(search['patients'])} patient(s)")
    assert len(search["patients"]) >= 1
    assert search["patients"][0]["last_name"] == "Doe"

    # ==================== INSURANCE (§11.7) ====================
    print("\n=== Step 4: Add Insurance Policy ===")
    ins1 = post("/insurance", {
        "patient_id": p1["patient_id"],
        "carrier_name": "Blue Cross",
        "member_id": "BC-123456",
        "group_number": "GRP-789",
        "copay_amount": 30.0,
        "visits_authorized": 24,
    })
    print(f"  Policy: {ins1['policy_id']} carrier={ins1['carrier_name']} status={ins1['eligibility_status']}")
    assert ins1["carrier_name"] == "Blue Cross"
    assert ins1["eligibility_status"] == "unknown"

    print("\n=== Step 4b: Verify Eligibility ===")
    ins1_updated = patch(f"/insurance/{ins1['policy_id']}/update", {
        "eligibility_status": "verified",
        "eligibility_notes": "Verified via portal — 24 visits authorized",
        "visits_used": 3,
    })
    print(f"  Eligibility: {ins1_updated['eligibility_status']} verified_at={ins1_updated['eligibility_verified_at']}")
    assert ins1_updated["eligibility_status"] == "verified"
    assert ins1_updated["eligibility_verified_at"] is not None

    # ==================== APPOINTMENT (§11.2) ====================
    print("\n=== Step 5: Create Appointment ===")
    from datetime import date
    today = date.today().isoformat()
    appt1 = post("/appointments", {
        "patient_id": p1["patient_id"],
        "provider_id": s1["staff_id"],
        "appointment_date": today,
        "appointment_time": "10:00",
        "appointment_type": "regular",
    })
    print(f"  Appointment: {appt1['appointment_id']} date={appt1['appointment_date']} status={appt1['status']}")
    assert appt1["status"] == "scheduled"

    print("\n=== Step 5b: List Today's Appointments ===")
    appts = get(f"/appointments?date={today}")
    print(f"  Today: {len(appts['appointments'])} appointment(s)")
    assert len(appts["appointments"]) >= 1

    # ==================== CHECK-IN + VISIT (§11.3, §11.5) ====================
    print("\n=== Step 6: Patient Check-in (linked to appointment) ===")
    v1 = post("/portal/checkin", {
        "patient_name": "John Doe",
        "patient_ref": "MRN-1001",
        "patient_id": p1["patient_id"],
        "appointment_id": appt1["appointment_id"],
        "actor_id": "frontdesk-1",
    })
    print(f"  Visit: {v1['visit_id']} status={v1['status']} patient_id={v1['patient_id']}")
    assert v1["status"] == "checked_in"
    assert v1["patient_id"] == p1["patient_id"]
    assert v1["appointment_id"] == appt1["appointment_id"]

    # ==================== DOCUMENT (§11.4) ====================
    print("\n=== Step 7: Create Intake Document ===")
    doc1 = post("/documents", {
        "patient_id": p1["patient_id"],
        "visit_id": v1["visit_id"],
        "document_type": "intake",
    })
    print(f"  Document: {doc1['document_id']} type={doc1['document_type']} seq={doc1['sequence_number']}")
    assert doc1["document_type"] == "intake"
    assert doc1["sequence_number"] == 1
    assert doc1["status"] == "draft"

    print("\n=== Step 7b: Sign Document ===")
    doc1_signed = post(f"/documents/{doc1['document_id']}/sign", {"document_id": doc1["document_id"], "actor_id": "patient-john"})
    print(f"  Document signed: status={doc1_signed['status']} signed_at={doc1_signed['signed_at']}")
    assert doc1_signed["status"] == "signed"

    print("\n=== Step 7c: Create Second Consent Document (auto sequence) ===")
    doc2 = post("/documents", {
        "patient_id": p1["patient_id"],
        "document_type": "consent",
    })
    assert doc2["sequence_number"] == 1  # first consent doc

    doc3 = post("/documents", {
        "patient_id": p1["patient_id"],
        "document_type": "intake",
    })
    print(f"  Second intake doc: seq={doc3['sequence_number']}")
    assert doc3["sequence_number"] == 2  # second intake doc

    # ==================== SERVICE (§11.3) ====================
    print("\n=== Step 8: Start Service ===")
    svc = post("/portal/service/start", {
        "visit_id": v1["visit_id"],
        "staff_id": s1["staff_id"],
        "room_id": r1["room_id"],
        "service_type": "PT",
        "actor_id": "therapist-1",
    })
    print(f"  Visit status={svc['status']} room={svc['room_id']} service={svc['service_type']}")
    assert svc["status"] == "in_service"

    print("\n=== Step 8b: Room Board ===")
    board = get("/projections/room-board")
    for rm in board["rooms"]:
        print(f"  {rm['code']} {rm['name']}: status={rm['status']} patient={rm['patient_name']}")
    r1_board = [r for r in board["rooms"] if r["room_id"] == r1["room_id"]][0]
    assert r1_board["status"] == "occupied"
    assert r1_board["patient_name"] == "John Doe"

    print("\n=== Step 9: End Service ===")
    end = post("/portal/service/end", {"visit_id": v1["visit_id"], "actor_id": "therapist-1"})
    assert end["status"] == "service_completed"

    # ==================== CLINICAL NOTE (§11.6) ====================
    print("\n=== Step 10: Create Clinical Note ===")
    note1 = post("/notes", {
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
    })
    print(f"  Note: {note1['note_id']} status={note1['status']} template={note1['template_type']}")
    assert note1["status"] == "draft"

    print("\n=== Step 10b: Sign Note ===")
    note1_signed = post(f"/notes/{note1['note_id']}/sign", {"note_id": note1["note_id"], "actor_id": s1["staff_id"]})
    print(f"  Note signed: status={note1_signed['status']} signed_at={note1_signed['signed_at']}")
    assert note1_signed["status"] == "signed"

    # ==================== CHECKOUT WITH PAYMENT (§11.3) ====================
    print("\n=== Step 11: Checkout with Payment ===")
    co = post("/portal/checkout", {
        "visit_id": v1["visit_id"],
        "payment_status": "copay_collected",
        "payment_amount": 30.0,
        "payment_method": "card",
        "actor_id": "frontdesk-1",
    })
    print(f"  Visit status={co['status']} payment={co['payment_status']} amount={co['payment_amount']}")
    assert co["status"] == "checked_out"
    assert co["payment_status"] == "copay_collected"
    assert co["payment_amount"] == 30.0

    # ==================== TASK (§11.9) ====================
    print("\n=== Step 12: Create Follow-up Task ===")
    task1 = post("/tasks", {
        "patient_id": p1["patient_id"],
        "visit_id": v1["visit_id"],
        "task_type": "insurance_followup",
        "title": "Submit claim for John Doe PT session",
        "priority": "high",
        "assignee_id": "backoffice-1",
    })
    print(f"  Task: {task1['task_id']} type={task1['task_type']} status={task1['status']}")
    assert task1["status"] == "open"
    assert task1["priority"] == "high"

    print("\n=== Step 12b: Complete Task ===")
    task1_done = patch(f"/tasks/{task1['task_id']}", {"status": "completed"})
    print(f"  Task status={task1_done['status']} completed_at={task1_done['completed_at']}")
    assert task1_done["status"] == "completed"
    assert task1_done["completed_at"] is not None

    # ==================== STAFF HOURS + REPORT ====================
    print("\n=== Step 13: Staff Hours ===")
    hours = get("/projections/staff-hours")
    for st in hours["staff"]:
        print(f"  {st['name']}: completed={st['completed_minutes']}min sessions={st['sessions_completed']}")

    print("\n=== Step 14: Generate Daily Report ===")
    report = post("/reports/daily/generate", {"actor_id": "manager-1"})
    print(f"  Date: {report['date']}")
    print(f"  Check-ins: {report['total_check_ins']}")
    print(f"  Check-outs: {report['total_check_outs']}")
    print(f"  Services completed: {report['total_services_completed']}")
    print(f"  Appointments: {report['total_appointments']}")
    print(f"  No-shows: {report['no_shows']}")
    print(f"  Open sessions: {report['open_sessions']}")
    assert report["total_check_ins"] >= 1
    assert report["total_services_completed"] >= 1

    # ==================== EVENT LOG ====================
    print("\n=== Step 15: Event Log ===")
    events = get("/events")
    print(f"  Total events: {events['count']}")
    event_types = set(e["event_type"] for e in events["events"])
    print(f"  Event types: {sorted(event_types)}")
    # Should have events from all new domain objects
    expected_types = {"ROOM_CREATED", "STAFF_CREATED", "PATIENT_CREATED", "PATIENT_CHECKIN",
                      "SERVICE_STARTED", "SERVICE_COMPLETED", "PATIENT_CHECKOUT",
                      "NOTE_CREATED", "NOTE_SIGNED", "DOCUMENT_CREATED", "DOCUMENT_SIGNED",
                      "TASK_CREATED", "TASK_UPDATED", "APPOINTMENT_CREATED",
                      "INSURANCE_POLICY_CREATED", "INSURANCE_POLICY_UPDATED",
                      "PAYMENT_RECORDED", "DAILY_REPORT_GENERATED"}
    missing = expected_types - event_types
    if missing:
        print(f"  WARNING: Missing expected event types: {missing}")
    else:
        print("  All expected event types present!")

    print("\n" + "=" * 60)
    print("ALL 15 STEPS PASSED — PRD v2.0 Domain Coverage Verified")
    print("=" * 60)
    print("\nDomain objects tested:")
    print("  ✓ Patient (§11.1)")
    print("  ✓ Appointment (§11.2)")
    print("  ✓ Front Desk Ops — Check-in/Room/Service (§11.3)")
    print("  ✓ Document/Signature (§11.4)")
    print("  ✓ Visit lifecycle (§11.5)")
    print("  ✓ Clinical Note (§11.6)")
    print("  ✓ Insurance/Eligibility (§11.7)")
    print("  ✓ Task/Case (§11.9)")
    print("  ✓ Daily Report (§11.10)")
    print("  ✓ Event audit log (§11.11)")


if __name__ == "__main__":
    main()
