# Processed Notes Prompt

"""
Prompt for tiamd_prod_processed_notes index - Processed clinical notes with SOAP structure.
"""

PROCESSED_NOTES_PROMPT = """
**Index: tiamd_prod_processed_notes**

Represents: Processed clinical notes and documentation, SOAP notes (Subjective, Objective, Assessment, Plan), 
progress notes, clinical documentation with structured JSON and formatted text, patient clinical narratives, 
medication lists, diagnostic results, treatment plans, and clinical assessments.

**This index contains PROCESSED/STRUCTURED clinical notes - organized and parsed for easy data extraction.**
**IMPORTANT: When presenting this data to users, refer to it as "Processed Data" or "Structured Data", NOT by the index name.**

**Field Mapping:**
- "composite_key": "Composite unique identifier for the note"
- "soapnotesJson": "Structured JSON containing SOAP note components (subjective, objective, assessment, plan)"
- "notesProcessedJson": "Processed structured JSON with extracted clinical information"
- "notesProcessedStatus": "Status of note processing (e.g., 'note submitted')"
- "notesProcessedText": "HTML formatted processed note text"
- "processingIssues": "Issues encountered during note processing"
- "dischargeDate": "Patient discharge date"
- "processedDateTime": "Date and time when note was processed"
- "patient_first_Name": "Patient first name"
- "patientmrn": "Patient Medical Record Number (MRN)"
- "ingestionDateTime": "Date and time when note was ingested"
- "patientName": "Full patient name (Last, First)"
- "admissionDate": "Patient admission date"
- "dateOfServiceEpoch": "Date of service in epoch format"
- "noteId": "Unique note identifier"
- "patient_last_Name": "Patient last name"
- "submitDateTime": "Date and time when note was submitted"
- "noteType": "Type of note (e.g., 'progress_note')"
- "location": "Patient location/facility address"
- "dateOfService": "Date of service for the note"
- "soapnotesText": "Formatted SOAP note text content"

**SOAP Note Structure (in JSON fields):**
- Subjective: Chief complaint, history of present illness, past medical history, medications, allergies
- Objective: Vital signs, physical examination, laboratory results, imaging results
- Assessment: Primary diagnosis, secondary diagnoses, clinical impression
- Plan: Treatment recommendations, follow-up, referrals

**When to use this index:**
Choose **tiamd_prod_processed_notes** when the question involves:
- Processed clinical notes with structured SOAP format
- Progress notes with JSON-formatted data
- Clinical documentation queries
- Patient demographics from processed notes
- SOAP note components
- Clinical timeline and events
"""
