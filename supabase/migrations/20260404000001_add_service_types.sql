-- Migration: add service_types table and staff_service_types junction
-- Safe to re-run (IF NOT EXISTS guards).

CREATE TABLE IF NOT EXISTS service_types (
  service_type_id  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  name             TEXT UNIQUE NOT NULL,
  is_active        BOOLEAN NOT NULL DEFAULT true,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staff_service_types (
  staff_id         TEXT NOT NULL REFERENCES staff(staff_id) ON DELETE CASCADE,
  service_type_id  TEXT NOT NULL REFERENCES service_types(service_type_id) ON DELETE CASCADE,
  PRIMARY KEY (staff_id, service_type_id)
);
CREATE INDEX IF NOT EXISTS idx_sst_staff   ON staff_service_types(staff_id);
CREATE INDEX IF NOT EXISTS idx_sst_stype   ON staff_service_types(service_type_id);

-- Seed default service types
INSERT INTO service_types (name, is_active) VALUES
  ('PT', true),  ('OT', true),  ('Eval', true),
  ('E-stim', true), ('Massage', true), ('Cupping', true),
  ('Acupuncture', true), ('Traction', true)
ON CONFLICT (name) DO NOTHING;
