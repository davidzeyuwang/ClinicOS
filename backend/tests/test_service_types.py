"""Tests for NEXT-P1-01 + NEXT-P1-02: admin-managed service types + staff qualifications."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_USERNAME = "admin@test.clinicos.local"
TEST_PASSWORD = "test1234"
TEST_TOKEN_HEADER = {"x-test-token": "test-admin-secret-fixed-token"}


@pytest.fixture()
def client():
    with TestClient(app) as tc:
        response = tc.post("/prototype/test/reset", headers=TEST_TOKEN_HEADER)
        assert response.status_code == 200
        yield tc


@pytest.fixture()
def auth_headers(client):
    resp = client.post("/prototype/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


BASE = "/prototype"


def test_seed_creates_11_service_types(client, auth_headers):
    """Startup seed inserts all 11 default service types."""
    r = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    assert r.status_code == 200
    types = r.json()["service_types"]
    names = {t["name"] for t in types}
    for expected in ["PT", "OT", "Acupuncture", "Cupping", "Massage", "E-stim", "Speech"]:
        assert expected in names, f"{expected} missing from seed"
    assert len(types) == 11


def test_create_service_type(client, auth_headers):
    """Admin can create a new service type."""
    r = client.post(f"{BASE}/admin/service-types", json={"name": "Lymphatic Massage"}, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Lymphatic Massage"
    assert data["is_active"] is True
    assert "service_type_id" in data

    r2 = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    names = [t["name"] for t in r2.json()["service_types"]]
    assert "Lymphatic Massage" in names


def test_update_service_type_name(client, auth_headers):
    """Admin can rename a service type."""
    r_list = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    pt = next(t for t in r_list.json()["service_types"] if t["name"] == "PT")
    sid = pt["service_type_id"]

    r = client.patch(f"{BASE}/admin/service-types/{sid}", json={"name": "Physical Therapy"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Physical Therapy"


def test_retire_service_type(client, auth_headers):
    """Retired service types disappear from default list; visible with include_inactive=true."""
    r_list = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    speech = next(t for t in r_list.json()["service_types"] if t["name"] == "Speech")
    sid = speech["service_type_id"]

    r = client.delete(f"{BASE}/admin/service-types/{sid}", headers=auth_headers)
    assert r.status_code == 204

    r2 = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    names = [t["name"] for t in r2.json()["service_types"]]
    assert "Speech" not in names

    r3 = client.get(f"{BASE}/admin/service-types?include_inactive=true", headers=auth_headers)
    names_all = [t["name"] for t in r3.json()["service_types"]]
    assert "Speech" in names_all


def test_staff_service_type_qualification(client, auth_headers):
    """Can set and get qualifications for a staff member."""
    r_staff = client.post(f"{BASE}/admin/staff", json={"name": "Test PT", "role": "therapist"}, headers=auth_headers)
    assert r_staff.status_code == 200
    staff_id = r_staff.json()["staff_id"]

    r_list = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    types = {t["name"]: t["service_type_id"] for t in r_list.json()["service_types"]}

    r_set = client.put(
        f"{BASE}/admin/staff/{staff_id}/service-types",
        json={"service_type_ids": [types["PT"], types["OT"]]},
        headers=auth_headers
    )
    assert r_set.status_code == 200

    r_get = client.get(f"{BASE}/admin/staff/{staff_id}/service-types", headers=auth_headers)
    assert r_get.status_code == 200
    qual_names = {t["name"] for t in r_get.json()["service_types"]}
    assert qual_names == {"PT", "OT"}


def test_set_staff_service_types_is_replace_all(client, auth_headers):
    """Setting qualifications replaces the previous full set."""
    r_staff = client.post(f"{BASE}/admin/staff", json={"name": "Acupuncturist", "role": "therapist"}, headers=auth_headers)
    staff_id = r_staff.json()["staff_id"]

    r_list = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    types = {t["name"]: t["service_type_id"] for t in r_list.json()["service_types"]}

    client.put(f"{BASE}/admin/staff/{staff_id}/service-types",
               json={"service_type_ids": [types["PT"], types["OT"]]},
               headers=auth_headers)

    client.put(f"{BASE}/admin/staff/{staff_id}/service-types",
               json={"service_type_ids": [types["Acupuncture"]]},
               headers=auth_headers)

    r_get = client.get(f"{BASE}/admin/staff/{staff_id}/service-types", headers=auth_headers)
    qual_names = {t["name"] for t in r_get.json()["service_types"]}
    assert qual_names == {"Acupuncture"}


def test_get_service_type_staff(client, auth_headers):
    """Reverse lookup: get qualified staff for a service type."""
    r_staff = client.post(f"{BASE}/admin/staff", json={"name": "PT Jane", "role": "therapist"}, headers=auth_headers)
    staff_id = r_staff.json()["staff_id"]

    r_list = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    pt = next(t for t in r_list.json()["service_types"] if t["name"] == "PT")
    pt_id = pt["service_type_id"]

    client.put(f"{BASE}/admin/staff/{staff_id}/service-types",
               json={"service_type_ids": [pt_id]},
               headers=auth_headers)

    r_get = client.get(f"{BASE}/admin/service-types/{pt_id}/staff", headers=auth_headers)
    assert r_get.status_code == 200
    staff_names = [s["name"] for s in r_get.json()["staff"]]
    assert "PT Jane" in staff_names


def test_staff_hours_includes_service_type_names(client, auth_headers):
    """GET /projections/staff-hours enriches each record with service_type_names."""
    r_staff = client.post(f"{BASE}/admin/staff", json={"name": "Dr Test", "role": "therapist"}, headers=auth_headers)
    staff_id = r_staff.json()["staff_id"]

    r_list = client.get(f"{BASE}/admin/service-types", headers=auth_headers)
    ot = next(t for t in r_list.json()["service_types"] if t["name"] == "OT")
    client.put(f"{BASE}/admin/staff/{staff_id}/service-types",
               json={"service_type_ids": [ot["service_type_id"]]},
               headers=auth_headers)

    r_hours = client.get(f"{BASE}/projections/staff-hours", headers=auth_headers)
    assert r_hours.status_code == 200
    staff_list = r_hours.json()["staff"]
    dr_test = next((s for s in staff_list if s["name"] == "Dr Test"), None)
    assert dr_test is not None
    assert "service_type_names" in dr_test
    assert "OT" in dr_test["service_type_names"]
