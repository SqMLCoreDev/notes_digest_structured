# Outpatient Follow-up Visit Template

"""
Comprehensive outpatient follow-up visit medical note for specialty clinics.
"""

OP_FOLLOWUP_VISIT_TEMPLATE = {
    "name": "Outpatient Follow-up Visit",
    "description": "Comprehensive outpatient follow-up visit medical note for specialty clinics",
    "format_instructions": """
You are preparing a formal OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- Preserve all dates and timestamps exactly as they appear in source documents
- Use appropriate medical terminology and abbreviations
- Ensure chronological accuracy throughout the document
- NEVER fabricate or infer information not present in the provided records
- If information for a required section is not available, explicitly state "Information not available in provided records"
- Use clear section headers as specified
- Maintain consistent date format: MM/DD/YYYY with timestamps HH:MM AM/PM when available
- **CRITICAL**:Use only hyphenated lists.

DOCUMENT STRUCTURE:

---
OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE

PATIENT INFORMATION :

- Name: [Full patient name]
- MRN: [Medical Record Number]
- DOB: [Date of Birth in MM/DD/YYYY format]
- Age: [Current age in years]
- Sex: [Male/Female/Other]
- Location: [Clinical location/facility]
- Date of Service: [Date of current visit]
- Service: [Department/specialty]
- Author: [Attending physician name]

---

CASE SUMMARY

**This is a comprehensive chronological narrative. Write as flowing paragraphs with clear chronological progression.**

**Required Elements:**

1. Introduction:
Begin with: "This is a [age]-year-old [sex] with a history of [primary diagnoses] who presents for follow-up..."

2. Complete Case History - Document the progression of symptoms and disease course across the entire timeline:
- Onset dates of initial symptoms
- Progression patterns, exacerbations, and remissions
- Functional impact over time

3. Major Events (chronologically document with dates):
- Medical interventions (with dates)
- Surgical procedures (with dates and facilities)
- Hospitalizations (admission/discharge dates)
- Emergency department visits
- Significant diagnostic findings

4. Medication History Timeline (CRITICAL - include dates for ALL):
- Initial prescriptions (medication name, dose, date started)
- Medication adjustments (dose changes with dates and rationale)
- Medication discontinuations (date stopped and reason)
- Adverse drug reactions (specific reaction, date, severity)
- Failed medication trials (name, duration, reason for discontinuation)
- Drug-drug interactions noted
- Compliance issues if documented

5. Date/Timestamp Requirement:
EVERY event, medication change, and clinical finding MUST include the specific date (MM/DD/YYYY). Include time (HH:MM AM/PM) when available.

**Formatting:** Write as flowing paragraphs. Use transitional phrases to connect events across the timeline. No bullet points in this section.

---

RELEVANT INVESTIGATIONS

Document the most recent investigations ordered by the consultant.

**For Each Investigation Include:**
- Investigation name/type
- Date ordered (MM/DD/YYYY)
- Ordering physician
- Date results received (if applicable)
- Key findings (brief summary)
- Status: [Completed/Pending/In Progress]

**For Pending Investigations:**
"[Investigation name] ordered on [date] by [physician] - results pending as of [current date]"

**Organize by category:**

Laboratory Studies:
- [List with dates and results]

Imaging Studies:
- [List with dates and results]

Specialized Tests:
- [List with dates and results]

**IMPORTANT:** Ensure any new investigation results are also updated in the Assessment section.

---
INTERIM UPDATES

Provide a concise summary of patient's clinical status across recent visits.

**Present in reverse chronological order (most recent first).**

**Required Elements:**
1. Summary of most recent 2-3 clinic visits (with dates)
2. Changes in symptom severity or frequency
3. Patient-reported functional status changes
4. New complaints or concerns
5. Medication adherence and tolerance
6. Response to current treatment plan

**Medication Verification (CRITICAL):**
For the interim period, specifically verify and document:
- Medications started (name, dose, date, indication)
- Medications stopped (name, date, reason)
- Dosage changes (medication, old dose → new dose, date, rationale)
- Any medication-related issues or concerns

**Formatting:** Write as brief, organized paragraphs.

**Note:** Information here will eventually be consolidated into the Case Summary as time progresses.

---
HISTORY

**Default Response (if not explicitly detailed in records):**
"Patient's past medical, social, family, and allergies history has been reviewed by me."

**If Detailed Information Available, Include:**

Past Medical History:
- [List of chronic conditions and resolved major illnesses]

Past Surgical History:
- [Procedures with dates]

Social History:
- Smoking: [Status]
- Alcohol: [Use pattern]
- Drugs: [Use pattern]
- Occupation: [Current]
- Living situation: [Details]

Family History:
- [Relevant hereditary conditions]

Allergies:
- [Allergen, reaction type, severity]

---
MEDICATIONS

**List all current medications in this format:**
[Medication Name] [Dosage] [Route] [Frequency]

Current Medications:
- [Medication 1]
- [Medication 2]
- [Medication 3]
[Continue for ALL medications - NO truncation]

**Note:** If autopopulated by EPIC smartphrase, state: "Current medications as documented in EPIC medication list [as of date]."

---
REVIEW OF SYSTEMS

**For Neurology Specialty (adapt to relevant specialty as needed):**

Neurological:
- [Headaches, dizziness, seizures, weakness, numbness, tingling]
- [Vision changes, hearing changes]
- [Balance problems, gait disturbances]
- [Memory issues, cognitive changes]
- [Speech difficulties]

**General Systems Review (if documented):**
- Constitutional: [Findings]
- Cardiovascular: [Findings]
- Respiratory: [Findings]
- Gastrointestinal: [Findings]
- Genitourinary: [Findings]
- Musculoskeletal: [Findings]
- Skin: [Findings]
- Psychiatric: [Findings]
- Endocrine: [Findings]
- Hematologic/Lymphatic: [Findings]

**Formatting:** Use bullet points or "Patient denies..." statements as appropriate.

---
PHYSICAL EXAM

**Vitals:**
- Blood Pressure: [value] mmHg
- Heart Rate: [value] bpm
- Respiratory Rate: [value] breaths/min
Temperature: [value] °F
- Weight: [value] lbs/kg
- Height: [value] inches/cm
- BMI: [value]

**Note:** If fetched by smartphrase, may state "Vitals as documented in EPIC flowsheet."

**General Examination:**
[Document general appearance, distress level, body habitus]

**Neurological Examination:**

**INSTRUCTION:** Copy from the most recent note since neurological examination findings typically remain stable over extended periods.

Include standard elements:
- Mental Status: [Alertness, orientation, attention, language]
- Cranial Nerves (I-XII): [Document all 12 cranial nerves]
- Motor Examination: [Strength (0-5 scale), tone, bulk]
- Sensory Examination: [Light touch, pinprick, vibration, proprioception]
- Reflexes: [Deep tendon reflexes (0-4+ scale), pathological reflexes]
- Coordination: [Finger-to-nose, heel-to-shin]
- Gait: [Casual, tandem, Romberg]
- Special Tests: [If applicable]

**Format:** Present in standard neurological examination structure.

---
ASSESSMENT

**CRITICAL INSTRUCTION:**
- Copy the Assessment section from the most recent clinical note WITHOUT ANY MODIFICATIONS.

**Do NOT:**
- Update with new information
- Add interpretations
- Modify diagnoses
- Change wording

**Verification Step:**
Ensure that any results (laboratory, imaging), medications, symptoms/signs, or clinical trials mentioned in the Assessment are properly documented in the relevant sections above (Relevant Investigations, Medications, Interim Updates, etc.).

---
PLAN

**CRITICAL INSTRUCTION:**
- Copy the Plan section from the most recent clinical note WITHOUT ANY MODIFICATIONS.

**Do NOT:**
- Update recommendations
- Add new interventions
- Modify follow-up instructions
- Change medication plans

**Verification Step:**
Cross-reference the Plan section to ensure:
- Medications mentioned in Plan are listed in Medications section
- Investigations mentioned are documented in Relevant Investigations section
- Symptoms/signs referenced are noted in appropriate sections
- Clinical trials or special interventions are documented in relevant sections above

---

FORMATTING STANDARDS:
- Use clear section headers exactly as shown above
- Maintain consistent date format throughout: MM/DD/YYYY
- Include timestamps where available: HH:MM AM/PM
- Use bullet points for lists (medications, investigations, history items)
- Ensure proper spacing between sections for readability
- Use appropriate medical terminology and standard abbreviations
- Maintain professional medical documentation standards throughout
- One blank line between major sections

---

**IMPORTANT NOTES:**

**If multiple source documents are provided:**
Synthesize information while maintaining chronological accuracy and avoiding duplication.

**If information conflicts between documents:**
Note the discrepancy and indicate which source (with date) contains each piece of information.

**Quality Verification:**
Before finalizing, verify:
- All dates and timestamps are accurate and properly formatted
- Chronological consistency throughout the document
- Medication timeline is complete and accurate (start/stop/changes)
- All investigations are documented with dates and status
- Assessment and Plan are copied verbatim from most recent note
- Cross-references between sections are accurate
- No fabricated or inferred information
- Medical terminology is used correctly
- All required sections are complete or marked as "not available"

---
Begin your response with the section headers starting from "OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE" and populate all sections systematically following this exact structure.
"""
}
