# Pre-Production Security Blockers

**Status:** Open  
**Date:** 2026-04-03  
**Reviewer:** Staff Security Engineer  
**Priority:** Fix before any production PHI handling  

These are issues in the current code that must be resolved before the HIPAA sprint (PRD-006) begins. They are independent of the compliance roadmap — they represent hardcoded secrets, unauthenticated endpoints, and access control gaps that exist today.

---

## BLOCKER-1: Unauthenticated Debug Endpoints Are Live

**Files:**
- [`backend/app/main.py:102-113`](../../backend/app/main.py#L102-L113) — `/debug-db`
- [`backend/app/routers/db_routes.py:53-64`](../../backend/app/routers/db_routes.py#L53-L64) — `/prototype/debug/httpx-test`
- [`backend/app/routers/db_routes.py:67-93`](../../backend/app/routers/db_routes.py#L67-L93) — `/prototype/debug/room-board-steps`

**Problem:**  
Three debug endpoints have no authentication guard. Any unauthenticated caller can:
- `/debug-db` — obtain DB type, first 40 chars of `DATABASE_URL` (which may include credentials), and full Python traceback
- `/debug/httpx-test` — trigger an outbound HTTP request from the server (SSRF vector)
- `/debug/room-board-steps` — run live DB queries and return row counts

**Fix:**  
Remove all three endpoints, or gate each with `require_role("admin")` if still needed.

---

## BLOCKER-2: `SECRET_KEY` Has a Hardcoded Fallback

**File:** [`backend/app/auth/jwt_utils.py:7`](../../backend/app/auth/jwt_utils.py#L7)

```python
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
```

**Problem:**  
If `SECRET_KEY` is not set in the deployment environment, all JWT tokens are signed with a publicly known key. Any attacker who reads the source code can forge an `admin` token for any `clinic_id` without knowing a password — bypassing authentication entirely.

**Fix:**  
Remove the default. Fail fast at startup if the env var is absent:
```python
SECRET_KEY = os.environ["SECRET_KEY"]  # raises KeyError if missing — intentional
```

---

## BLOCKER-3: Admin Password Printed in Plaintext to Server Logs

**File:** [`backend/app/main.py:65`](../../backend/app/main.py#L65)

```python
print(f"[seed] Test clinic created (id={clinic.clinic_id}), admin: admin@test.clinicos.local / test1234")
```

**Problem:**  
The seeded admin password (`test1234`) is printed to stdout on first boot. If server logs are aggregated (Supabase, CloudWatch, Datadog, Vercel), this credential is visible to anyone with log access. PRD-006 §10 explicitly prohibits secrets in logs.

**Fix:**  
Remove the password from the print statement. Log only the username and clinic ID.

---

## BLOCKER-4: CORS Wildcard with `allow_credentials=True`

**File:** [`backend/app/main.py:80-86`](../../backend/app/main.py#L80-L86)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```

**Problem:**  
Combining `allow_origins=["*"]` with `allow_credentials=True` is a CORS misconfiguration. Per the CORS spec, browsers must not send credentials when the allowed origin is a wildcard — Starlette silently drops the `Access-Control-Allow-Credentials` header in this case, so credentials may not work at all in some browsers. More critically, if this is ever corrected without narrowing the origin list, it would allow any website to make authenticated cross-origin requests on behalf of a logged-in user.

**Fix:**  
Replace `["*"]` with the specific frontend origins:
```python
allow_origins=["http://localhost:8000", "https://clinicos-psi.vercel.app"],
```

---

## HIGH-1: Deactivated User Tokens Remain Valid for Up to 8 Hours

**File:** [`backend/app/auth/deps.py:20-34`](../../backend/app/auth/deps.py#L20-L34)

**Problem:**  
`get_current_user` validates the JWT signature only. It does not query the database to check `user.is_active`. If an admin disables a compromised account, the attacker's existing token continues to work until its 8-hour expiry.

**Fix:**  
Add a DB lookup in `get_current_user` to verify `is_active`. This is a prerequisite for the short-lived token + refresh flow defined in RFC-002 §5.1 (HIPAA-02).

---

## HIGH-2: No Rate Limiting on `/auth/login`

**File:** [`backend/app/routers/auth_routes.py:13`](../../backend/app/routers/auth_routes.py#L13)

**Problem:**  
The login endpoint has no brute-force protection. An attacker can make unlimited password guesses. HIPAA §164.312(d) requires authentication controls that prevent this. PRD-006 HIPAA-08 defines the fix (5 failed attempts → 15-minute lockout), but the `User` model has no `failed_attempts` or `locked_until` columns yet.

**Fix:**  
Implement per-account lockout as specified in RFC-002 §4 (HIPAA-08). This is Sprint 2 in PRD-006 but should be moved to Sprint 1 given the lack of any current mitigation.

---

## HIGH-3: `delete_visit` Is Not Admin-Restricted

**File:** [`backend/app/routers/db_routes.py:215-227`](../../backend/app/routers/db_routes.py#L215-L227)

**Problem:**  
The `DELETE /portal/visits/{visit_id}` endpoint uses `get_current_user` (any authenticated user) instead of `require_role("admin")`. Any frontdesk user can delete visits, which affects the audit trail and event log integrity — a direct conflict with ADR-001 and §164.312(c)(1) Integrity.

**Fix:**  
Change the dependency to `require_role("admin")`.

---

## HIGH-4: `?force=true` Bypasses Duplicate Detection for Any Role

**File:** [`backend/app/routers/db_routes.py:391`](../../backend/app/routers/db_routes.py#L391)

**Problem:**  
`POST /patients?force=true` allows any authenticated user (including `frontdesk`) to bypass duplicate patient detection. This should be an admin-only override.

**Fix:**  
Check `current_user["role"] == "admin"` before honoring `force=True`, or move it to a separate admin endpoint.

---

## HIGH-5: Internal Exception Details Returned to API Callers

**File:** [`backend/app/routers/db_routes.py:323-325`](../../backend/app/routers/db_routes.py#L323-L325)

```python
raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
```

**Problem:**  
Exception class names, DB query fragments, and table names are returned in the HTTP response body. This is information disclosure that can assist an attacker in probing the backend.

**Fix:**  
Log the full exception internally (`logger.exception(...)`) and return a generic `{"detail": "Internal server error"}`.

---

## Remediation Priority Order

| # | Issue | Action |
|---|---|---|
| BLOCKER-1 | Unauthenticated debug endpoints | Remove or gate with `require_role("admin")` |
| BLOCKER-2 | Hardcoded `SECRET_KEY` fallback | Remove default; fail fast at startup |
| BLOCKER-3 | Password in server logs | Remove from `print()` statement |
| BLOCKER-4 | CORS wildcard + credentials | Replace `["*"]` with explicit origin list |
| HIGH-1 | Deactivated users bypass auth | Check `is_active` in `get_current_user` |
| HIGH-2 | No login brute-force protection | Implement HIPAA-08 lockout (move to Sprint 1) |
| HIGH-3 | `delete_visit` not admin-restricted | Change to `require_role("admin")` |
| HIGH-4 | `?force=true` unrestricted | Restrict to admin role |
| HIGH-5 | Exception details in HTTP response | Log internally, return generic 500 |

---

## Relationship to PRD-006 / RFC-002

BLOCKER-1 through BLOCKER-4 and HIGH-3 through HIGH-5 are **not covered** by PRD-006 or RFC-002 — they are implementation bugs independent of the compliance roadmap.

HIGH-1 (deactivated user token) and HIGH-2 (login lockout) **are** covered by PRD-006 (HIPAA-02 and HIPAA-08) but are more urgent than their sprint assignments suggest. They should be pulled into Sprint 1.

All items in this document must be resolved before the PHI audit log (HIPAA-01) is deployed, as there is no point in auditing reads if authentication and access control are not sound.
