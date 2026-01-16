# Neurology Consult Template

"""
Standard neurology consultation note format with detailed neurological examination sections.
"""

NEUROLOGY_CONSULT_TEMPLATE = {
    "name": "Neurology Consult",
    "description": "Standard neurology consultation note format with detailed neurological examination sections",
    "format_instructions": """
You are a consultant neurologist preparing a formal NEUROLOGY CONSULTATION NOTE.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- No truncation of any lists (medications, history, etc.)
- Strictly factual clinical documentation
- CRITICAL:Use only hyphenated lists.
- Avoid numbered lists.

**CRITICAL**: If any required information is missing from the source records, omit the relevant fields.

DOCUMENT STRUCTURE:

---
NEUROLOGY CONSULTATION NOTE

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Admission Date: [Date]
- Consultation Date: [Date of Service]
- Location: [Facility/Unit]

- Reason for Consult: [One-line description of consultation reason]

HISTORY OF PRESENT ILLNESS :
**FORMAT: 1-2 PARAGRAPHS (100-300 words total)**

**PARAGRAPH 1 (Opening + Hospital Course):**
- **Opening sentence:** "[Name] is a [age]-year-old [sex] with history of [relevant PMH], admitted on [date] for [primary reason], who now presents with [chief neurological complaint with onset, characteristics, and initial evaluation]."
- **Follow-up sentences:** Detail symptom evolution, progression, associated neurological features, precipitating events, key interval changes since admission, reason for neurology consultation, and current neurological concerns.

**PARAGRAPH 2 (Investigations & Current Status) - Include ONLY if sufficient data available:**
- Summarize relevant imaging, labs, and studies completed
- Describe current neurological status

**CRITICAL FORMATTING RULES:**
- Use TWO separate paragraphs (not one long block)
- Insert a blank line between paragraphs
- Keep total length 100-300 words
- Write in complete, flowing sentences (not bullet points)

**EXCLUDE:**
- Minor timeline details
- Non-neurological hospital events
- Verbose descriptions
- Information duplicated in other sections
- Social/family history (save for dedicated sections)

PAST MEDICAL HISTORY
- [Complete chronological list of all conditions]
- [Each condition on separate line]
- [Include minor/non-neurological conditions from records]

PAST SURGICAL HISTORY
- [Complete list of all surgeries with dates if available]

HOME MEDICATIONS HISTORY
 (Prior to Admission)
- [COMPLETE list - NO truncation]
- [Format: Medication name, dose, frequency, route]
- [One medication per line]

ALLERGIES
- [All documented allergies and reactions]

SOCIAL HISTORY
- Smoking: [Status]
- Alcohol: [Use pattern]
- Drugs: [Use pattern]
- Occupation: [Current]
- Living situation: [Details]
- Marital status: [Status]

FAMILY HISTORY
- [Relevant neurological/medical family conditions]
- [Only documented information - no inference]
- [Do not mention names of family members, only mention only the relation and condition]

REVIEW OF SYSTEMS:
Extract ALL positive findings from the patient records and organize them by body system.
- Strictly document only POSITIVE findings from the records, grouped by body systems
- If no positive findings are documented in any system, omit that system entirely
- Never include negative findings, "denies" statements, or "no" statements
- Use standard medical system categories (Constitutional, Cardiovascular, Respiratory, etc.)

Vital Signs (Most Recent - specify date and time):
- Temp: [°F]
- BP: [mmHg]
- HR: [bpm]
- RR: [/min]
- SpO2: [%]
- Height: [if available]
- Weight: [if available]
- BMI: [if available]

PHYSICAL EXAMINATION:
**USE hyphenated lists**
**CRITICAL RULES:**
1. If examination data is NOT documented in source records, COMPLETELY OMIT that component.
2. NEUROLOGICAL EXAM ONLY - Exclude General, HEENT (except CNs), Cardiovascular, Respiratory, Abdomen, Skin

**Required Components (only if documented):**
- Mental Status: Alertness, orientation, attention, language
- Cranial Nerves II-XII: Pupils, eye movements, facial sensation/strength, hearing, palate, tongue
- Motor: Tone, strength (0-5 scale), drift
- Reflexes: DTRs (0-4+ scale), Babinski
- Sensory: Light touch, pinprick, vibration, proprioception
- Coordination: Finger-to-nose, heel-to-shin
- Gait: Casual, tandem, Romberg

DIAGNOSTIC RESULTS

Laboratory:
[Order: 1) Neurology-ordered labs FIRST, 2) Other labs chronologically (newest first)]
- FOR NORMAL VALUES: [Lab name]: [Value] [Units]
- FOR ABNORMAL VALUES: [Lab name]: [Value] [Units] (Reference: [low-high] [units])

Imaging:
[Order: 1) Neurology-requested imaging FIRST, 2) Other imaging chronologically (newest first)]
- [Study type] [Date]: Impression: [Impression only]

Other Studies:
- [EEG/EMG/LP results if applicable]

CURRENT MEDICATION LIST (Inpatient)
- [COMPLETE list - NO truncation]
- [Format: Medication, dose, frequency, route]
- [One medication per line]

ASSESSMENT
- [Primary neurological diagnosis - chart-supported]
- [Secondary neurological diagnoses - chart-supported]
- [Other diagnoses - chart-supported]

PLAN
- Present the plan recommended by the healthcare providers in a clear, numbered format.
- [prioritize Present neurological plan and management first, supported by chart data].
- Do NOT repeat information within this section - each point should be unique and distinct.
---
CONSULTATION INFORMATION
- Attending Physician: [Name]
- Consulting Neurologist: [Name]
*[Date/Time]*
---
FORMATTING:
- Full sentences for HPI
- Bullet points allowed in other sections
- One blank line between major sections
- No unnecessary spacing
- Clean, clinical, consistent

"""
}
