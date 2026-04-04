# PRD-006: HIPAA Compliance Controls

**Status:** Draft v1  
**Date:** 2026-04-04  
**Owner:** Product / Compliance  
**Related:** `PRD/003-clinic-os-prd-v2.md`, `ADR/001-event-sourcing.md`, `RFC/001-auth-rbac-multitenancy.md`

---

## 1. Background

ClinicOS stores and processes protected health information (PHI) across patient, visit, insurance, treatment, note, and document workflows. The current system already has:

- JWT authentication
- role-based access control
- clinic-scoped multi-tenancy
- immutable append-only `event_log` for write-side actions

However, current controls are not yet sufficient for HIPAA-aligned production use. In particular:

- PHI read access is not fully audited
- idle session timeout is not enforced
- field-level encryption is not implemented
- minimum necessary access is incomplete
- lockout, breach detection, and break-glass controls are missing
- event-log integrity verification is not cryptographically chained

This PRD defines the next compliance-focused delivery slice.

---

## 2. Goals

- Add the highest-priority HIPAA-aligned technical safeguards to ClinicOS
- Reduce PHI exposure risk in day-to-day clinic operations
- Improve auditability for internal review and future compliance review
- Preserve the current FastAPI + SQLAlchemy + PostgreSQL/Supabase architecture

## 3. Non-Goals

- Full legal certification or formal HIPAA attestation
- BAAs, contracts, or policy-process documentation outside the application
- replacing Supabase-managed disk encryption
- full SIEM/SOC integration in this phase
- organization-wide IAM/SSO

---

## 4. Current PHI Inventory

| Table | PHI Fields | Sensitivity |
|---|---|---|
| `patients` | `first_name`, `last_name`, `date_of_birth`, `phone`, `email`, `address`, `mrn` | High |
| `insurance_policies` | `member_id`, `group_number`, `carrier_name`, `copay_amount` | High |
| `clinical_notes` | `content`, `raw_input` | High |
| `visits` | `patient_name`, `patient_id`, `service_type`, `payment_amount`, `copay_collected` | Medium |
| `appointments` | `patient_id`, `appointment_date`, `appointment_time`, `notes` | Medium |
| `documents` | `metadata`, `file_ref`, `patient_id` | Medium |
| `visit_treatments` | `modality`, `therapist_id`, `notes`, `duration_minutes` | Medium |
| `tasks` | `patient_id`, `description` | Low |

---

## 5. Existing Technical Baseline

### Already implemented

- JWT auth with HS256
- bcrypt password hashing
- RBAC via `require_role()`
- `clinic_id` tenant scoping on core tables and queries
- append-only write event log
- Pydantic request validation

### Important current-state notes

- Current login uses `username`, not `email`
- Current clinic creation route is `/prototype/auth/register-clinic`, admin-only
- Current JWT access token lifetime is 8 hours
- Current event log covers writes, not comprehensive PHI reads

---

## 6. User Roles

| Role | Purpose | Compliance Relevance |
|---|---|---|
| `admin` | Clinic administration and configuration | highest access, must be most audited |
| `frontdesk` | patient intake, scheduling, checkout, insurance coordination | needs demographic + insurance access, should not see full clinical notes |
| `doctor` | treatment, note review, clinical decision-making | needs clinical context, should not see unnecessary financial detail |

---

## 7. Features

## P0 — Must Have (Sprint 1)

### HIPAA-01: PHI Audit Log

**Problem:** Current `event_log` captures write-side events, but not all PHI read access.

**Requirement:**
- Log every read access to PHI-bearing records
- Capture:
  - who accessed
  - what entity was accessed
  - patient context if applicable
  - when
  - route / action
  - source IP / user agent when available

**Acceptance Criteria:**
- Reading patient detail creates audit entry
- Reading clinical note content creates audit entry
- Reading insurance policy detail creates audit entry
- Audit log excludes raw PHI payload values

### HIPAA-02: Session Timeout + Token Lifecycle

