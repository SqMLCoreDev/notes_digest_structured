# Processed Notes JSON Nested Prompt

"""
Prompt for tiamd_prod_processed_notes_json_nested index - Processed notes with nested JSON structure.
"""

PROCESSED_NOTES_JSON_NESTED_PROMPT = """
**Index: tiamd_prod_processed_notes_json_nested**

Represents: Processed clinical notes with nested JSON structure, progress notes with hierarchical 
data organization, clinical documentation with nested objects (e.g., clinical_timeline as object), 
structured extracted fields with both nested and flattened formats.

**IMPORTANT: This index uses nested JSON structures. Some fields are nested objects, while others 
are flattened with underscore notation.**

**Field Categories:**

**Processing & Metadata:**
- "composite_key": "Composite unique identifier"
- "notesProcessedStatus": "Status of note processing"
- "processedDateTime": "Date/time when note was processed"
- "noteId": "Unique note identifier"
- "noteType": "Type of note"

**Patient Demographics (Flattened):**
- "patient_first_Name", "patient_last_Name", "patientName": "Patient name fields"
- "patientmrn": "Patient Medical Record Number (MRN)"
- "patient_demographics_*": "All patient demographic fields"

**Clinical Timeline (Nested Object):**
- "clinical_timeline": "Nested object containing timeline information"
  - "date_of_service": "Date of service"
  - "reason": "Reason for visit/consultation"

**Subjective (Clinical History):**
- "history_of_present_illness": "History of present illness"
- "past_medical_history": "Past medical history"
- "current_medications": "Current medications"
- "allergies": "Allergies information"
- "social_history": "Social history"
- "family_history": "Family history"

**Objective (Clinical Findings):**
- "objective_vital_signs": "Vital signs summary"
- "objective_physical_exam": "Physical examination summary"
- "objective_labs": "Laboratory results summary"
- "objective_imaging": "Imaging results summary"

**Assessment:**
- "assessment": "Clinical assessment/diagnoses"
- "assessment_and_plan": "Assessment and plan combined"

**Plan:**
- "plan": "Treatment plan summary"
- "medication_changes": "Medication changes"
- "disposition": "Disposition information"

**When to use this index:**
Choose **tiamd_prod_processed_notes_json_nested** when the question involves:
- Processed clinical notes with nested JSON structure
- Progress notes with nested objects
- Clinical documentation queries using nested field access
- Clinical timeline as nested object structure
- Questions requiring access to nested JSON structures
- When you need to query nested objects (e.g., clinical_timeline.reason)
"""
