# Clinical Notes Prompt (Non-Production)

"""
Prompt for tiamd_clinical_notes index - Raw/Original clinical notes.
"""

CLINICAL_NOTES_PROMPT = """
**Index: tiamd_clinical_notes**

Represents: Clinical consultation notes, specialist consultations, consultation documentation with 
structured JSON and formatted text, consultation findings, specialist recommendations.

**This index contains RAW/ORIGINAL clinical notes - unprocessed clinical documentation as entered by clinicians.**
**IMPORTANT: When presenting this data to users, refer to it as "Raw Data" or "Original Documentation", NOT by the index name.**

**Field Mapping:**
- "dateOfService": "Date of service for the consultation (format: MM-DD-YYYY)"
- "ingestionDate": "Date when note was ingested (epoch_millis format)"
- "ingestionDateTime": "Date and time when note was ingested"
- "locationname": "Location name"
- "noteId": "Unique note identifier"
- "noteType": "Type of note (e.g., 'consultation_note')"
- "notesReprocessedStatus": "Status of note reprocessing"
- "patientID": "Patient ID/Patient name"
- "patientMRN": "Patient Medical Record Number"
- "rawdata": "Raw clinical note data (text)"
- "reprocessed_date": "Date when note was reprocessed"
- "serviceDate": "Service date"
- "status": "Note status"

**Important Notes:**
- Clinical content (SOAP notes, consultation findings) is stored in the "rawdata" text field
- Multiple variations of patient name and MRN fields exist
- Date fields are available in multiple formats

**When to use this index:**
Choose **tiamd_clinical_notes** when the question involves:
- RAW/ORIGINAL clinical notes (user selected "Raw" or wants unprocessed data)
- Consultation notes, specialist consultations
- Clinical note documentation and raw clinical data
- Patient identifiers (MRN, patient names)
- Note metadata (note ID, note type, status)
- Service dates and consultation dates
- Location/facility information
- Raw clinical documentation content
"""
