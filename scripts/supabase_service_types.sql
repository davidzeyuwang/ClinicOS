-- Migration: add service_types + staff_service_types tables
-- Run this once in your Supabase SQL editor before deploying
-- Safe to run multiple times (CREATE TABLE IF NOT EXISTS).

-- ── Service type registry ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS service_types (
    service_type_id VARCHAR(36) PRIMARY KEY,
    name            VARCHAR(64) NOT NULL UNIQUE,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Staff ↔ service type qualification matrix ────────────────────────────────
CREATE TABLE IF NOT EXISTS staff_service_types (
    staff_id        VARCHAR(36) REFERENCES staff(staff_id) ON DELETE CASCADE,
    service_type_id VARCHAR(36) REFERENCES service_types(service_type_id) ON DELETE CASCADE,
    PRIMARY KEY (staff_id, service_type_id)
);

-- Index for reverse lookup (service_type → qualified staff)
CREATE INDEX IF NOT EXISTS idx_sst_service_type_id
    ON staff_service_types (service_type_id);

-- After running this migration, seed service types via:
--   python3 scripts/seed_prod.py
