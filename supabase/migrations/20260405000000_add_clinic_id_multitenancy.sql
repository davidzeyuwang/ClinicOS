-- Add clinic_id column to all tenant tables for multi-tenant isolation
-- Backfill existing data with the default "Test Clinic" clinic_id

ALTER TABLE patients ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE visits ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE staff ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE rooms ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE visit_treatments ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE event_log ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE daily_reports ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE clinical_notes ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE insurance_policies ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE service_types ADD COLUMN IF NOT EXISTS clinic_id TEXT;
ALTER TABLE staff_service_types ADD COLUMN IF NOT EXISTS clinic_id TEXT;

-- Backfill: assign all existing rows to the first clinic (Test Clinic)
UPDATE patients SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE visits SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE staff SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE rooms SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE appointments SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE visit_treatments SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE event_log SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE daily_reports SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE clinical_notes SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE insurance_policies SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE documents SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE tasks SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE service_types SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;
UPDATE staff_service_types SET clinic_id = '0343c088-def0-457b-8043-af031c86fab1' WHERE clinic_id IS NULL;

-- Create indexes for tenant queries
CREATE INDEX IF NOT EXISTS idx_patients_clinic ON patients(clinic_id);
CREATE INDEX IF NOT EXISTS idx_visits_clinic ON visits(clinic_id);
CREATE INDEX IF NOT EXISTS idx_staff_clinic ON staff(clinic_id);
CREATE INDEX IF NOT EXISTS idx_rooms_clinic ON rooms(clinic_id);
CREATE INDEX IF NOT EXISTS idx_appointments_clinic ON appointments(clinic_id);
CREATE INDEX IF NOT EXISTS idx_visit_treatments_clinic ON visit_treatments(clinic_id);
CREATE INDEX IF NOT EXISTS idx_event_log_clinic ON event_log(clinic_id);
CREATE INDEX IF NOT EXISTS idx_service_types_clinic ON service_types(clinic_id);
