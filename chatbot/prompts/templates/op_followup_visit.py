# Outpatient Follow-up Visit Template

"""
Comprehensive outpatient follow-up visit medical note for specialty clinics.
"""

OP_FOLLOWUP_VISIT_TEMPLATE = {
    "name": "Outpatient Follow-up Visit",
    "description": "Comprehensive outpatient follow-up visit medical note for specialty clinics",
    "format_instructions": """
You are preparing a formal OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE.

CRITICAL FIRST STEP: INFORMATION CONSISTENCY ANALYSIS

BEFORE generating the note, you MUST:

Analyze the source document for inconsistencies, particularly in:
- Medications: dosages mentioned in different sections
- Imaging dates and findings: same study referenced with different details
- Surgical dates and procedures: conflicting timelines
- Symptom chronology: events described in different order
- Clinical findings: exam findings vs. history descriptions

Resolve inconsistencies by prioritizing:
- HIGHEST PRIORITY: Information from the Assessment section (most recent clinical synthesis)
- SECOND PRIORITY: Most recent date-stamped information
- THIRD PRIORITY: Most specific/detailed information
- Document conflicts: If irreconcilable, note: "conflicting reports suggest..."

Specific consistency checks:
- Medications: Use ONLY the dosages from "Current Medications" section or latest Assessment mention
- Imaging findings: If same MRI mentioned multiple times, use most complete description
- Dates: If event has multiple dates, use most specific date and note if uncertainty exists
- Exam findings: Use findings from Physical Examination section, not historical mentions
- Attribution: NEVER change who said/did something - preserve exact attribution from source
- Cautious language: Keep hedging phrases like "supportive of," "consistent with," "appears to be" exactly as stated

State in your analysis: "Consistency analysis performed. Resolved [X] discrepancies using Assessment section priority."

CRITICAL RULES FOR DATE HANDLING:
- Use the most recent clinical encounter date from the Assessment section as the authoritative Date of Service
- If there are apparent discrepancies between header dates and encounter dates, prioritize the Assessment section date
- Do NOT include explanatory notes about date discrepancies in the final output
- Simply use the correct date consistently throughout the document

---

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- Preserve all dates and timestamps exactly as they appear in source documents
- Use appropriate medical terminology and abbreviations
- Ensure chronological accuracy throughout the document
- NEVER fabricate or infer information not present in the provided records
- If information for a required section is not available, omit that section entirely
- Use clear section headers as specified
- Maintain consistent date format: MM-DD-YYYY (e.g., "01-16-2025"); MM-YYYY if day unknown; YYYY if only year known
- Always include at least month and year for all events
- Include timestamps HH:MM AM/PM when available
- Use only hyphenated lists where lists are required
- PRESERVE EXACT ATTRIBUTION: Never change who said/did/reported something
- MAINTAIN CAUTIOUS LANGUAGE: Keep hedging phrases ("supportive of," "consistent with," "appears to be") exactly as stated
- KEEP PATIENT VOICE: Maintain "she says," "he reports," "patient feels" as stated in source
- PRESERVE CHARACTER NARRATIVES: Keep attribution phrases like "her surgeon wanted," "she was told," "Dr. X recommended" exactly as in source
- CRITICAL FORMATTING: Do NOT use any asterisks, hashtags, or markdown formatting symbols in the output
- Do NOT use bold, italics, or any text emphasis markers
- Use only plain text with hyphenated lists
- Do NOT use double asterisks, single asterisks, or any emphasis formatting
- Problem names in Assessment should be written in plain text without any formatting
- Do NOT include phrases like "Not documented" or "Information not available" - simply omit sections that lack data

DOCUMENT STRUCTURE:

---
OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE

PATIENT INFORMATION:

- Name: [Full patient name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth in MM-DD-YYYY format]
- Age: [Current age in years]
- Sex: [Male/Female/Other]
- Location: [Clinical location/facility]
- Date of Service: [Date of current visit in MM-DD-YYYY format]
- Service: [Department/specialty]
- Author: [Attending physician name]

REASON FOR VISIT

[Brief statement of visit purpose - typically "follow-up" or specific reason]

CASE SUMMARY

This is a comprehensive chronological narrative. Write as flowing paragraphs with clear chronological progression.

Opening Format:
"[Mr./Ms. Name], a [age] y.o. [male/female], was evaluated at [clinic name] in follow up.

Case summary:
[Begin comprehensive narrative here]"

Required Elements:

Introduction:
- Begin with patient demographics and when you first saw them: "[Gender descriptor] first seen in [year/month] for [primary problem] characterized by [key symptoms]."

Chronological Organization:
- Start with CURRENT presentation and when you first saw the patient
- Backtrack to ORIGINAL inciting event/injury (with date)
- Move forward chronologically through interventions
- Use transitional phrases to connect events across timeline

Complete Case History - Document the progression across entire timeline:
- Initial presentation with specific date (MM-DD-YYYY or MM-YYYY format)
- Inciting event/injury with date and description
- Initial evaluation and findings
- Onset dates of symptoms with progression patterns
- Exacerbations and remissions with dates
- Functional impact over time

Major Events (chronologically document with dates in MM-DD-YYYY format):
- Medical interventions (with dates and outcomes)
- Surgical procedures (with dates, facilities, and surgeons when known)
- Hospitalizations (admission/discharge dates)
- Emergency department visits
- Significant diagnostic findings with dates
- Other treating physicians (names and specialties)

Imaging History Timeline:
- List ALL relevant imaging with dates (MM-DD-YYYY format)
- Include key findings only (concise)
- For serial imaging, compare: "MRI from 01-16-2025 showed... while subsequent imaging in 04-2022 revealed..."
- Note when you haven't seen images yourself: "apparently showed..." or "reportedly demonstrated..."

Medication History Timeline (CRITICAL - include dates for ALL):
- Initial prescriptions (medication name, dose, date started, indication)
- Medication adjustments (dose changes with dates and rationale)
- Document treatment trials: what was tried → outcome (success/failure/partial) → why discontinued
- Adverse drug reactions (specific reaction, date, severity)
- Failed medication trials (name, duration, reason for discontinuation)
- Drug-drug interactions noted
- Compliance issues if documented
- Management chronology showing progression through treatment modalities with results

Attribution and Uncertainty:
- Use "apparently" when relying on patient report of old records
- Use "I believe" or "I suspect" for clinical judgment
- Document conflicting opinions: "Dr. X is saying... Dr. Y is saying..."
- CRITICAL: Preserve exact attribution as stated in source (e.g., "her spine surgeon from Florida wanted to remove hardware")
- MAINTAIN CHARACTER NARRATIVES: Keep "she says," "he feels," "patient reports" exactly as in source
- PRESERVE CAUTIOUS LANGUAGE: Keep "findings are supportive of..." - do not change to "findings support"

Clinical Reasoning:
- Make thought process explicit: "The primary clinical question is..."
- State hypotheses: "which I believe was related to..."
- Document skepticism professionally when appropriate
- Note inconsistencies when present

Patient-Centered Documentation:
- Include direct quotes from patient (in quotation marks) - use sparingly
- Document patient preferences concisely
- Acknowledge patient suffering and psychosocial context briefly
- Note patient's own research/treatment attempts
- Include insurance/compensation complications concisely
- PRESERVE PATIENT'S VOICE: Keep "she says," "he feels," "patient does not feel like" exactly as stated

Date Format Requirement:
- EVERY event, medication change, and clinical finding MUST include specific date
- Full date when available: MM-DD-YYYY (e.g., "01-16-2025")
- Month and year if day unknown: MM-YYYY (e.g., "01-2025")
- Year only if more specific date unavailable: YYYY (e.g., "2025")
- Include time when available: HH:MM AM/PM

Formatting: 
- Write as flowing paragraphs (4-7 sentences per paragraph)
- No bullet points in this section
- Use transitional phrases
- Moderate paragraph length for readability
- Professional but empathetic tone
- Non-judgmental even when documenting non-compliance
- Medically precise with proper anatomic terms
- Efficient sentences without excessive wordiness

RELEVANT INVESTIGATIONS

Document the most recent investigations ordered by the consultant.

For Each Investigation Include:
- Investigation name/type
- Date ordered (MM-DD-YYYY format)
- Ordering physician
- Date results received (if applicable)
- Key findings (brief summary)

For Pending Investigations:
"[Investigation name] ordered on [MM-DD-YYYY] by [physician] - results pending as of [current date]"

Organize by category:

Laboratory Studies:
- [Date]: [Time if available]
  - [Lab test 1]: [Value] [Units] [Reference range if abnormal]
  - [Lab test 2]: [Value] [Units] [Reference range if abnormal]
  - [Continue for all labs from this date]

CRITICAL: Present each lab test as a separate hyphenated item under the date header.

Imaging Studies:
- [Imaging type] ([MM-DD-YYYY]): [Key findings or "No abnormality detected"]

CRITICAL: Do NOT include "Status: Completed" or "Status: Active" or similar status indicators. Either present the stated impressions/findings or state "No abnormality detected" if applicable.

Specialized Tests:
- [Test name] ([MM-DD-YYYY]): [Key findings or results]

IMPORTANT: Ensure any new investigation results are also updated in the Assessment section.

INTERIM UPDATES

Provide a concise summary of patient's clinical status across recent visits.

Present in reverse chronological order (most recent first).

Required Elements:
- Summary of most recent 2-3 clinic visits (with dates in MM-DD-YYYY format)
- Changes in symptom severity or frequency
- Patient-reported functional status changes
- New complaints or concerns
- Medication adherence and tolerance
- Response to current treatment plan
- Transportation/access barriers if relevant
- Family support/caregiving needs if relevant

Medication Changes Summary:
Within the narrative, incorporate:
- Medications started (name, dose, date, indication)
- Medications stopped (name, date, reason)
- Dosage changes (medication, old dose → new dose, date, rationale)
- Any medication-related issues or concerns

CRITICAL: Integrate medication information naturally within the narrative paragraphs. Do NOT create a separate "Medication Verification" subsection or paragraph with that heading.

Formatting: Write as brief, organized paragraphs.

Note: Information here will eventually be consolidated into the Case Summary as time progresses.

HISTORY

Default Response:
"Patient's past medical, social, family, and allergies history has been reviewed by me."

CRITICAL: If detailed historical information is available in the source records, you may expand this section with specific details, but the default statement above should always be included.

If Detailed Information Available, Include AFTER the default statement:

Past Medical History:
- [List of chronic conditions and resolved major illnesses]

Past Surgical History:
- [Procedures with dates in MM-DD-YYYY or MM-YYYY format]

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

MEDICATIONS

Format as structured list:

Current Medications:
- [Medication Name (BRAND NAME)] [Dosage] [Route] [Frequency]
  [Additional instructions - "as needed for..." if applicable]
- [Continue for ALL medications - NO truncation]

Example Format:
- acetaminophen (TYLENOL) 650 mg rectally every 4 hours as needed for Pain
- amitriptyline (ELAVIL) 10 mg by mouth nightly

Include:
- Generic name with brand name in parentheses
- Exact dosage, route, and frequency
- "As needed" indications where applicable
- Note dispense quantity and refills if available

Note: If autopopulated by EPIC smartphrase, state: "Current medications as documented in EPIC medication list [as of MM-DD-YYYY]."

CRITICAL: Use ONLY the dosages from this section or latest Assessment mention when resolving conflicts.

REVIEW OF SYSTEMS

For Neurology Specialty (adapt to relevant specialty as needed):

CRITICAL FORMATTING RULES:
- ONLY include systems with documented POSITIVE symptoms
- Do NOT mention systems with no documented findings
- Do NOT include phrases like "Not documented"
- At the END of the section, add: "All other systems reviewed and negative."

Neurological:
- [Only include if positive findings: Headaches, dizziness, seizures, weakness, numbness, tingling]
- [Only include if positive findings: Vision changes, hearing changes]
- [Only include if positive findings: Balance problems, gait disturbances]
- [Only include if positive findings: Memory issues, cognitive changes]
- [Only include if positive findings: Speech difficulties]

General Systems (only include systems with positive findings):
- Constitutional: [Findings - only if positive]
- Cardiovascular: [Findings - only if positive]
- Respiratory: [Findings - only if positive]
- Gastrointestinal: [Findings - only if positive]
- Genitourinary: [Findings - only if positive]
- Musculoskeletal: [Findings - only if positive]
- Skin: [Findings - only if positive]
- Psychiatric: [Findings - only if positive]
- Endocrine: [Findings - only if positive]
- Hematologic/Lymphatic: [Findings - only if positive]

Final statement: "All other systems reviewed and negative."

Formatting: Use hyphenated lists for positive findings only.

PHYSICAL EXAM

Vitals:
[ONLY include available vital signs - omit any that are not documented]
- Blood Pressure: [value] mmHg
- Heart Rate: [value] bpm
- Respiratory Rate: [value] breaths/min
- Temperature: [value] °F
- Weight: [value] lbs/kg
- Height: [value] inches/cm
- BMI: [value]

CRITICAL: Do NOT include "Not documented" for missing vitals. Simply omit the line item if not available.

Note: If fetched by smartphrase, may state "Vitals as documented in EPIC flowsheet."

General Examination:
[Document general appearance, distress level, body habitus]

Neurological Examination:

INSTRUCTION: Copy from the most recent note since neurological examination findings typically remain stable over extended periods.

Structure:
- GENERAL: awake, alert, distress level
- HIGHER FUNCTIONS: orientation, language, knowledge
- PSYCHIATRIC: mood, memory, attention
- CRANIAL NERVES: organized by function
  - Cranial Nerves I-XII: [Document all systematically]
- MOTOR SYSTEM:
  - Gait: [Describe casual, tandem, Romberg first]
  - Strength: [Use 0-5 scale with +/- modifiers, e.g., 4+/5]
  - Tone: [Document]
  - Bulk: [Document]
  - Movements: [Document]
  - Coordination: [Finger-to-nose, heel-to-shin]
- SENSORY SYSTEM:
  - By modality: [Pinprick, vibration, proprioception]
  - With anatomic distribution
- REFLEXES:
  - Grade 0-4 scale
  - Listed by anatomic location
  - Include pathological reflexes

Special Tests: [If applicable]

Format: Present in standard neurological examination structure with specific grading scales.

CRITICAL: If examination components are not documented, omit those sections entirely. Do NOT include "Not documented" statements.

DIAGNOSES

Format as numbered list with ICD codes in table format:

     ICD-10-CM    ICD-9-CM
1. [Diagnosis 1]    [Code]    [Code]
2. [Diagnosis 2]    [Code]    [Code]
3. [Diagnosis 3]    [Code]    [Code]
                    [Code]    [Code]  (if multiple codes for same diagnosis)

Requirements:
- Number each diagnosis
- Include BOTH ICD-10-CM and ICD-9-CM codes
- Some diagnoses may have multiple codes (list all)
- Align codes in columns for readability

DO NOT include codes in the Assessment section - codes belong only here.

ASSESSMENT

CRITICAL INSTRUCTION:
- Copy the Assessment section from the most recent clinical note WITHOUT ANY MODIFICATIONS.
- This section should be used as the HIGHEST PRIORITY source for resolving conflicts in other sections.

Do NOT:
- Update with new information
- Add interpretations
- Modify diagnoses
- Change wording

Format for Each Major Diagnosis (when present in source):
- Problem name (matching the diagnosis list) - written in plain text without any formatting
- Dense paragraph format (not bullet points) including:
  - When first identified (with date in MM-DD-YYYY or MM-YYYY format)
  - Relevant imaging timeline with dates and essential findings only
  - Current status and key symptoms
  - Clinical reasoning about etiology (concise)
  - Treatments attempted with outcomes (summarized)
  - Current management
  - Future considerations if relevant
  - Critical uncertainties only

Verification Step:
Ensure that any results (laboratory, imaging), medications, symptoms/signs, or clinical trials mentioned in the Assessment are properly documented in the relevant sections above (Relevant Investigations, Medications, Interim Updates, etc.).

PLAN

CRITICAL INSTRUCTION:
- Copy the Plan section from the most recent clinical note WITHOUT ANY MODIFICATIONS.

Do NOT:
- Update recommendations
- Add new interventions
- Modify follow-up instructions
- Change medication plans

Typical Elements (when present in source):
- Medication changes with reasoning
- New diagnostic tests ordered
- Referrals to other specialists
- Patient education provided
- Follow-up interval
- When patient refuses treatments, note this

Verification Step:
Cross-reference the Plan section to ensure:
- Medications mentioned in Plan are listed in Medications section
- Investigations mentioned are documented in Relevant Investigations section
- Symptoms/signs referenced are noted in appropriate sections
- Clinical trials or special interventions are documented in relevant sections above

---

FORMATTING STANDARDS:
- Use clear section headers exactly as shown above
- Maintain consistent date format throughout: MM-DD-YYYY (or MM-YYYY, or YYYY minimum)
- Include timestamps where available: HH:MM AM/PM
- Use hyphenated lists for medications, investigations, history items, laboratory results
- Ensure proper spacing between sections for readability
- Use appropriate medical terminology and standard abbreviations
- Maintain professional medical documentation standards throughout
- One blank line between major sections
- Dense but organized paragraphs (4-7 sentences)
- Professional, empathetic tone without excessive courtesy language
- NO asterisks, hashtags, or markdown formatting symbols
- NO bold, italics, or text emphasis markers
- Use only plain text
- Do NOT include "Not documented" or similar phrases - simply omit sections without data

---

IMPORTANT NOTES:

If multiple source documents are provided:
Synthesize information while maintaining chronological accuracy and avoiding duplication. Consolidate details efficiently without deleting facts.

If information conflicts between documents:
Use the Assessment section as HIGHEST PRIORITY source. Note discrepancies when irreconcilable and indicate which source (with date) contains each piece of information.

Quality Verification:
Before finalizing, verify:
- Consistency analysis completed and conflicts resolved
- All dates and timestamps are accurate and properly formatted (MM-DD-YYYY minimum)
- Chronological consistency throughout the document
- Date discrepancies resolved without explanatory notes in output
- Medication timeline is complete and accurate (start/stop/changes)
- All investigations are documented with dates
- Laboratory results presented as hyphenated lists under date headers
- Imaging findings presented without status indicators
- Assessment and Plan are copied verbatim from most recent note
- Cross-references between sections are accurate
- No fabricated or inferred information
- Medical terminology is used correctly
- Sections without data are omitted entirely (no "Not documented" phrases)
- Exact attribution preserved from source (never changed who said/did/reported)
- Cautious medical language maintained ("supportive of," "consistent with," "appears to be")
- Patient voice preserved ("she says," "he reports," "patient feels")
- Treatment trials clearly documented (attempt → outcome → reason for change)
- NO asterisks, hashtags, or formatting symbols used anywhere in output
- Problem names in Assessment written in plain text without formatting
- Review of Systems includes only positive findings with final "All other systems reviewed and negative" statement
- Vitals section omits any undocumented measurements
- Medication changes integrated naturally into Interim Updates narrative without separate subsection

---
Begin your response with the section headers starting from "OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE" and populate all sections systematically following this exact structure.
"""
}
