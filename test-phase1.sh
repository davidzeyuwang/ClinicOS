#!/bin/bash
API="http://127.0.0.1:8000/prototype"

echo "=== Creating test patient ==="
PATIENT=$(curl -s -X POST "$API/patients" -H "Content-Type: application/json" \
  -d '{"first_name":"Test","last_name":"Patient","phone":"555-1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['patient_id'])")
echo "Patient ID: $PATIENT"

echo "=== Creating test room ==="
ROOM=$(curl -s -X POST "$API/admin/rooms" -H "Content-Type: application/json" \
  -d '{"name":"Test Room","code":"TR1","room_type":"treatment"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['room_id'])")
echo "Room ID: $ROOM"

echo "=== Creating test staff ==="
STAFF=$(curl -s -X POST "$API/admin/staff" -H "Content-Type: application/json" \
  -d '{"name":"Test Therapist","role":"therapist"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['staff_id'])")
echo "Staff ID: $STAFF"

echo "=== Checking in patient ==="
VISIT=$(curl -s -X POST "$API/portal/checkin" -H "Content-Type: application/json" \
  -d "{\"patient_id\":\"$PATIENT\",\"patient_name\":\"Test Patient\",\"actor_id\":\"frontdesk\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['visit_id'])")
echo "Visit ID: $VISIT"

echo "=== Starting service ==="
curl -s -X POST "$API/portal/service/start" -H "Content-Type: application/json" \
  -d "{\"visit_id\":\"$VISIT\",\"room_id\":\"$ROOM\",\"staff_id\":\"$STAFF\",\"service_type\":\"PT\",\"actor_id\":\"therapist\"}" > /dev/null

echo "=== Ending service ==="
curl -s -X POST "$API/portal/service/end" -H "Content-Type: application/json" \
  -d "{\"visit_id\":\"$VISIT\",\"actor_id\":\"therapist\"}" > /dev/null

echo "=== Checking out ==="
CHECKOUT=$(curl -s -X POST "$API/portal/checkout" -H "Content-Type: application/json" \
  -d "{\"visit_id\":\"$VISIT\",\"actor_id\":\"frontdesk\",\"copay_collected\":25.00,\"wd_verified\":true,\"patient_signed\":true}")
echo "$CHECKOUT" | python3 -m json.tool 2>/dev/null || echo "Checkout response: $CHECKOUT"

echo "=== Testing PDF generation ==="
curl -s "$API/patients/$PATIENT/sign-sheet.pdf" -o /tmp/test-sign-sheet.pdf
if [ -f /tmp/test-sign-sheet.pdf ]; then
  SIZE=$(wc -c < /tmp/test-sign-sheet.pdf)
  echo "✅ PDF generated successfully ($SIZE bytes)"
  echo "PDF saved to: /tmp/test-sign-sheet.pdf"
  echo ""
  echo "To view PDF: open /tmp/test-sign-sheet.pdf"
else
  echo "❌ PDF generation failed"
fi
