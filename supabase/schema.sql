-- ClinicOS — Supabase (PostgreSQL) schema
-- Run this once in the Supabase SQL Editor before deploying.

-- EVENT LOG (append-only, sacred — ADR-001)
CREATE TABLE IF NOT EXISTS event_log (
  id              SERIAL PRIMARY KEY,
  event_id        TEXT UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
  event_type      TEXT NOT NULL,
  occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor_id        TEXT NOT NULL,
  idempotency_key TEXT UNIQUE NOT NULL DEFAULT gen_random_uuid()::text,
  schema_version  INT NOT NULL DEFAULT 1,
  payload         JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_event_log_type ON event_log(event_type);

-- ROOMS
CREATE TABLE IF NOT EXISTS rooms (
  room_id    TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name       TEXT NOT NULL,
  code       TEXT NOT NULL,
  room_type  TEXT NOT NULL DEFAULT 'treatment',
  branch     TEXT DEFAULT 'Main',
  floor      TEXT DEFAULT '1F',
  active     BOOLEAN NOT NULL DEFAULT true,
  status     TEXT NOT NULL DEFAULT 'available',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- STAFF
CREATE TABLE IF NOT EXISTS staff (
  staff_id   TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name       TEXT NOT NULL,
  role       TEXT NOT NULL,
  license_id TEXT,
  active     BOOLEAN NOT NULL DEFAULT true,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- PATIENTS
CREATE TABLE IF NOT EXISTS patients (
  patient_id     TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  first_name     TEXT NOT NULL,
  last_name      TEXT NOT NULL,
  date_of_birth  TEXT,
  gender         TEXT,
  phone          TEXT,
  email          TEXT,
  address        TEXT,
  mrn            TEXT UNIQUE,
  intake_status  TEXT NOT NULL DEFAULT 'pending',
  consent_status TEXT NOT NULL DEFAULT 'pending',
  notes          TEXT,
  active         BOOLEAN NOT NULL DEFAULT true,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- APPOINTMENTS
CREATE TABLE IF NOT EXISTS appointments (
  appointment_id      TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  patient_id          TEXT NOT NULL,
  provider_id         TEXT,
  appointment_date    TEXT NOT NULL,
  appointment_time    TEXT,
  appointment_type    TEXT NOT NULL DEFAULT 'regular',
  status              TEXT NOT NULL DEFAULT 'scheduled',
  cancellation_reason TEXT,
  notes               TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_appts_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appts_date    ON appointments(appointment_date);

-- VISITS
CREATE TABLE IF NOT EXISTS visits (
  visit_id           TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  patient_id         TEXT,
  appointment_id     TEXT,
  patient_name       TEXT NOT NULL,
  patient_ref        TEXT,
  status             TEXT NOT NULL DEFAULT 'checked_in',
  check_in_time      TIMESTAMPTZ,
  service_type       TEXT,
  service_start_time TIMESTAMPTZ,
  service_end_time   TIMESTAMPTZ,
  check_out_time     TIMESTAMPTZ,
  staff_id           TEXT,
  room_id            TEXT,
  note_status        TEXT NOT NULL DEFAULT 'pending',
  payment_status     TEXT NOT NULL DEFAULT 'pending',
  payment_amount     FLOAT,
  payment_method     TEXT,
  copay_collected    NUMERIC(10,2),
  wd_verified        BOOLEAN NOT NULL DEFAULT false,
  patient_signed     BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_visits_patient ON visits(patient_id);
-- Migration helper (idempotent for existing databases):
ALTER TABLE visits ADD COLUMN IF NOT EXISTS copay_collected NUMERIC(10,2);
ALTER TABLE visits ADD COLUMN IF NOT EXISTS wd_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE visits ADD COLUMN IF NOT EXISTS patient_signed BOOLEAN NOT NULL DEFAULT false;

-- CLINICAL NOTES
CREATE TABLE IF NOT EXISTS clinical_notes (
  note_id       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  visit_id      TEXT NOT NULL,
  patient_id    TEXT,
  provider_id   TEXT,
  template_type TEXT,
  status        TEXT NOT NULL DEFAULT 'draft',
  content       JSONB,
  raw_input     TEXT,
  signed_at     TIMESTAMPTZ,
  signed_by     TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notes_visit   ON clinical_notes(visit_id);
CREATE INDEX IF NOT EXISTS idx_notes_patient ON clinical_notes(patient_id);

-- INSURANCE POLICIES
CREATE TABLE IF NOT EXISTS insurance_policies (
  policy_id               TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  patient_id              TEXT NOT NULL,
  carrier_name            TEXT NOT NULL,
  member_id               TEXT,
  group_number            TEXT,
  plan_type               TEXT,
  copay_amount            FLOAT,
  deductible              FLOAT,
  priority                TEXT NOT NULL DEFAULT 'primary',
  eligibility_status      TEXT NOT NULL DEFAULT 'unknown',
  eligibility_verified_at TIMESTAMPTZ,
  eligibility_notes       TEXT,
  visits_authorized       INT,
  visits_used             INT,
  active                  BOOLEAN NOT NULL DEFAULT true,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_insurance_patient ON insurance_policies(patient_id);

-- DOCUMENTS
CREATE TABLE IF NOT EXISTS documents (
  document_id     TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  patient_id      TEXT NOT NULL,
  visit_id        TEXT,
  document_type   TEXT NOT NULL,
  template_id     TEXT,
  sequence_number INT NOT NULL DEFAULT 1,
  status          TEXT NOT NULL DEFAULT 'draft',
  version         INT NOT NULL DEFAULT 1,
  file_ref        TEXT,
  metadata        JSONB,
  signed_at       TIMESTAMPTZ,
  signed_by       TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_docs_patient ON documents(patient_id);

-- TASKS
CREATE TABLE IF NOT EXISTS tasks (
  task_id      TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  patient_id   TEXT,
  visit_id     TEXT,
  claim_id     TEXT,
  task_type    TEXT NOT NULL,
  title        TEXT NOT NULL,
  description  TEXT,
  status       TEXT NOT NULL DEFAULT 'open',
  priority     TEXT NOT NULL DEFAULT 'normal',
  assignee_id  TEXT,
  due_date     TEXT,
  completed_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tasks_patient ON tasks(patient_id);

-- VISIT TREATMENTS (PRD-005)
CREATE TABLE IF NOT EXISTS visit_treatments (
  treatment_id     TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  visit_id         TEXT NOT NULL REFERENCES visits(visit_id),
  modality         TEXT NOT NULL,
  therapist_id     TEXT REFERENCES staff(staff_id),
  duration_minutes INT,
  started_at       TIMESTAMPTZ,
  completed_at     TIMESTAMPTZ,
  notes            TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_visit_treatments_visit ON visit_treatments(visit_id);
CREATE INDEX IF NOT EXISTS idx_visit_treatments_therapist ON visit_treatments(therapist_id);

-- DAILY REPORTS
CREATE TABLE IF NOT EXISTS daily_reports (
  id                       SERIAL PRIMARY KEY,
  report_date              TEXT NOT NULL,
  total_check_ins          INT NOT NULL DEFAULT 0,
  total_check_outs         INT NOT NULL DEFAULT 0,
  total_services_completed INT NOT NULL DEFAULT 0,
  total_appointments       INT NOT NULL DEFAULT 0,
  no_shows                 INT NOT NULL DEFAULT 0,
  open_sessions            INT NOT NULL DEFAULT 0,
  report_data              JSONB NOT NULL,
  generated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_daily_reports_date ON daily_reports(report_date);
