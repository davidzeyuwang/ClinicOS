-- Migration: add clinics and users tables for multi-tenant auth
-- Safe to re-run (IF NOT EXISTS guards).

-- CLINICS (multi-tenancy root)
CREATE TABLE IF NOT EXISTS clinics (
  clinic_id  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name       TEXT NOT NULL,
  slug       TEXT UNIQUE NOT NULL,
  timezone   TEXT NOT NULL DEFAULT 'America/New_York',
  is_active  BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_clinics_slug ON clinics(slug);

-- USERS (application users with RBAC)
CREATE TABLE IF NOT EXISTS users (
  user_id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  clinic_id        TEXT NOT NULL REFERENCES clinics(clinic_id),
  email            TEXT UNIQUE NOT NULL,
  username         TEXT UNIQUE,
  hashed_password  TEXT NOT NULL,
  display_name     TEXT NOT NULL DEFAULT '',
  role             TEXT NOT NULL DEFAULT 'frontdesk',
  is_active        BOOLEAN NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_clinic ON users(clinic_id);
CREATE INDEX IF NOT EXISTS idx_users_email  ON users(email);
