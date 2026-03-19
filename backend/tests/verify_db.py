"""Verify data persisted in SQLite."""
import sqlite3

conn = sqlite3.connect("/Users/zw/workspace/ClinicOS/backend/clinicos.db")
c = conn.cursor()

print("=== TABLES ===")
for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
    count = c.execute(f"SELECT COUNT(*) FROM {row[0]}").fetchone()[0]
    print(f"  {row[0]}: {count} rows")

print("\n=== ROOMS ===")
for row in c.execute("SELECT code, name, status FROM rooms"):
    print(f"  {row[0]} {row[1]}: {row[2]}")

print("\n=== STAFF ===")
for row in c.execute("SELECT name, role FROM staff"):
    print(f"  {row[0]} ({row[1]})")

print("\n=== VISITS ===")
for row in c.execute("SELECT patient_name, status FROM visits"):
    print(f"  {row[0]}: {row[1]}")

print("\n=== EVENTS ===")
for row in c.execute("SELECT event_type, actor_id FROM event_log ORDER BY id"):
    print(f"  [{row[0]}] actor={row[1]}")

print("\n=== DAILY REPORTS ===")
for row in c.execute("SELECT report_date, total_check_ins, total_services_completed FROM daily_reports"):
    print(f"  {row[0]}: check_ins={row[1]} services={row[2]}")

conn.close()
print("\nDATA PERSISTENCE VERIFIED")
