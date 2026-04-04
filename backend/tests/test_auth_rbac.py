"""
Backend smoke tests: Authentication, RBAC, and Multi-tenancy.
Covers: AUTH-00, AUTH-01, AUTH-02, MT-01, MT-02
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_USERNAME = "admin@test.clinicos.local"
TEST_PASSWORD = "test1234"
TEST_TOKEN_HEADER = {"x-test-token": "test-admin-secret-fixed-token"}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        r = c.post("/prototype/test/reset", headers=TEST_TOKEN_HEADER)
        assert r.status_code == 200, f"Reset failed: {r.text}"
        yield c


@pytest.fixture()
def auth_headers(client):
    r = client.post(
        "/prototype/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def frontdesk_headers(client):
    """Create a frontdesk user via the test endpoint, return their auth headers."""
    suffix = str(uuid.uuid4())[:8]
    username = f"frontdesk-{suffix}@test.local"
    r = client.post(
        "/prototype/test/create-user",
        json={"username": username, "password": "front123!", "role": "frontdesk"},
        headers=TEST_TOKEN_HEADER,
    )
    assert r.status_code == 200, f"create-user failed: {r.text}"
    lr = client.post(
        "/prototype/auth/login",
        json={"username": username, "password": "front123!"},
    )
    assert lr.status_code == 200
    return {"Authorization": f"Bearer {lr.json()['access_token']}"}


# ── AUTH-01: Login / JWT ───────────────────────────────────────────────────────

def test_login_success_returns_jwt_with_all_fields(client):
    """Valid credentials → 200 with access_token, role, clinic_id, user_id."""
    r = client.post(
        "/prototype/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["role"] == "admin"
    assert body["clinic_id"]
    assert body["user_id"]
    assert body["display_name"]


def test_login_wrong_password_returns_401(client):
    r = client.post(
        "/prototype/auth/login",
        json={"username": TEST_USERNAME, "password": "totally-wrong"},
    )
    assert r.status_code == 401


def test_login_unknown_user_returns_401(client):
    r = client.post(
        "/prototype/auth/login",
        json={"username": "nobody@nowhere.example", "password": "irrelevant"},
    )
    assert r.status_code == 401


def test_me_with_valid_token(client, auth_headers):
    """GET /auth/me with valid Bearer token returns correct user object."""
    r = client.get("/prototype/auth/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == TEST_USERNAME
    assert body["role"] == "admin"
    assert body["clinic_id"]


def test_me_without_token_returns_401(client):
    r = client.get("/prototype/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token_returns_401(client):
    r = client.get("/prototype/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


# ── AUTH-01: Auth guard on protected endpoints ─────────────────────────────────

def test_patients_endpoint_requires_auth(client):
    """GET /patients without token → 401."""
    r = client.get("/prototype/patients")
    assert r.status_code == 401


def test_patients_endpoint_accepts_valid_token(client, auth_headers):
    """GET /patients with valid token → 200 with patients list."""
    r = client.get("/prototype/patients", headers=auth_headers)
    assert r.status_code == 200
    assert "patients" in r.json()


# ── AUTH-02: Role-based access control ────────────────────────────────────────

def test_admin_can_create_service_type(client, auth_headers):
    """Admin role succeeds on admin-only POST /admin/service-types."""
    r = client.post(
        "/prototype/admin/service-types",
        json={"name": "RBACSmoke", "description": "RBAC smoke type"},
        headers=auth_headers,
    )
    assert 200 <= r.status_code < 300, f"expected 2xx, got {r.status_code}: {r.text}"


def test_frontdesk_cannot_create_service_type(client, frontdesk_headers):
    """Frontdesk role → 403 on admin-only endpoint."""
    r = client.post(
        "/prototype/admin/service-types",
        json={"name": "FrontdeskAttempt", "description": "should fail"},
        headers=frontdesk_headers,
    )
    assert r.status_code == 403


def test_frontdesk_can_read_patients(client, frontdesk_headers):
    """Frontdesk role CAN access non-admin endpoints."""
    r = client.get("/prototype/patients", headers=frontdesk_headers)
    assert r.status_code == 200


# ── AUTH-00: Clinic self-registration ─────────────────────────────────────────

def test_register_clinic_creates_clinic_and_admin_user(client, auth_headers):
    """POST /auth/register-clinic → returns clinic_id + user_id."""
    suffix = str(uuid.uuid4())[:8]
    r = client.post(
        "/prototype/auth/register-clinic",
        json={
            "clinic_name": f"Smoke Clinic {suffix}",
            "slug": f"smoke-{suffix}",
            "admin_username": f"admin-{suffix}@smoke.test",
            "admin_password": "Smoke123!",
            "admin_display_name": f"Admin {suffix}",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["clinic_id"]
    assert body["user_id"]


def test_register_clinic_duplicate_slug_returns_409(client, auth_headers):
    """Duplicate clinic slug → 409 Conflict."""
    suffix = str(uuid.uuid4())[:8]
    payload = {
        "clinic_name": f"Dup Clinic {suffix}",
        "slug": f"dup-{suffix}",
        "admin_password": "Pass123!",
    }
    r1 = client.post(
        "/prototype/auth/register-clinic",
        json={**payload, "admin_username": f"dup1-{suffix}@test.local"},
        headers=auth_headers,
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/prototype/auth/register-clinic",
        json={**payload, "admin_username": f"dup2-{suffix}@test.local"},
        headers=auth_headers,
    )
    assert r2.status_code == 409


# ── MT-01 + MT-02: Multi-tenancy isolation ─────────────────────────────────────

def test_cross_clinic_patient_isolation(client, auth_headers):
    """Clinic B user cannot see Clinic A patients."""
    # Create a patient in Clinic A
    pr = client.post(
        "/prototype/patients",
        json={"first_name": "Clinic", "last_name": "Alpha", "date_of_birth": "1990-01-01", "phone": "555-9999"},
        headers=auth_headers,
    )
    assert pr.status_code == 200
    patient_id = pr.json()["patient_id"]

    # Register Clinic B and get its admin token
    suffix = str(uuid.uuid4())[:8]
    reg = client.post(
        "/prototype/auth/register-clinic",
        json={
            "clinic_name": f"Clinic B {suffix}",
            "slug": f"clinicb-{suffix}",
            "admin_username": f"adminb-{suffix}@b.test",
            "admin_password": "BPass123!",
            "admin_display_name": "Admin B",
        },
        headers=auth_headers,
    )
    assert reg.status_code == 200

    lr = client.post(
        "/prototype/auth/login",
        json={"username": f"adminb-{suffix}@b.test", "password": "BPass123!"},
    )
    assert lr.status_code == 200
    b_headers = {"Authorization": f"Bearer {lr.json()['access_token']}"}

    # Clinic B sees 0 patients (no cross-tenant data)
    list_r = client.get("/prototype/patients", headers=b_headers)
    assert list_r.status_code == 200
    assert list_r.json()["patients"] == []

    # Direct GET by patient_id from Clinic A → 404 for Clinic B
    get_r = client.get(f"/prototype/patients/{patient_id}", headers=b_headers)
    assert get_r.status_code == 404


def test_clinic_b_data_not_visible_to_clinic_a(client, auth_headers):
    """Asymmetric isolation: data created in Clinic B cannot be seen from Clinic A."""
    suffix = str(uuid.uuid4())[:8]

    # Register Clinic B and create a patient there
    reg = client.post(
        "/prototype/auth/register-clinic",
        json={
            "clinic_name": f"Clinic B2 {suffix}",
            "slug": f"clinicb2-{suffix}",
            "admin_username": f"adminb2-{suffix}@b2.test",
            "admin_password": "B2Pass123!",
            "admin_display_name": "Admin B2",
        },
        headers=auth_headers,
    )
    assert reg.status_code == 200

    lr = client.post(
        "/prototype/auth/login",
        json={"username": f"adminb2-{suffix}@b2.test", "password": "B2Pass123!"},
    )
    b2_headers = {"Authorization": f"Bearer {lr.json()['access_token']}"}

    pr = client.post(
        "/prototype/patients",
        json={"first_name": "Clinic", "last_name": "Beta", "date_of_birth": "1991-02-02", "phone": "555-8888"},
        headers=b2_headers,
    )
    assert pr.status_code == 200
    b2_patient_id = pr.json()["patient_id"]

    # Clinic A cannot access Clinic B's patient
    get_r = client.get(f"/prototype/patients/{b2_patient_id}", headers=auth_headers)
    assert get_r.status_code == 404
