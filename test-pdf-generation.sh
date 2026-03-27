#!/bin/bash
# Quick test: Generate a patient with visits and download PDF

echo "🧪 Testing PDF Generation (WHO/WHAT/WHEN/WHERE)"
echo ""

API="http://localhost:8000/prototype"

# 1. Create room
echo "1️⃣  Creating room..."
ROOM=$(curl -s -X POST "$API/admin/rooms" -H "Content-Type: application/json" \
  -d '{"name":"Treatment Room 201","code":"R201","room_type":"treatment"}')
ROOM_ID=$(echo $ROOM | grep -o '"room_id":"[^"]*"' | cut -d'"' -f4)
echo "   ✓ Room created: $ROOM_ID"

# 2. Create staff
echo "2️⃣  Creating staff..."
STAFF=$(curl -s -X POST "$API/admin/staff" -H "Content-Type: application/json" \
  -d '{"name":"Dr. Sarah Chen","role":"therapist","license_id":"PT-12345"}')
STAFF_ID=$(echo $STAFF | grep -o '"staff_id":"[^"]*"' | cut -d'"' -f4)
echo "   ✓ Staff created: Dr. Sarah Chen ($STAFF_ID)"

# 3. Create patient
echo "3️⃣  Creating patient..."
PATIENT=$(curl -s -X POST "$API/patients" -H "Content-Type: application/json" \
  -d '{"first_name":"John","last_name":"Doe","date_of_birth":"1980-05-15","phone":"555-1234","mrn":"MRN-TEST-001"}')
PATIENT_ID=$(echo $PATIENT | grep -o '"patient_id":"[^"]*"' | cut -d'"' -f4)
echo "   ✓ Patient created: John Doe ($PATIENT_ID)"

# 4. Add insurance
echo "4️⃣  Adding insurance..."
curl -s -X POST "$API/insurance" -H "Content-Type: application/json" \
  -d "{\"patient_id\":\"$PATIENT_ID\",\"carrier_name\":\"Blue Shield PPO\",\"member_id\":\"BS123456\",\"group_number\":\"GRP-789\",\"copay_amount\":30.0,\"visits_authorized\":24,\"plan_type\":\"PPO\"}" > /dev/null
echo "   ✓ Insurance added"

# 5. Create 3 visits
for i in 1 2 3; do
  echo "5️⃣  Creating visit $i..."
  
  # Checkin
  VISIT=$(curl -s -X POST "$API/portal/checkin" -H "Content-Type: application/json" \
    -d "{\"patient_ref\":\"MRN-TEST-001\",\"patient_name\":\"John Doe\",\"patient_id\":\"$PATIENT_ID\",\"actor_id\":\"front-desk\"}")
  VISIT_ID=$(echo $VISIT | grep -o '"visit_id":"[^"]*"' | cut -d'"' -f4)
  
  # Start service (establishes WHO/WHAT/WHERE)
  curl -s -X POST "$API/portal/service/start" -H "Content-Type: application/json" \
    -d "{\"visit_id\":\"$VISIT_ID\",\"service_type\":\"PT\",\"staff_id\":\"$STAFF_ID\",\"room_id\":\"$ROOM_ID\",\"actor_id\":\"$STAFF_ID\"}" > /dev/null
  
  # End service
  curl -s -X POST "$API/portal/service/end" -H "Content-Type: application/json" \
    -d "{\"visit_id\":\"$VISIT_ID\",\"actor_id\":\"$STAFF_ID\"}" > /dev/null
  
  # Checkout
  curl -s -X POST "$API/portal/checkout" -H "Content-Type: application/json" \
    -d "{\"visit_id\":\"$VISIT_ID\",\"actor_id\":\"front-desk\",\"payment_status\":\"copay_collected\",\"payment_method\":\"card\",\"payment_amount\":30.0,\"copay_collected\":30.0,\"wd_verified\":true,\"patient_signed\":true}" > /dev/null
  
  echo "   ✓ Visit $i completed (PT with Dr. Sarah Chen in R201)"
done

echo ""
echo "✅ TEST DATA CREATED!"
echo ""
echo "📄 NOW OPEN THE UI AND TEST:"
echo "   1. Go to: http://localhost:8000/ui/index.html"
echo "   2. Click 'Patients' tab"
echo "   3. Click 'John Doe'"
echo "   4. Click '📄 Download Sign Sheet PDF' button"
echo ""
echo "🔗 Direct PDF download:"
echo "   curl http://localhost:8000/prototype/patients/$PATIENT_ID/sign-sheet.pdf -o test-sign-sheet.pdf"
echo "   open test-sign-sheet.pdf"
echo ""
