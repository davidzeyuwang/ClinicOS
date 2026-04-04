"""
Test Suite: PRD-005 Multiple Treatments Per Visit
Tests treatment CRUD, event logging, and compliance.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

TEST_EMAIL = "admin@test.clinicos.local"
TEST_PASSWORD = "test1234"
TEST_TOKEN_HEADER = {"x-test-token": "test-admin-secret-fixed-token"}


@pytest.mark.asyncio
async def test_prd005_multiple_treatments_workflow():
    """
    Test Case: PRD-005 Complete Workflow

    Scenario:
    1. Create room, staff, patient, insurance
    2. Check in patient
    3. Add multiple treatments (PT + E-stim + Massage)
    4. Update treatment duration
    5. List treatments for visit
    6. Query treatment records
    7. Delete one treatment
    8. Checkout patient
    9. Verify events logged

    Expected: All API calls succeed, events logged correctly.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset
        reset_resp = await client.post("/prototype/test/reset", headers=TEST_TOKEN_HEADER)
        assert reset_resp.status_code == 200

        # Get auth token
        login_resp = await client.post("/prototype/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        auth = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        # 1. Create entities
        room = await client.post("/prototype/admin/rooms", json={
            "name": "Treatment Room 1",
            "code": "TR1",
            "room_type": "treatment"
        }, headers=auth)
        assert room.status_code == 200
        room_id = room.json()["room_id"]

        staff1 = await client.post("/prototype/admin/staff", json={
            "name": "Dr. Sarah Chen",
            "role": "physical_therapist"
        }, headers=auth)
        assert staff1.status_code == 200
        therapist1_id = staff1.json()["staff_id"]

        staff2 = await client.post("/prototype/admin/staff", json={
            "name": "Lisa Wu",
            "role": "massage_therapist"
        }, headers=auth)
        assert staff2.status_code == 200
        therapist2_id = staff2.json()["staff_id"]

        patient = await client.post("/prototype/patients", json={
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1985-03-10",
            "phone": "555-1234"
        }, headers=auth)
        assert patient.status_code == 200
        patient_id = patient.json()["patient_id"]

        insurance = await client.post("/prototype/insurance", json={
            "patient_id": patient_id,
            "priority": "primary",
            "carrier_name": "Blue Cross",
            "member_id": "BC123456",
            "copay_amount": 25.00
        }, headers=auth)
        assert insurance.status_code == 200

        # 2. Check in patient
        checkin_resp = await client.post("/prototype/portal/checkin", json={
            "patient_name": "John Doe",
            "patient_id": patient_id,
            "actor_id": therapist1_id
        }, headers=auth)
        assert checkin_resp.status_code == 200
        visit_id = checkin_resp.json()["visit_id"]

        # Start service to assign room
        start_resp = await client.post("/prototype/portal/service/start", json={
            "visit_id": visit_id,
            "room_id": room_id,
            "staff_id": therapist1_id,
            "service_type": "Multiple Treatments",
            "actor_id": therapist1_id
        }, headers=auth)
        assert start_resp.status_code == 200

        # 3. Add multiple treatments
        treatment1 = await client.post(f"/prototype/visits/{visit_id}/treatments/add", json={
            "visit_id": visit_id,
            "modality": "Physical Therapy",
            "therapist_id": therapist1_id,
            "duration_minutes": 30,
            "notes": "Lower back exercises",
            "actor_id": therapist1_id
        }, headers=auth)
        assert treatment1.status_code == 200
        t1_id = treatment1.json()["treatment_id"]
        assert treatment1.json()["modality"] == "Physical Therapy"
        assert treatment1.json()["duration_minutes"] == 30

        treatment2 = await client.post(f"/prototype/visits/{visit_id}/treatments/add", json={
            "visit_id": visit_id,
            "modality": "E-stim",
            "therapist_id": therapist1_id,
            "duration_minutes": 15,
            "actor_id": therapist1_id
        }, headers=auth)
        assert treatment2.status_code == 200
        t2_id = treatment2.json()["treatment_id"]

        treatment3 = await client.post(f"/prototype/visits/{visit_id}/treatments/add", json={
            "visit_id": visit_id,
            "modality": "Massage",
            "therapist_id": therapist2_id,
            "duration_minutes": 20,
            "notes": "Deep tissue",
            "actor_id": therapist2_id
        }, headers=auth)
        assert treatment3.status_code == 200
        t3_id = treatment3.json()["treatment_id"]

        # 4. Update treatment duration
        update_resp = await client.patch(
            f"/prototype/visits/{visit_id}/treatments/{t1_id}/update",
            json={"duration_minutes": 45, "notes": "Extended session"},
            headers=auth
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["duration_minutes"] == 45

        # 5. List treatments for visit
        list_resp = await client.get(f"/prototype/visits/{visit_id}/treatments", headers=auth)
        assert list_resp.status_code == 200
        treatments = list_resp.json()["treatments"]
        assert len(treatments) == 3
        assert treatments[0]["modality"] == "Physical Therapy"
        assert treatments[1]["modality"] == "E-stim"
        assert treatments[2]["modality"] == "Massage"
        assert "therapist_name" in treatments[0]

        # 6. Query treatment records
        records_resp = await client.get("/prototype/treatment-records", headers=auth)
        assert records_resp.status_code == 200
        records = records_resp.json()["treatments"]
        assert len(records) == 3
        assert "patient_name" in records[0]
        assert "therapist_name" in records[0]
        assert "room_name" in records[0]

        # Filter by modality
        filtered = await client.get("/prototype/treatment-records?modality=E-stim", headers=auth)
        assert filtered.status_code == 200
        assert len(filtered.json()["treatments"]) == 1
        assert filtered.json()["treatments"][0]["modality"] == "E-stim"

        # Filter by therapist
        therapist_records = await client.get(f"/prototype/treatment-records?staff_id={therapist2_id}", headers=auth)
        assert therapist_records.status_code == 200
        assert len(therapist_records.json()["treatments"]) == 1
        assert therapist_records.json()["treatments"][0]["modality"] == "Massage"

        # 7. Delete one treatment
        delete_resp = await client.delete(f"/prototype/visits/{visit_id}/treatments/{t2_id}/delete", headers=auth)
        assert delete_resp.status_code == 200
        assert delete_resp.json()["deleted"] is True

        # Verify deletion
        list_after_delete = await client.get(f"/prototype/visits/{visit_id}/treatments", headers=auth)
        assert len(list_after_delete.json()["treatments"]) == 2

        # 8. Checkout patient
        end_service = await client.post("/prototype/portal/service/end", json={
            "visit_id": visit_id,
            "actor_id": therapist1_id
        }, headers=auth)
        assert end_service.status_code == 200

        checkout = await client.post("/prototype/portal/checkout", json={
            "visit_id": visit_id,
            "copay_collected": 25.00,
            "payment_method": "card",
            "wd_verified": True,
            "patient_signed": True,
            "actor_id": therapist1_id
        }, headers=auth)
        assert checkout.status_code == 200

        # 9. Verify events logged
        events_resp = await client.get("/prototype/events", headers=auth)
        assert events_resp.status_code == 200
        events = events_resp.json()["events"]

        treatment_events = [e for e in events if "TREATMENT" in e["event_type"]]
        assert len(treatment_events) >= 5  # 3 added, 1 updated, 1 deleted

        added_events = [e for e in treatment_events if e["event_type"] == "TREATMENT_ADDED"]
        assert len(added_events) == 3

        updated_events = [e for e in treatment_events if e["event_type"] == "TREATMENT_UPDATED"]
        assert len(updated_events) == 1

        deleted_events = [e for e in treatment_events if e["event_type"] == "TREATMENT_DELETED"]
        assert len(deleted_events) == 1


@pytest.mark.asyncio
async def test_cannot_add_treatment_to_checked_out_visit():
    """
    Test Case: Cannot add treatments after checkout

    Expected: 400 error when attempting to add treatment to checked-out visit
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset and auth
        await client.post("/prototype/test/reset", headers=TEST_TOKEN_HEADER)
        login_resp = await client.post("/prototype/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        auth = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        # Create minimal entities
        room = await client.post("/prototype/admin/rooms", json={
            "name": "Room 1", "code": "R1", "room_type": "treatment"
        }, headers=auth)
        room_id = room.json()["room_id"]

        staff = await client.post("/prototype/admin/staff", json={
            "name": "Dr. Test", "role": "therapist"
        }, headers=auth)
        staff_id = staff.json()["staff_id"]

        patient = await client.post("/prototype/patients", json={
            "first_name": "Jane", "last_name": "Smith", "date_of_birth": "1990-07-22", "phone": "555-9999"
        }, headers=auth)
        patient_id = patient.json()["patient_id"]

        insurance = await client.post("/prototype/insurance", json={
            "patient_id": patient_id,
            "priority": "primary",
            "carrier_name": "Aetna",
            "member_id": "AET123",
            "copay_amount": 30.00
        }, headers=auth)

        # Complete full visit cycle
        checkin = await client.post("/prototype/portal/checkin", json={
            "patient_name": "Jane Smith",
            "patient_id": patient_id,
            "actor_id": staff_id
        }, headers=auth)
        visit_id = checkin.json()["visit_id"]

        await client.post("/prototype/portal/service/start", json={
            "visit_id": visit_id,
            "room_id": room_id,
            "staff_id": staff_id,
            "service_type": "PT",
            "actor_id": staff_id
        }, headers=auth)

        await client.post("/prototype/portal/service/end", json={
            "visit_id": visit_id,
            "actor_id": staff_id
        }, headers=auth)

        await client.post("/prototype/portal/checkout", json={
            "visit_id": visit_id,
            "copay_collected": 30.00,
            "payment_method": "cash",
            "wd_verified": True,
            "patient_signed": True,
            "actor_id": staff_id
        }, headers=auth)

        # Try to add treatment after checkout
        add_after_checkout = await client.post(f"/prototype/visits/{visit_id}/treatments/add", json={
            "visit_id": visit_id,
            "modality": "PT",
            "therapist_id": staff_id,
            "duration_minutes": 30,
            "actor_id": staff_id
        }, headers=auth)

        assert add_after_checkout.status_code == 400
        assert "Cannot add treatment" in add_after_checkout.json()["detail"]


@pytest.mark.asyncio
async def test_treatment_without_therapist_defaults_to_actor():
    """
    Test Case: Treatment without therapist_id defaults to actor_id

    Expected: therapist_id automatically set to actor_id when not provided
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset and auth
        await client.post("/prototype/test/reset", headers=TEST_TOKEN_HEADER)
        login_resp = await client.post("/prototype/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        auth = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        room = await client.post("/prototype/admin/rooms", json={
            "name": "Room X", "code": "RX", "room_type": "treatment"
        }, headers=auth)
        room_id = room.json()["room_id"]

        staff = await client.post("/prototype/admin/staff", json={
            "name": "Dr. Auto", "role": "therapist"
        }, headers=auth)
        staff_id = staff.json()["staff_id"]

        patient = await client.post("/prototype/patients", json={
            "first_name": "Auto", "last_name": "Test", "date_of_birth": "1980-11-05", "phone": "555-0000"
        }, headers=auth)
        patient_id = patient.json()["patient_id"]

        insurance = await client.post("/prototype/insurance", json={
            "patient_id": patient_id,
            "priority": "primary",
            "carrier_name": "UHC",
            "member_id": "UHC999",
            "copay_amount": 20.00
        }, headers=auth)

        checkin = await client.post("/prototype/portal/checkin", json={
            "patient_name": "Auto Test",
            "patient_id": patient_id,
            "actor_id": staff_id
        }, headers=auth)
        visit_id = checkin.json()["visit_id"]

        await client.post("/prototype/portal/service/start", json={
            "visit_id": visit_id,
            "room_id": room_id,
            "staff_id": staff_id,
            "service_type": "Cupping",
            "actor_id": staff_id
        }, headers=auth)

        # Add treatment WITHOUT therapist_id
        treatment = await client.post(f"/prototype/visits/{visit_id}/treatments/add", json={
            "visit_id": visit_id,
            "modality": "Cupping",
            "duration_minutes": 10,
            "actor_id": staff_id
            # No therapist_id provided
        }, headers=auth)

        assert treatment.status_code == 200
        assert treatment.json()["therapist_id"] == staff_id  # Should default to actor_id


@pytest.mark.asyncio
async def test_treatment_records_date_filter():
    """
    Test Case: Treatment records filtered by date range

    Expected: Only treatments within date range returned
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset and auth
        await client.post("/prototype/test/reset", headers=TEST_TOKEN_HEADER)
        login_resp = await client.post("/prototype/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        auth = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

        # Create entities
        room = await client.post("/prototype/admin/rooms", json={
            "name": "Room D", "code": "RD", "room_type": "treatment"
        }, headers=auth)
        room_id = room.json()["room_id"]

        staff = await client.post("/prototype/admin/staff", json={
            "name": "Dr. Date", "role": "therapist"
        }, headers=auth)
        staff_id = staff.json()["staff_id"]

        patient = await client.post("/prototype/patients", json={
            "first_name": "Date", "last_name": "Filter", "date_of_birth": "1995-09-15", "phone": "555-3283"
        }, headers=auth)
        patient_id = patient.json()["patient_id"]

        insurance = await client.post("/prototype/insurance", json={
            "patient_id": patient_id,
            "priority": "primary",
            "carrier_name": "Cigna",
            "member_id": "CIG123",
            "copay_amount": 25.00
        }, headers=auth)

        # Create visit and treatment
        checkin = await client.post("/prototype/portal/checkin", json={
            "patient_name": "Date Filter",
            "patient_id": patient_id,
            "actor_id": staff_id
        }, headers=auth)
        visit_id = checkin.json()["visit_id"]

        await client.post("/prototype/portal/service/start", json={
            "visit_id": visit_id,
            "room_id": room_id,
            "staff_id": staff_id,
            "service_type": "Acupuncture",
            "actor_id": staff_id
        }, headers=auth)

        await client.post(f"/prototype/visits/{visit_id}/treatments/add", json={
            "visit_id": visit_id,
            "modality": "Acupuncture",
            "therapist_id": staff_id,
            "duration_minutes": 40,
            "actor_id": staff_id
        }, headers=auth)

        # Query with today's date (use UTC date to match how visits are stored)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()

        records_today = await client.get(f"/prototype/treatment-records?date_from={today}&date_to={today}", headers=auth)
        assert records_today.status_code == 200
        assert len(records_today.json()["treatments"]) == 1

        # Query with future date (should be empty)
        future = "2099-12-31"
        records_future = await client.get(f"/prototype/treatment-records?date_from={future}&date_to={future}", headers=auth)
        assert records_future.status_code == 200
        assert len(records_future.json()["treatments"]) == 0