**Problem:** Current JWT lasts 8 hours, with no idle timeout enforcement and no key rotation mechanism.

**Requirement:**
- Auto-logout after 15 minutes inactivity
- Frontend clears local token/session state
- Access tokens are short-lived (15-minute TTL)
- Refresh tokens are long-lived (7 days), stored server-side as a hash
- `SECRET_KEY` must be rotatable without requiring all users to re-authenticate mid-session
- Rotation procedure is documented and executable by any admin

**Acceptance Criteria:**
- 15 minutes idle in UI logs user out
- Expired access token returns `401`
- Refresh flow issues new access token without forcing immediate login when refresh token is valid
- `SECRET_KEY` can be rotated by updating environment config + redeploying; active refresh tokens remain valid during the overlap window
- Rotation is logged as a `KEY_ROTATED` event in the audit trail
- After rotation, old access tokens (signed with previous key) are rejected immediately

### HIPAA-03: Encryption at Rest (Field Level)

**Problem:** Database disk encryption exists in managed infrastructure, but especially sensitive fields remain plaintext at application level.

**Requirement:**
- Add application-layer field encryption using Fernet for:
  - `patients.date_of_birth`
  - `patients.phone`
  - `patients.address`
  - `insurance_policies.member_id`
- Keep search/index strategy explicit for encrypted fields

**Acceptance Criteria:**
- Encrypted fields are unreadable in DB without app key
- Application transparently decrypts for authorized users
- Key management configuration is environment-based

### HIPAA-04: Encryption in Transit

**Problem:** Transport security requirements are not explicitly enforced at app layer.

**Requirement:**
- Enforce HTTPS in production
- Add HSTS headers
- Reject insecure HTTP requests in production deployment

**Acceptance Criteria:**
- Production responses include HSTS
- HTTP is redirected or rejected
- Local development remains usable without HTTPS

## P1 — Second Sprint

### HIPAA-05: Minimum Necessary Access

**Problem:** Role checks exist, but field-level PHI exposure is broader than necessary.

**Requirement:**
- Field-filter responses by role

**Target access model:**
- `frontdesk`:
  - demographics
  - insurance
  - scheduling
  - checkout data
  - no full clinical note content
- `doctor`:
  - clinical notes
  - visit history
  - treatments
  - no unnecessary payment detail beyond copay context
- `admin`:
  - full clinic access

**Acceptance Criteria:**
- Frontdesk note list omits note content/body
- Doctor financial views omit unnecessary amounts
- Admin sees full records

### HIPAA-07: Unique User Identification

**Problem:** Unique named users exist conceptually, but stronger user-identification controls are needed.

**Requirement:**
- No shared login accounts
- Prevent duplicate usernames within required uniqueness scope
- Track `last_login_at`
- Require password change on first login for newly created users

**Acceptance Criteria:**
- New users are flagged for first-login password reset
- Duplicate usernames are rejected according to chosen uniqueness rule
- Last login timestamp updates on successful login

### HIPAA-08: Login Lockout

**Problem:** Repeated failed authentication attempts are not rate-limited at the user-account level.

**Requirement:**
- 5 failed login attempts triggers 15-minute lockout
- Track with `failed_attempts` and `locked_until`

**Acceptance Criteria:**
- 5 bad passwords lock the account
- Valid password during lockout still returns locked error
- Successful login resets failed attempt count

## P2 — Third Sprint

### HIPAA-06: Break-Glass Emergency Access

**Problem:** Emergency access process for exceptional cross-boundary access is not defined.

**Requirement:**
- Admin-only emergency override
- Requires reason string
- Logged as `BREAK_GLASS_ACCESS`
- Auto-expires after 4 hours

**Acceptance Criteria:**
- Break-glass grant requires explicit reason
- All break-glass use is auditable
- Access expires automatically

### HIPAA-09: Event Log Integrity

**Problem:** Event log is append-only but not cryptographically chained.

**Requirement:**
- Add SHA-256 hash chaining:
  - `prev_hash`
  - `row_hash`
- Daily verification job validates chain

