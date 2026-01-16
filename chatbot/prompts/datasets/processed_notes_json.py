# Processed Notes JSON Prompt

"""
Prompt for tiamd_prod_processed_notes_json index - Processed notes with flattened JSON structure.
"""

PROCESSED_NOTES_JSON_PROMPT = """
**Index: tiamd_prod_processed_notes_json**

Represents: Processed clinical notes with flattened JSON structure, progress notes with categorized 
extracted data, clinical documentation with specific field categories (demographics, subjective, 
objective, assessment, plan).

**This index contains PROCESSED clinical notes with FLATTENED JSON fields for easy querying.**

**Field Categories:**

**Processing & Metadata:**
- "composite_key": "Composite unique identifier"
- "notesProcessedStatus": "Status of note processing"
- "processingIssues": "Issues encountered during processing"
- "processedDateTime": "Date/time when note was processed"
- "noteId": "Unique note identifier"
- "noteType": "Type of note (e.g., 'progress_note')"

**Patient Demographics:**
- "patient_first_Name", "patient_last_Name", "patientName": "Patient name fields"
- "patientmrn": "Patient Medical Record Number (MRN)"
- "patient_demographics_*": "All patient demographic fields"

**Location & Dates:**
- "location": "Facility/location address"
- "admissionDate": "Admission date"
- "dischargeDate": "Discharge date"
- "dateOfService": "Date of service"

**When to use this index:**
Choose **tiamd_prod_processed_notes_json** when the question involves:
- Processed clinical notes with structured/flattened JSON fields
- Progress notes with categorized extracted data
- Clinical documentation queries using specific field categories
- Patient demographics from clinical notes
- Subjective clinical information
- Objective clinical findings
- Clinical assessments and diagnoses
- Treatment plans, medication changes
"""
