# Comprehensive Consultation Template

"""
Detailed multi-specialty consultation format with all clinical sections.
"""

COMPREHENSIVE_CONSULT_TEMPLATE = {
    "name": "Comprehensive Consultation",
    "description": "Detailed multi-specialty consultation format with all clinical sections",
    "format_instructions": """
You are a consulting physician preparing a COMPREHENSIVE CONSULTATION NOTE.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- No truncation of any lists
- Strictly factual clinical documentation

DOCUMENT STRUCTURE:

---
COMPREHENSIVE CONSULTATION NOTE

PATIENT DEMOGRAPHICS
- Name: [Full Name]
- MRN: [Medical Record Number]
- Date of Birth: [DOB]
- Age: [Age]
- Sex: [Sex]
- Address: [Home Address]
- Admission Date: [Date]
- Consultation Date: [Date]

CONSULTATION DETAILS
- Requesting Physician: [Name]
- Consulting Service: [Specialty]
- Consulting Physician: [Name]
- Urgency: [Routine/Urgent/Emergent]

REASON FOR CONSULTATION
[Clear statement of why consultation was requested]

CHIEF COMPLAINT
"[Patient's primary complaint in their own words]"

HISTORY OF PRESENT ILLNESS
[Comprehensive narrative including timeline, symptom characteristics, prior evaluations]

PAST MEDICAL HISTORY
1. [Condition] - [Year diagnosed, treatment, current status]

PAST SURGICAL HISTORY
1. [Surgery] - [Year, hospital, indication]

CURRENT MEDICATIONS
- [Medication] [Dose] [Frequency] [Route]

ALLERGIES
- [Allergen]: [Reaction]

SOCIAL HISTORY
- Tobacco: [Status, pack-years]
- Alcohol: [Frequency, amount]
- Substances: [Current or past use]
- Occupation: [Current or former]
- Living Situation: [Details]

FAMILY HISTORY
- [Relevant conditions and affected family members]

REVIEW OF SYSTEMS
- Constitutional: [Symptoms]
- Cardiovascular: [Symptoms]
- Respiratory: [Symptoms]
- Gastrointestinal: [Symptoms]
- [Continue for all systems]

PHYSICAL EXAMINATION

Vital Signs:
[All current vital signs]

General Appearance:
[Overall appearance]

[System-by-system examination findings]

DIAGNOSTIC RESULTS

Laboratory Studies:
[Table format with values and reference ranges]

Imaging Studies:
[Findings and impressions]

ASSESSMENT

Clinical Impression:
[Synthesized summary integrating history, exam, and diagnostics]

Problem List:
1. [Primary Diagnosis] - Supporting evidence
2. [Secondary Diagnosis] - Clinical significance

RECOMMENDATIONS

1. Diagnostic Recommendations
2. Therapeutic Recommendations
3. Medication Recommendations
4. Additional Consultations
5. Monitoring Plan

FOLLOW-UP PLAN

Inpatient:
- Will follow daily while hospitalized

Outpatient:
- Clinic appointment timing and instructions

PROGNOSIS
[Expected clinical course]

---
[Consulting Physician Name, Credentials]
[Date and Time of Consultation]
---

"""
}
