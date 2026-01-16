# Non-Prod Processed Notes Prompt

"""
Prompt for tiamd_processed_notes index - Processed notes (non-production).
"""

PROCESSED_NOTES_NONPROD_PROMPT = """
**Index: tiamd_processed_notes**

Represents: Processed clinical notes and documentation, SOAP notes (Subjective, Objective, Assessment, Plan), 
progress notes, clinical documentation with structured JSON and formatted text.

**This index contains PROCESSED/STRUCTURED clinical notes - organized and parsed for easy data extraction.**
**IMPORTANT: When presenting this data to users, refer to it as "Processed Data" or "Structured Data", NOT by the index name.**

**Field Mapping:**
- "composite_key": "Composite unique identifier for the note"
- "soapnotesJson": "Structured JSON containing SOAP note components"
- "notesProcessedJson": "Processed structured JSON with extracted clinical information"
- "notesProcessedStatus": "Status of note processing"
- "notesProcessedText": "HTML formatted processed note text"
- "dischargeDate": "Patient discharge date"
- "processedDateTime": "Date and time when note was processed"
- "patientmrn": "Patient Medical Record Number (MRN)"
- "ingestionDateTime": "Date and time when note was ingested"
- "patientName": "Full patient name (Last, First)"
- "admissionDate": "Patient admission date"
- "noteId": "Unique note identifier"
- "noteType": "Type of note"
- "location": "Patient location/facility address"
- "dateOfService": "Date of service for the note"
- "soapnotesText": "Formatted SOAP note text content"

**When to use this index:**
Choose **tiamd_processed_notes** when the question involves:
- PROCESSED/STRUCTURED data
- Clinical notes, progress notes, SOAP notes
- Patient clinical narratives
- Physical examination findings, vital signs
- Laboratory results, diagnostic test results
- Clinical assessments, diagnoses
- Treatment plans, medication lists
"""
