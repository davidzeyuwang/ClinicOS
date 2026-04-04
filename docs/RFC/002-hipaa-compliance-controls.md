# RFC-002: HIPAA Compliance Controls

**Status:** Draft  
**Date:** 2026-04-04  
**Owner:** Architecture / Compliance  
**Related PRD:** `docs/PRD/006-hipaa-compliance.md`

---

## 1. Summary

This RFC defines the technical design for HIPAA-focused controls in ClinicOS:

- PHI read audit logging
- session timeout and refresh-token model
- field-level encryption
- HTTPS / HSTS enforcement
- minimum necessary field filtering
- unique user identification hardening
- login lockout
- break-glass access
- event-log hash chaining
- breach detection and notification

---

## 2. Current-State Constraints

- Current auth uses username + password, JWT access tokens, and RBAC
- Current access token lifetime is 8 hours
- Current `event_log` records write actions only
- Current tenant/user context is available through `CurrentUser`
- Current service layer is already clinic-scoped

These features should extend the current architecture rather than replace it.

---

## 3. Event Schemas

### 3.1 New event types

- `PHI_ACCESSED`
- `SESSION_EXPIRED`
- `PASSWORD_RESET_REQUIRED`
- `ACCOUNT_LOCKED`
- `BREAK_GLASS_ACCESS`
- `EVENT_CHAIN_VERIFIED`
- `EVENT_CHAIN_FAILED`
- `BREACH_ALERT`

### 3.2 Event payloads

#### `PHI_ACCESSED`

```json
{
  "clinic_id": "uuid",
  "actor_user_id": "uuid",
  "resource_type": "patient|insurance_policy|clinical_note|document|visit",
  "resource_id": "uuid",
  "patient_id": "uuid",
  "route": "/prototype/patients/{patient_id}",
  "method": "GET",
  "ip_address": "203.0.113.10",
  "user_agent": "Mozilla/5.0",
  "access_scope": "detail|list|export",
  "occurred_at": "2026-04-04T12:00:00Z"
}
```

#### `ACCOUNT_LOCKED`

```json
{
  "clinic_id": "uuid",
  "user_id": "uuid",
  "username": "frontdesk@test.local",
  "failed_attempts": 5,
  "locked_until": "2026-04-04T12:15:00Z",
  "ip_address": "203.0.113.10"
}
```

#### `BREAK_GLASS_ACCESS`

```json
{
  "clinic_id": "uuid",
  "actor_user_id": "uuid",
  "reason": "ER callback / urgent chart access",
  "granted_at": "2026-04-04T12:00:00Z",
  "expires_at": "2026-04-04T16:00:00Z",
  "scope": "patient|clinic|support_override"
}
```

#### `BREACH_ALERT`

```json
{
  "clinic_id": "uuid",
  "alert_type": "bulk_export|failed_auth_burst|event_chain_failure",
  "actor_user_id": "uuid",
  "ip_address": "203.0.113.10",
  "threshold": 50,
  "observed_value": 72,
  "triggered_at": "2026-04-04T12:00:00Z"
}
```

---

## 4. Data Model Changes

### HIPAA-01 / HIPAA-10

#### `phi_access_audit`

```sql
CREATE TABLE phi_access_audit (
    audit_id         UUID PRIMARY KEY,
    clinic_id        UUID NOT NULL,
    actor_user_id    UUID NOT NULL,
    resource_type    VARCHAR(64) NOT NULL,
    resource_id      VARCHAR(36) NOT NULL,
    patient_id       VARCHAR(36),
    route            TEXT NOT NULL,
    http_method      VARCHAR(8) NOT NULL,
    access_scope     VARCHAR(32) NOT NULL,
    ip_address       VARCHAR(64),
    user_agent       TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_phi_access_audit_clinic_time
ON phi_access_audit (clinic_id, created_at DESC);
```

### HIPAA-02 / HIPAA-08

#### `users` additions

```sql
ALTER TABLE users ADD COLUMN refresh_token_hash TEXT;
ALTER TABLE users ADD COLUMN refresh_token_expires_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN last_login_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN failed_attempts INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
```

### HIPAA-03

Add encrypted-shadow columns or convert designated fields to encrypted storage:

- `patients.date_of_birth_enc`
- `patients.phone_enc`
- `patients.address_enc`
- `insurance_policies.member_id_enc`

Recommended pattern:
- keep app-level typed properties
- store ciphertext in DB columns
- avoid plaintext duplicate columns after migration completes

### HIPAA-06

#### `break_glass_sessions`

```sql
CREATE TABLE break_glass_sessions (
    session_id       UUID PRIMARY KEY,
    clinic_id        UUID NOT NULL,
    actor_user_id    UUID NOT NULL,
    reason           TEXT NOT NULL,
    scope            VARCHAR(64) NOT NULL,
    granted_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at       TIMESTAMPTZ NOT NULL,
    revoked_at       TIMESTAMPTZ
);
```

### HIPAA-09

