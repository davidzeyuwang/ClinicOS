"""SQLAlchemy table definitions for ClinicOS.

Domain model aligned with PRD v2.0 §9:
  Patient · Appointment · Visit · Room / Resource Allocation · Clinical Note ·
  Document · Consent / Intake Package · Insurance Policy · Eligibility Check ·
  Claim · Task / Case · User · Role / Permission · Audit Log
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ==================== CLINIC + USER (Auth §11.10) ====================

class Clinic(Base):
    """Clinic/tenant master record."""
    __tablename__ = "clinics"

    clinic_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class User(Base):
    """Application user with role-based access."""
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # admin | frontdesk | doctor
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


# ==================== EVENT LOG (ADR-001) ====================

class EventLog(Base):
    """Append-only event log. Sacred — no updates, no deletes."""
    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=_new_id)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), unique=True, default=_new_id)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)


# ==================== ROOM / RESOURCE (§11.3) ====================

class Room(Base):
    """Room projection table."""
    __tablename__ = "rooms"

    room_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    room_type: Mapped[str] = mapped_column(String(32), default="treatment")
    branch: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default="Main")
    floor: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default="1F")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="available")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== STAFF (§11.3) ====================

class Staff(Base):
    """Staff projection table."""
    __tablename__ = "staff"

    staff_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    license_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== SERVICE TYPES (admin-managed) ====================

class ServiceType(Base):
    """Admin-managed service type registry (replaces hardcoded frontend lists)."""
    __tablename__ = "service_types"

    service_type_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)


class StaffServiceType(Base):
    """Junction table: which staff are qualified to perform which service types."""
    __tablename__ = "staff_service_types"

    staff_id: Mapped[str] = mapped_column(String(36), ForeignKey("staff.staff_id"), primary_key=True)
    service_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("service_types.service_type_id"), primary_key=True)


# ==================== PATIENT (§11.1) ====================

class Patient(Base):
    """Patient master file — unified patient record."""
    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    date_of_birth: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    gender: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mrn: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # Medical Record Number
    intake_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | completed
    consent_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | signed
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== APPOINTMENT (§11.2) ====================

class Appointment(Base):
    """Appointment management — tracks scheduled visits."""
    __tablename__ = "appointments"

    appointment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # staff_id
    appointment_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    appointment_time: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # HH:MM
    appointment_type: Mapped[str] = mapped_column(String(32), default="regular")  # regular | walk_in | follow_up | eval
    status: Mapped[str] = mapped_column(String(32), default="scheduled")  # scheduled | confirmed | checked_in | completed | no_show | cancelled
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== VISIT (§11.5) ====================

class Visit(Base):
    """Visit projection table — tracks full visit lifecycle."""
    __tablename__ = "visits"

    visit_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    patient_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    appointment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    patient_name: Mapped[str] = mapped_column(String(128), nullable=False)
    patient_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="checked_in")
    check_in_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    service_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # Legacy single service - will be deprecated
    service_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    service_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    staff_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    room_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    note_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | draft | signed | claim_ready
    payment_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | copay_collected | paid | insurance_only | no_charge
    payment_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # cash | card | insurance | no_charge
    copay_collected: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # actual copay amount collected at desk
    wd_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # Temporary legacy field: current implementation merged paper-form W/D into one boolean
    patient_signed: Mapped[bool] = mapped_column(Boolean, default=False)  # patient signed at checkout
    supervising_staff_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # 生诊医生 — supervising/attending physician


# ==================== VISIT TREATMENTS (§11.5 - Multiple Modalities) ====================

class VisitTreatment(Base):
    """Treatment modalities within a visit - supports multiple concurrent treatments."""
    __tablename__ = "visit_treatments"

    treatment_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    visit_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    modality: Mapped[str] = mapped_column(String(64), nullable=False)  # PT, OT, Eval, E-stim, Massage, Cupping, etc.
    therapist_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # Can differ from visit.staff_id
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== CLINICAL NOTE (§11.6) ====================

class ClinicalNote(Base):
    """Clinical note — linked to visit, supports draft/signed lifecycle."""
    __tablename__ = "clinical_notes"

    note_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    visit_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    patient_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    provider_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    template_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SOAP, PT_eval, OT_eval, etc.
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft | final | signed
    content: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # structured note fields
    raw_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # free-text / voice transcript
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== INSURANCE POLICY (§11.7) ====================

class InsurancePolicy(Base):
    """Patient insurance information — supports multiple policies per patient."""
    __tablename__ = "insurance_policies"

    policy_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    carrier_name: Mapped[str] = mapped_column(String(128), nullable=False)
    member_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    group_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    plan_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    copay_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    deductible: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="primary")  # primary | secondary
    eligibility_status: Mapped[str] = mapped_column(String(32), default="unknown")  # unknown | verified | denied | expired
    eligibility_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    eligibility_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visits_authorized: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    visits_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== DOCUMENT (§11.4) ====================

class Document(Base):
    """Document record — intake, consent, signature, attachments."""
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    patient_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    visit_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)  # intake | consent | visitsign | insurance_card | attachment
    template_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)  # auto-incrementing per patient+type
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft | completed | signed | archived
    version: Mapped[int] = mapped_column(Integer, default=1)
    file_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # S3 key or local path
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== TASK / CASE (§11.9) ====================

class Task(Base):
    """Task/case management — replaces Asana for patient-linked tasks."""
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    patient_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    visit_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    claim_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)  # eligibility_verification | insurance_followup | note_completion | claim_followup | general
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")  # open | in_progress | blocked | completed | cancelled
    priority: Mapped[str] = mapped_column(String(16), default="normal")  # low | normal | high | urgent
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    due_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


# ==================== DAILY REPORT (projection) ====================

class DailyReport(Base):
    """Persisted daily report snapshots."""
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clinic_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    report_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    total_check_ins: Mapped[int] = mapped_column(Integer, default=0)
    total_check_outs: Mapped[int] = mapped_column(Integer, default=0)
    total_services_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_appointments: Mapped[int] = mapped_column(Integer, default=0)
    no_shows: Mapped[int] = mapped_column(Integer, default=0)
    open_sessions: Mapped[int] = mapped_column(Integer, default=0)
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
