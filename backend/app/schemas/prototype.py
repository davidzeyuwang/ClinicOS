"""Pydantic schemas for ClinicOS API.

Aligned with PRD v2.0 domain model (§9) and functional modules (§11).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ==================== ENUMS / LITERALS ====================

RoomStatus = Literal["available", "occupied", "cleaning", "out_of_service"]
VisitStatus = Literal["checked_in", "in_service", "service_completed", "checked_out"]
AppointmentStatus = Literal["scheduled", "confirmed", "checked_in", "completed", "no_show", "cancelled"]
NoteStatus = Literal["draft", "final", "signed"]
DocumentStatus = Literal["draft", "completed", "signed", "archived"]
TaskStatus = Literal["open", "in_progress", "blocked", "completed", "cancelled"]
TaskPriority = Literal["low", "normal", "high", "urgent"]
EligibilityStatus = Literal["unknown", "verified", "denied", "expired"]
PaymentStatus = Literal["pending", "copay_collected", "paid", "insurance_only", "no_charge"]
PaymentMethod = Literal["cash", "card", "insurance", "no_charge"]


# ==================== ROOM (§11.3) ====================

class RoomCreate(BaseModel):
    name: str
    code: str
    room_type: str = "treatment"
    branch: str = "Main"
    floor: str = "1F"
    active: bool = True


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    room_type: Optional[str] = None
    branch: Optional[str] = None
    floor: Optional[str] = None
    active: Optional[bool] = None
    status: Optional[RoomStatus] = None


# ==================== STAFF (§11.3) ====================

class StaffCreate(BaseModel):
    name: str
    role: str
    license_id: Optional[str] = None
    active: bool = True


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    license_id: Optional[str] = None
    active: Optional[bool] = None


# ==================== PATIENT (§11.1) ====================

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    phone: str
    gender: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    mrn: Optional[str] = None
    notes: Optional[str] = None


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    mrn: Optional[str] = None
    intake_status: Optional[str] = None
    consent_status: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class PatientSearch(BaseModel):
    query: str = Field(description="Search by name, MRN, phone, or email")


# ==================== APPOINTMENT (§11.2) ====================

class AppointmentCreate(BaseModel):
    patient_id: str
    provider_id: Optional[str] = None
    appointment_date: str = Field(description="YYYY-MM-DD")
    appointment_time: Optional[str] = Field(default=None, description="HH:MM")
    appointment_type: str = "regular"  # regular | walk_in | follow_up | eval
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    provider_id: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    appointment_type: Optional[str] = None
    status: Optional[AppointmentStatus] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None


# ==================== VISIT (§11.5) ====================

class PatientCheckIn(BaseModel):
    patient_name: str
    patient_ref: Optional[str] = None
    patient_id: Optional[str] = None
    appointment_id: Optional[str] = None
    actor_id: str


class ServiceStart(BaseModel):
    visit_id: str
    staff_id: str
    room_id: str
    service_type: str
    actor_id: str
    supervising_staff_id: Optional[str] = None


class ServiceEnd(BaseModel):
    visit_id: str
    actor_id: str


class ServiceResume(BaseModel):
    visit_id: str
    actor_id: str


class PatientCheckout(BaseModel):
    visit_id: str
    payment_status: Optional[PaymentStatus] = None
    payment_amount: Optional[float] = None
    payment_method: Optional[PaymentMethod] = None
    copay_collected: Optional[float] = None
    wd_verified: bool = False
    patient_signed: bool = False
    actor_id: str


class VisitPaymentSave(BaseModel):
    visit_id: str
    payment_status: Optional[PaymentStatus] = None
    payment_amount: Optional[float] = None
    payment_method: Optional[PaymentMethod] = None
    copay_collected: Optional[float] = None
    wd_verified: bool = False
    patient_signed: bool = False
    actor_id: str


class RoomStatusChange(BaseModel):
    room_id: str
    status: RoomStatus
    actor_id: str


# ==================== CLINICAL NOTE (§11.6) ====================

class ClinicalNoteCreate(BaseModel):
    visit_id: str
    patient_id: Optional[str] = None
    provider_id: Optional[str] = None
    template_type: Optional[str] = None
    content: Optional[dict] = None
    raw_input: Optional[str] = None


class ClinicalNoteUpdate(BaseModel):
    content: Optional[dict] = None
    raw_input: Optional[str] = None
    status: Optional[NoteStatus] = None


class ClinicalNoteSign(BaseModel):
    note_id: str
    actor_id: str


# ==================== INSURANCE (§11.7) ====================

class InsurancePolicyCreate(BaseModel):
    patient_id: str
    carrier_name: str
    member_id: Optional[str] = None
    group_number: Optional[str] = None
    plan_type: Optional[str] = None
    copay_amount: Optional[float] = None
    deductible: Optional[float] = None
    priority: str = "primary"
    visits_authorized: Optional[int] = None


class InsurancePolicyUpdate(BaseModel):
    carrier_name: Optional[str] = None
    member_id: Optional[str] = None
    group_number: Optional[str] = None
    plan_type: Optional[str] = None
    copay_amount: Optional[float] = None
    deductible: Optional[float] = None
    priority: Optional[str] = None
    eligibility_status: Optional[EligibilityStatus] = None
    eligibility_notes: Optional[str] = None
    visits_authorized: Optional[int] = None
    visits_used: Optional[int] = None
    active: Optional[bool] = None


# ==================== DOCUMENT (§11.4) ====================

class DocumentCreate(BaseModel):
    patient_id: str
    visit_id: Optional[str] = None
    document_type: str  # intake | consent | visitsign | insurance_card | attachment
    template_id: Optional[str] = None
    file_ref: Optional[str] = None
    metadata: Optional[dict] = None


class DocumentUpdate(BaseModel):
    status: Optional[DocumentStatus] = None
    file_ref: Optional[str] = None
    metadata: Optional[dict] = None


class DocumentSign(BaseModel):
    document_id: str
    actor_id: str


# ==================== TASK (§11.9) ====================

class TaskCreate(BaseModel):
    patient_id: Optional[str] = None
    visit_id: Optional[str] = None
    claim_id: Optional[str] = None
    task_type: str = "general"  # eligibility_verification | insurance_followup | note_completion | claim_followup | general
    title: str
    description: Optional[str] = None
    priority: TaskPriority = "normal"
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None


# ==================== REPORT ====================

class DailyReportGenerate(BaseModel):
    actor_id: str
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD. Defaults to today UTC")


# ==================== TREATMENT (§PRD-005) ====================

class TreatmentAdd(BaseModel):
    """Add a treatment modality to an active visit."""
    visit_id: str
    modality: str = Field(description="PT, OT, Eval, E-stim, Massage, Cupping, Acupuncture, etc.")
    therapist_id: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=30, ge=1, le=480)
    notes: Optional[str] = None
    actor_id: str


class TreatmentUpdate(BaseModel):
    """Update treatment details (duration, notes)."""
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=480)
    notes: Optional[str] = None


class TreatmentRecordsFilter(BaseModel):
    """Query filters for treatment records."""
    date_from: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    date_to: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    patient_id: Optional[str] = None
    staff_id: Optional[str] = None  # therapist
    modality: Optional[str] = None


# ==================== EVENT ====================

class EventEnvelope(BaseModel):
    event_id: str
    event_type: str
    occurred_at: datetime
    actor_id: str
    idempotency_key: str
    payload: dict


# ==================== SERVICE TYPES ====================

class ServiceTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)

class ServiceTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    is_active: Optional[bool] = None

class StaffServiceTypesSet(BaseModel):
    """Replace-all: sets exact list of service type IDs for a staff member."""
    service_type_ids: list[str]


# ==================== AUTH SCHEMAS ====================

class LoginRequest(BaseModel):
    email: Optional[str] = None      # login with email
    username: Optional[str] = None   # or login with username alias
    password: str

    @property
    def identifier(self) -> str:
        """Return whichever identifier was supplied."""
        return self.email or self.username or ""


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    clinic_id: str
    role: str
    display_name: str


class RegisterClinicRequest(BaseModel):
    clinic_name: str
    slug: str
    admin_email: str
    admin_password: str
    admin_display_name: str = ""
    admin_username: Optional[str] = None   # optional short alias for the admin


class AdminUserCreateRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""
    role: str = "frontdesk"  # admin | frontdesk | doctor
    username: Optional[str] = None


class CreateTestUserRequest(BaseModel):
    email: str
    username: Optional[str] = None   # optional short alias
    password: str
    display_name: str = ""
    role: str = "frontdesk"  # admin | frontdesk | doctor