**Acceptance Criteria:**
- New events store hash chain values
- Verification job detects tampering/gaps
- Integrity failure emits alert event

### HIPAA-10: Breach Detection + Notification

**Problem:** Suspicious access/export patterns are not automatically detected.

**Requirement:**
- Detect:
  - >50 patient records exported in one request
  - >3 failed auth attempts in 5 minutes from same IP
- Alert admin by email
- Log `BREACH_ALERT`

**Acceptance Criteria:**
- Trigger conditions produce alert event
- Admin email notification is sent
- Alert is visible in internal audit trail

---

## 8. User Stories

- As a compliance officer, I want every PHI access recorded so I can investigate inappropriate access.
- As a clinic manager, I want users auto-logged out after inactivity so unattended devices do not expose PHI.
- As a patient, I want my sensitive data protected at rest and in transit.
- As front desk, I want only the PHI I need so I can do my work without overexposure.
- As an admin, I want emergency override access only when necessary and fully logged.

---

## 9. Functional Requirements

1. The system must log both PHI writes and PHI reads.
2. The system must identify each access by authenticated user.
3. The system must support session expiry and idle timeout.
4. The system must enforce HTTPS in production environments.
5. The system must support role-based field filtering.
6. The system must support lockout after repeated failed login attempts.
7. The system must support first-login password reset flow.
8. The system must support break-glass override with expiration.
9. The system must support cryptographic integrity verification of event history.
10. The system must support automated suspicious-activity alerts.

---

## 10. Security / Compliance Constraints

- No PHI values in application logs or HTTP error messages
- PHI read-audit records must avoid storing raw PHI bodies
- Secrets for JWT, Fernet, and email providers must be environment-managed
- Encryption keys must not be stored in source control
- Local dev mode may use relaxed transport constraints, production may not
- `SECRET_KEY` must be unique per environment (local ≠ production)
- `SECRET_KEY` must be rotated at least quarterly, or immediately on suspected compromise
- Rotation must be logged as a `KEY_ROTATED` event visible in the audit trail
- Login identifier is `username` in current implementation; decision to migrate to `email` is tracked in Open Question #1

---

## 11. Edge Cases

- User is active in one browser tab but idle in another
- Refresh token expired while access token is still cached in UI
- Frontdesk accesses patient detail with embedded clinical note previews
- Doctor linked to staff record but viewing another doctor’s notes
- Break-glass session spans midnight or timezone boundaries
- Event-chain verification job runs while writes are happening
- Export threshold is triggered by a legitimate bulk operation

---

## 12. Success Metrics

- 100% of PHI read routes covered by audit logging
- 100% of protected routes require authenticated user context
- Idle sessions expire at 15 minutes in UI behavior tests
- Field-level encryption enabled for all designated fields
- Lockout and breach alerts verified by automated tests

---

## 13. Out of Scope for This PRD

- enterprise SSO
- device management / MDM
- workstation disk encryption outside app boundary
- business policy/training documents
- legal incident response workflow beyond app-level alerting

---

## 14. Release Plan

### Sprint 1
- HIPAA-01
- HIPAA-02
- HIPAA-03
- HIPAA-04

### Sprint 2
- HIPAA-05
- HIPAA-07
- HIPAA-08

### Sprint 3
- HIPAA-06
- HIPAA-09
- HIPAA-10

---

## 15. Open Questions

1. Should username remain the unique login identifier, or move to email? (RFC-001 uses email; current implementation uses username — must be resolved before HIPAA-07)
2. Should first-login password change apply only to admin-created users, or all new users?
3. What export actions count toward breach/export thresholds?
4. Does break-glass apply only within clinic boundaries, or also for future multi-clinic support staff?
5. What email provider should deliver breach notifications in production?
6. What is the target access token TTL once HIPAA-02 is implemented? (15 minutes recommended to match idle timeout)
7. Should zero-downtime key rotation support an overlap window where both old and new keys are accepted simultaneously? (Required if refresh token TTL > 0 at rotation time — see RFC-002 §6)
