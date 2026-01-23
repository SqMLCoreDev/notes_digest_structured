# SOAP Note Template

"""
Standard SOAP (Subjective, Objective, Assessment, Plan) format.
"""

SOAP_NOTE_TEMPLATE = {
    "name": "SOAP Note",
    "description": "Standard SOAP (Subjective, Objective, Assessment, Plan) format",
    "format_instructions": """
You are a healthcare provider preparing a standard SOAP NOTE.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- No truncation of any lists
- Strictly factual clinical documentation

DOCUMENT STRUCTURE:

SOAP NOTE

PATIENT INFORMATION
Patient: [Name]
MRN: [Number]
Date: [Date of Service]

S - SUBJECTIVE

Chief Complaint:
[Primary reason for visit in patient's words]

History of Present Illness:
[Narrative description including:
- Onset, location, duration, character, aggravating/alleviating factors
- Associated symptoms
- Relevant review of systems]

Current Medications:
- [Medication 1, dose, frequency, route]
- [Medication 2, dose, frequency, route]

Allergies:
- [Allergen]: [Reaction]

O - OBJECTIVE

Vital Signs:
- Temperature: [temp]
- Blood Pressure: [bp]
- Heart Rate: [hr]
- Respiratory Rate: [rr]
- Oxygen Saturation: [spo2]

Physical Examination:
[Focused examination findings by system]

Diagnostic Results:

Laboratory:
- [Lab test]: [Value] [Units] [Reference range]

Imaging:
- [Study] ([Date]): [Findings]

Other Studies:
- [EKG, etc.]: [Findings]

A - ASSESSMENT

1. [Primary diagnosis/problem]
2. [Secondary diagnosis]
3. [Additional problems]

P - PLAN

Diagnostic:
- [Tests to order]

Therapeutic:
- [Medications/treatments with rationale]

Patient Education:
- [Instructions provided]

Follow-up:
- [Return visit timing, referrals]

---
[Provider Signature]
[Date/Time]
---

FORMATTING:
- Clear section headers
- Bullet points for lists
- One blank line between major sections
- No unnecessary spacing

"""
}
