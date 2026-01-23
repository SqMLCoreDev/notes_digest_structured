#!/bin/bash

# Test script for validation endpoint

echo "Testing Validation Endpoint..."
echo "================================"
echo ""

curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_note": "Patient is a 45-year-old male presenting with chest pain. Blood pressure 140/90. Prescribed aspirin 81mg daily.",
    "generated_output": "PROGRESS NOTE\n\nPATIENT INFORMATION\n- Name: Patient\n- Age: 45\n- Sex: Male\n\nSUBJECTIVE\nPatient presents with chest pain.\n\nOBJECTIVE\nBlood pressure: 140/90\n\nASSESSMENT\nChest pain, rule out cardiac event\n\nPLAN\nAspirin 81mg daily",
    "note_type": "progress_note",
    "note_id": "test_001",
    "store_to_es": true
  }' | python3 -m json.tool

echo ""
echo "================================"
echo "To check validation history for a note:"
echo "curl http://localhost:8000/validate/test_001"
