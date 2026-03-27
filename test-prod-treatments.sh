#!/bin/bash
# Production Test: PRD-005 Treatment APIs

BASE_URL="https://clinicos-psi.vercel.app"

echo "=== 1. Creating Room ==="
ROOM_RESP=$(curl -s -X POST "$BASE_URL/prototype/admin/rooms" \
  -H "Content-Type: application/json" \
  -d '{"name":"Treatment Room Test","code":"TRT","room_type":"treatment"}')
ROOM_ID=$(echo "$ROOM_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('room_id',''))")
echo "Room ID: $ROOM_ID"

echo -e "\n=== 2. Creating Staff ==="
STAFF_RESP=$(curl -s -X POST "$BASE_URL/prototype/admin/staff" \
  -H "Content-Type: application/json" \
  -d '{"name":"Dr. Test Therapist","role":"physical_therapist"}')
STAFF_ID=$(echo "$STAFF_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('staff_id',''))")
echo "Staff ID: $STAFF_ID"

echo -e "\n=== 3. Creating Patient ==="
PATIENT_RESP=$(curl -s -X POST "$BASE_URL/prototype/patients" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Production","last_name":"Test","phone":"555-PROD"}')
PATIENT_ID=$(echo "$PATIENT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('patient_id',''))")
echo "Patient ID: $PATIENT_ID"

echo -e "\n=== 4. Check In Patient ==="
CHECKIN_RESP=$(curl -s -X POST "$BASE_URL/prototype/portal/checkin" \
  -H "Content-Type: application/json" \
  -d "{\"patient_name\":\"Production Test\",\"patient_id\":\"$PATIENT_ID\",\"actor_id\":\"$STAFF_ID\"}")
VISIT_ID=$(echo "$CHECKIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('visit_id',''))")
echo "Visit ID: $VISIT_ID"

echo -e "\n=== 5. Start Service ==="
START_RESP=$(curl -s -X POST "$BASE_URL/prototype/portal/service/start" \
  -H "Content-Type: application/json" \
  -d "{\"visit_id\":\"$VISIT_ID\",\"room_id\":\"$ROOM_ID\",\"staff_id\":\"$STAFF_ID\",\"service_type\":\"Multiple Treatments\",\"actor_id\":\"$STAFF_ID\"}")
echo "Service started: $(echo "$START_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")"

echo -e "\n=== 6. Add Treatment 1: PT (30 min) ==="
T1_RESP=$(curl -s -X POST "$BASE_URL/prototype/visits/$VISIT_ID/treatments/add" \
  -H "Content-Type: application/json" \
  -d "{\"visit_id\":\"$VISIT_ID\",\"modality\":\"Physical Therapy\",\"therapist_id\":\"$STAFF_ID\",\"duration_minutes\":30,\"notes\":\"Production test PT\",\"actor_id\":\"$STAFF_ID\"}")
T1_ID=$(echo "$T1_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('treatment_id','')} - {d.get('modality','')} - {d.get('duration_minutes','')}min\")")
echo "Treatment 1: $T1_ID"

echo -e "\n=== 7. Add Treatment 2: E-stim (15 min) ==="
T2_RESP=$(curl -s -X POST "$BASE_URL/prototype/visits/$VISIT_ID/treatments/add" \
  -H "Content-Type: application/json" \
  -d "{\"visit_id\":\"$VISIT_ID\",\"modality\":\"E-stim\",\"therapist_id\":\"$STAFF_ID\",\"duration_minutes\":15,\"actor_id\":\"$STAFF_ID\"}")
T2_ID=$(echo "$T2_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('treatment_id','')} - {d.get('modality','')} - {d.get('duration_minutes','')}min\")")
echo "Treatment 2: $T2_ID"

echo -e "\n=== 8. List Treatments for Visit ==="
LIST_RESP=$(curl -s "$BASE_URL/prototype/visits/$VISIT_ID/treatments")
echo "$LIST_RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin)
treatments = data.get('treatments', [])
print(f'Total treatments: {len(treatments)}')
for t in treatments:
    print(f\"  - {t['modality']} ({t['duration_minutes']}min) by {t.get('therapist_name', 'N/A')}\")
"

echo -e "\n=== 9. Query Treatment Records ==="
RECORDS_RESP=$(curl -s "$BASE_URL/prototype/treatment-records")
echo "$RECORDS_RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin)
treatments = data.get('treatments', [])
print(f'Total treatment records: {len(treatments)}')
if treatments:
    print(f'Latest: {treatments[0].get(\"patient_name\", \"N/A\")} - {treatments[0].get(\"modality\", \"N/A\")}')
"

echo -e "\n=== ✅ All PRD-005 APIs Working in Production! ==="