#### `event_log` additions

```sql
ALTER TABLE event_log ADD COLUMN prev_hash TEXT;
ALTER TABLE event_log ADD COLUMN row_hash TEXT;
```

---

## 5. API Contracts

### 5.1 Auth / Session

- `POST /prototype/auth/login`
  - enforce lockout
  - return access token + refresh token
- `POST /prototype/auth/refresh`
  - validate refresh token
  - return rotated access token
- `POST /prototype/auth/logout`
  - revoke refresh token
- `POST /prototype/auth/change-password`
  - satisfy first-login reset requirement

### 5.2 PHI Audit

No public endpoint required in v1 for regular users.

Admin/compliance endpoints:

- `GET /prototype/admin/phi-access-audit`
- filters:
  - patient_id
  - actor_user_id
  - resource_type
  - date range

### 5.3 Break Glass

- `POST /prototype/admin/break-glass`
- `DELETE /prototype/admin/break-glass/{session_id}`
- `GET /prototype/admin/break-glass`

### 5.4 Clinic security alerts

- `GET /prototype/admin/security-alerts`

---

## 6. Minimum Necessary Filtering Design

Implement serializer-level or response-builder-level field filtering.

### Frontdesk

Allowed:
- patient demographics
- insurance details
- scheduling details
- checkout fields

Blocked:
- clinical note `content`
- clinical note `raw_input`

### Doctor

Allowed:
- visit history
- treatment details
- note content
- patient demographics needed for treatment

Blocked / limited:
- broad financial details beyond copay/payment context needed for care

### Admin

Allowed:
- all fields

Implementation rule:
- backend filtering is the source of truth
- frontend hiding is secondary

---

## 7. Encryption Design

### 7.1 Field encryption

Use Fernet for selected fields.

Key source:
- environment variable, e.g. `FERNET_KEY`

Pattern:

```python
encrypt(value: str) -> str
decrypt(value: str) -> str
```

### 7.2 Search constraints

Encrypted fields cannot support normal plaintext search without extra design.

Initial recommendation:
- do not support arbitrary search on encrypted fields
- continue searching patients by name / MRN
- exact-match flows on encrypted values can use deterministic sidecar hash if needed later

### 7.3 Transport

Production middleware:
- reject or redirect HTTP
- set HSTS headers
- trust proxy headers only in configured environments

---

## 8. Event Log Integrity Design

For each new event row:

```text
row_hash = SHA256(prev_hash + canonical_json(payload) + event_type + occurred_at + actor_id)
```

Store:
- `prev_hash`
- `row_hash`

Daily job:
- walks chain in order
- recomputes hashes
- logs `EVENT_CHAIN_VERIFIED` or `EVENT_CHAIN_FAILED`

---

## 9. Breach Detection Design

### Rules

1. bulk export threshold
2. failed auth burst by IP
3. event chain verification failure

### Notification

Initial channel:
- admin email

Future channels:
- webhook
- Slack / pager

---

## 10. Migration Plan

### Phase A
- add `users` columns for lockout/session/password-change metadata
- add `phi_access_audit`
- add `event_log` hash columns
- add `break_glass_sessions`

### Phase B
- introduce refresh token flow
- shorten access-token TTL
- add frontend idle timeout behavior

### Phase C
- add field encryption and backfill migration
- verify decrypt path in services/serializers

### Phase D
- add minimum necessary filtering
- add audit logging on read paths

### Phase E
- add breach detection jobs and notifications
- add event-chain verification job

---

## 11. Task Breakdown

### HIPAA-BE-01
Implement PHI read audit logging

### HIPAA-BE-02
Implement short-lived access tokens + refresh tokens + idle timeout support hooks

### HIPAA-BE-03
Implement Fernet field-level encryption for designated PHI columns

### HIPAA-BE-04
Implement HTTPS enforcement + HSTS middleware

### HIPAA-BE-05
Implement minimum necessary field filtering by role

### HIPAA-BE-06
Implement unique-user hardening: first-login password reset + last-login tracking

### HIPAA-BE-07
Implement login lockout policy

### HIPAA-BE-08
Implement break-glass emergency access workflow

### HIPAA-BE-09
Implement event-log hash chaining + daily verification

### HIPAA-BE-10
Implement breach detection + admin notification

---

## 12. Testing Plan

- backend unit tests for encryption, lockout, token refresh, field filtering
- API tests for auth/session and admin compliance routes
- E2E tests for idle timeout and role-scoped UI behavior
- migration tests for encrypted-field backfill
- scheduled-job verification tests for event chain and breach detection

---

## 13. Risks

- field encryption may complicate search and support workflows
- read-audit coverage can be missed if enforced inconsistently
- break-glass can be abused if approval/reporting is too weak
- short access tokens can degrade UX if refresh handling is fragile

---

## 14. Decision

ClinicOS should implement HIPAA controls as incremental extensions of the current authenticated, tenant-scoped architecture, not as a parallel compliance subsystem.
