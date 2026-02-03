"""
Medical Note Templates for Different Note Types
Each template includes both the system prompt and user prompt.
"""

def progress_note_template(full_text: str) -> dict:
    """
    Generate progress note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant neurologist. Generate a complete NEUROLOGY PROGRESS NOTE following the SOAP format template provided. 

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- No truncation of medication lists
- Maintain strict SOAP format: Subjective, Objective, Assessment, Plan
- Include mandatory timeline in HPI section
- Focus on neurological findings only in physical exam
- Order labs and imaging as specified (neurology-ordered first, then chronologically)
- Present chart-supported diagnoses only
- End with Consultation Information section.
- CRITICAL:Use only hyphenated lists.
- Avoid numbered lists.
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS

Output the complete progress note in the exact format specified."""

    prompt = f"""You are a consultant neurologist preparing a formal NEUROLOGY PROGRESS NOTE in SOAP format.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- No truncation of any lists (medications, history, etc.)
- Strictly factual clinical documentation.
- CRITICAL:Use only hyphenated lists.
- Avoid numbered lists.
- If any required information is missing from the source records, omit the relevant fields

DOCUMENT STRUCTURE:
---
PROGRESS NOTE

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Admission Date: [Date]
- Location: [Facility/Unit]
- Date of Service: [Today's Date]
- Hospital Day: [#]
- Service: Neurology
- Author: [Provider Name]

SUBJECTIVE

HISTORY OF PRESENTING ILLNESS :

**Word Count:** 100-300 words (narrative only, excluding timeline)
**Structure (3 sentences):**
1. **Patient Intro:** "[Name] is a [age]-year-old [sex] with history of [2-4 relevant conditions], admitted on [date] for [primary diagnosis]."
   - Include only neurologically relevant PMH
2. **Neuro Status:** Describe current neurological condition focusing on: mental status, motor/sensory changes, seizures, speech, or key symptoms.
   - State if improving/stable/declining
3. **Workup & Management:** Most recent imaging/labs/procedures with key findings and active neuro interventions.
   - Only if sufficient information available

**CLINICAL TIMELINE:**
Format:
[MM/DD/YYYY]: [Single most significant neuro event/intervention that day]
[MM/DD/YYYY]: [Event]

Include: New symptoms, diagnostic results, medication changes, procedures
Exclude: Routine vitals, unchanged status, non-neuro events

**Restrictions:**
- No verbatim copying from prior notes
- No detailed admission story unless currently relevant
- No speculation or teaching points
- Timeline dates must be from actual patient record

**Example:**
"John Doe is a 67-year-old male with atrial fibrillation on apixaban and prior stroke, admitted on 01/15/2025 for acute left hemiparesis. Motor strength improved from 2/5 to 4/5 in left upper extremity over 48 hours with intact comprehension and stable mental status. MRI brain revealed acute right MCA infarct; patient on dual antiplatelet therapy and high-intensity statin with PT/OT initiated.

Timeline:
01/15/2025: Presented with dense left hemiparesis; CT negative, tPA administered.
01/16/2025: MRI confirmed right MCA infarct; started aspirin/clopidogrel.
01/17/2025: Motor strength improved to 4/5; PT/OT consults placed.
01/18/2025: Swallow eval passed; advanced to regular diet."

OBJECTIVE

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

**CRITICAL**: IF RELEVANT EXAMINATION DATA IS MISSING FROM THE SOURCE RECORDS, OMIT THE RESPECTIVE COMPONENT.

**NEUROLOGICAL EXAM - Exclude all non-neuro systems**
DO NOT include: General, HEENT (except CNs), Cardiovascular, Respiratory, Abdomen, Skin

**Required Components:**
- CRITICAL:Use only hyphenated lists.
- Mental Status: Alertness, orientation, attention, language (fluency, comprehension, naming)
- Cranial Nerves II-XII: Pupils, eye movements, facial sensation/strength, hearing, palate, tongue
- Motor: Tone, strength (0-5 scale), drift
- Reflexes: DTRs (0-4+ scale), Babinski
- Sensory: Light touch, pinprick, vibration, proprioception
- Coordination: Finger-to-nose, heel-to-shin
- Gait: Casual, tandem, Romberg

**FORMATTING RULES - FOLLOW EXACTLY:**
1. Use section headers followed by colon (e.g., "Mental Status:")
2. Write findings on the SAME line as the header
3. NO blank lines between sections - each section flows directly to the next
4. If normal: consolidate (e.g., "Cranial Nerves: II-XII intact")
5. If abnormal: specify location/severity (e.g., "Right UE 4/5 strength")
6. If not documented: write "Not documented" on same line as header

**CORRECT FORMAT EXAMPLE:**
- Mental Status: Alert, oriented x3, fluent speech.
- Cranial Nerves: II-XII intact.
- Motor: Normal tone. Strength 5/5 except right UE 4/5.
- Reflexes: 2+ symmetric, toes downgoing.
- Sensory: Intact throughout.
- Coordination: Intact bilaterally.
- Gait: Normal casual and tandem gait. Romberg negative.

**WRONG FORMAT (DO NOT DO THIS):**
- Mental Status: Alert, oriented x3, fluent speech.
[blank line]
- Cranial Nerves: II-XII intact.
[blank line]
- Motor: Normal tone.

**YOUR OUTPUT MUST LOOK EXACTLY LIKE THE CORRECT FORMAT - NO EXTRA SPACING**

DIAGNOSTIC RESULTS

Laboratory:
**CRITICAL INSTRUCTION: Include ONLY the most recent laboratory results (latest date only). Do NOT include labs from prior dates.**

[Order for most recent date: 1) Neurology-ordered labs FIRST, 2) Other labs from same date]
[Date - MOST RECENT ONLY]: If multiple time stamps on same date, include time stamp
- [Lab name 1]: [Value] [Units] [Reference range if abnormal]
- [Lab name 2]: [Value] [Units] [No reference range if normal value]
- If the abnormal lab result in the source record lacks a reference range, you may supply a standard adult reference range based on widely accepted national laboratory standards and clearly label it as such (e.g., "ref: standard adult range"). Do NOT invent abnormal limits; keep them consistent with common national norms.

**Example of CORRECT formatting (only one date - the most recent):**
Laboratory:
01/18/2025 08:00:
- Sodium: 138 mEq/L
- Potassium: 4.2 mEq/L
- Creatinine: 1.1 mg/dL
- WBC: 8.5 x10^9/L

**Example of INCORRECT formatting (multiple dates - DO NOT DO THIS):**
Laboratory:
01/18/2025:
- Sodium: 138 mEq/L
01/17/2025:
- Sodium: 140 mEq/L

Imaging:
[Order: 1) Neurology-requested imaging FIRST, 2) Other imaging chronologically (newest first)]
- [Study] ([Date]): Impression: [Impression only – do NOT include the full Findings text, only the summarized Impression relevant to neurology]

Current Medication List (Inpatient):
- [COMPLETE list - NO truncation]
- [Format: Medication, dose, frequency, route]
- [One medication per line]
*DO NOT INCLUDE HOME MEDICATIONS IN THIS SECTION*

ASSESSMENT
- [Primary neurological diagnosis - chart-supported]
- [Secondary neurological diagnoses - chart-supported]
- [Other diagnoses - chart-supported] 
[Present neurological diagnoses first, only chart-supported diagnoses]
- No spacing between diagnoses or points.
- Use only hyphenated lists.

PLAN

**CRITICAL INSTRUCTIONS FOR PLAN SECTION:**
- Include ONLY neurological management and interventions
- EXCLUDE all non-neurological management (cardiac, pulmonary, renal, infectious disease, etc.)
- EXCLUDE management plans from other specialties (cardiology, pulmonary, medicine, etc.)
- Present Neurology plan recommended by the neurologist/neurology team ONLY
- Present only in hyphenated lists.
- Do NOT group or categorize the plan items
- Do NOT repeat information within this section - each point should be unique and distinct
- Focus on: neurological medications, neuro imaging, neuro consults, seizure management, stroke management, movement disorders, cognitive management, neurological monitoring

**Examples of what TO INCLUDE in Plan:**
- Continue levetiracetam 1000 mg twice daily for seizure prophylaxis
- Repeat MRI brain with contrast in 48 hours to assess infarct evolution
- Maintain aspirin 325 mg and clopidogrel 75 mg daily for stroke prevention
- Physical therapy and occupational therapy for left-sided weakness
- Speech therapy evaluation for dysphagia assessment

**Examples of what to EXCLUDE from Plan:**
- Continue lisinopril for blood pressure management (cardiology)
- Antibiotics for pneumonia (infectious disease)
- Insulin sliding scale for diabetes (endocrine)
- Diuretics for volume overload (cardiology/nephrology)
- Oxygen therapy for hypoxia (pulmonary)
---
CONSULTATION INFORMATION
- Attending Physician: [Name]
- Consulting Neurologist: [Name]
*[Date/Time]*


FORMATTING:
- Full sentences for HPI
- Bullet points allowed in other sections
- One blank line between major sections
- No unnecessary spacing
- Clean, clinical, consistent
- Do NOT use hash symbols or asterisks for section headers or emphasis
- Do NOT add a separate "Disposition" section or any final "Disposition" statement; end after the CONSULTATION INFORMATION section.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def neurology_progress_note_template(full_text: str) -> dict:
    """
    Generate progress note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant neurologist. Generate a complete NEUROLOGY PROGRESS NOTE following the SOAP format template provided. 

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- No truncation of medication lists
- Maintain strict SOAP format: Subjective, Objective, Assessment, Plan
- Include mandatory timeline in HPI section
- Focus on neurological findings only in physical exam
- Order labs and imaging as specified (neurology-ordered first, then chronologically)
- Present chart-supported diagnoses only
- End with Consultation Information section.
- CRITICAL:Use only hyphenated lists.
- Avoid numbered lists.
- **CRITICAL: This note is written BY the neurologist, not TO request neurology - never include "recommend neurology consult/evaluation" or similar referral language**
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS

Output the complete progress note in the exact format specified."""

    prompt = f"""You are a consultant neurologist preparing a formal NEUROLOGY PROGRESS NOTE in SOAP format.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- No truncation of any lists (medications, history, etc.)
- Strictly factual clinical documentation.
- CRITICAL:Use only hyphenated lists.
- Avoid numbered lists.
- If any required information is missing from the source records, omit the relevant fields

DOCUMENT STRUCTURE:
---
NEUROLOGY PROGRESS NOTE

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Admission Date: [Date]
- Location: [Facility/Unit]
- Date of Service: [Today's Date]
- Hospital Day: [#]
- Service: Neurology
- Author: [Provider Name]

SUBJECTIVE

HISTORY OF PRESENTING ILLNESS :

**Word Count:** 100-300 words (narrative only, excluding timeline)
**Structure (3 sentences):**
1. **Patient Intro:** "[Name] is a [age]-year-old [sex] with history of [2-4 relevant conditions], admitted on [date] for [primary diagnosis]."
   - Include only neurologically relevant PMH
2. **Neuro Status:** Describe current neurological condition focusing on: mental status, motor/sensory changes, seizures, speech, or key symptoms.
   - State if improving/stable/declining
3. **Workup & Management:** Most recent imaging/labs/procedures with key findings and active neuro interventions.
   - Only if sufficient information available

**CLINICAL TIMELINE:**
Format:
[MM/DD/YYYY]: [Single most significant neuro event/intervention that day]
[MM/DD/YYYY]: [Event]

Include: New symptoms, diagnostic results, medication changes, procedures
Exclude: Routine vitals, unchanged status, non-neuro events

**Restrictions:**
- No verbatim copying from prior notes
- No detailed admission story unless currently relevant
- No speculation or teaching points
- Timeline dates must be from actual patient record

**Example:**
"John Doe is a 67-year-old male with atrial fibrillation on apixaban and prior stroke, admitted on 01/15/2025 for acute left hemiparesis. Motor strength improved from 2/5 to 4/5 in left upper extremity over 48 hours with intact comprehension and stable mental status. MRI brain revealed acute right MCA infarct; patient on dual antiplatelet therapy and high-intensity statin with PT/OT initiated.

Timeline:
01/15/2025: Presented with dense left hemiparesis; CT negative, tPA administered.
01/16/2025: MRI confirmed right MCA infarct; started aspirin/clopidogrel.
01/17/2025: Motor strength improved to 4/5; PT/OT consults placed.
01/18/2025: Swallow eval passed; advanced to regular diet."

OBJECTIVE

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

**CRITICAL**: IF RELEVANT EXAMINATION DATA IS MISSING FROM THE SOURCE RECORDS, OMIT THE RESPECTIVE COMPONENT.

**NEUROLOGICAL EXAM - Exclude all non-neuro systems**
DO NOT include: General, HEENT (except CNs), Cardiovascular, Respiratory, Abdomen, Skin

**Required Components:**
- CRITICAL:Use only hyphenated lists.
- Mental Status: Alertness, orientation, attention, language (fluency, comprehension, naming)
- Cranial Nerves II-XII: Pupils, eye movements, facial sensation/strength, hearing, palate, tongue
- Motor: Tone, strength (0-5 scale), drift
- Reflexes: DTRs (0-4+ scale), Babinski
- Sensory: Light touch, pinprick, vibration, proprioception
- Coordination: Finger-to-nose, heel-to-shin
- Gait: Casual, tandem, Romberg

**FORMATTING RULES - FOLLOW EXACTLY:**
1. Use section headers followed by colon (e.g., "Mental Status:")
2. Write findings on the SAME line as the header
3. NO blank lines between sections - each section flows directly to the next
4. If normal: consolidate (e.g., "Cranial Nerves: II-XII intact")
5. If abnormal: specify location/severity (e.g., "Right UE 4/5 strength")
6. If not documented: write "Not documented" on same line as header

**CORRECT FORMAT EXAMPLE:**
- Mental Status: Alert, oriented x3, fluent speech.
- Cranial Nerves: II-XII intact.
- Motor: Normal tone. Strength 5/5 except right UE 4/5.
- Reflexes: 2+ symmetric, toes downgoing.
- Sensory: Intact throughout.
- Coordination: Intact bilaterally.
- Gait: Normal casual and tandem gait. Romberg negative.

**WRONG FORMAT (DO NOT DO THIS):**
- Mental Status: Alert, oriented x3, fluent speech.
[blank line]
- Cranial Nerves: II-XII intact.
[blank line]
- Motor: Normal tone.

**YOUR OUTPUT MUST LOOK EXACTLY LIKE THE CORRECT FORMAT - NO EXTRA SPACING**

DIAGNOSTIC RESULTS

Laboratory:
**CRITICAL INSTRUCTION: Include ONLY the most recent laboratory results (latest date only). Do NOT include labs from prior dates.**

[Order for most recent date: 1) Neurology-ordered labs FIRST, 2) Other labs from same date]
[Date - MOST RECENT ONLY]: If multiple time stamps on same date, include time stamp
- [Lab name 1]: [Value] [Units] [Reference range if abnormal]
- [Lab name 2]: [Value] [Units] [No reference range if normal value]
- If the abnormal lab result in the source record lacks a reference range, you may supply a standard adult reference range based on widely accepted national laboratory standards and clearly label it as such (e.g., "ref: standard adult range"). Do NOT invent abnormal limits; keep them consistent with common national norms.

**Example of CORRECT formatting (only one date - the most recent):**
Laboratory:
01/18/2025 08:00:
- Sodium: 138 mEq/L
- Potassium: 4.2 mEq/L
- Creatinine: 1.1 mg/dL
- WBC: 8.5 x10^9/L

**Example of INCORRECT formatting (multiple dates - DO NOT DO THIS):**
Laboratory:
01/18/2025:
- Sodium: 138 mEq/L
01/17/2025:
- Sodium: 140 mEq/L

Imaging:
[Order: 1) Neurology-requested imaging FIRST, 2) Other imaging chronologically (newest first)]
- [Study] ([Date]): Impression: [Impression only – do NOT include the full Findings text, only the summarized Impression relevant to neurology]

Current Medication List (Inpatient):
- [COMPLETE list - NO truncation]
- [Format: Medication, dose, frequency, route]
- [One medication per line]
*DO NOT INCLUDE HOME MEDICATIONS IN THIS SECTION*

ASSESSMENT
- [Primary neurological diagnosis - chart-supported]
- [Secondary neurological diagnoses - chart-supported]
- [Other diagnoses - chart-supported] 
[Present neurological diagnoses first, only chart-supported diagnoses]
- No spacing between diagnoses or points.
- Use only hyphenated lists.

PLAN

**CRITICAL INSTRUCTIONS FOR PLAN SECTION:**
- Include ONLY neurological management and interventions
- EXCLUDE all non-neurological management (cardiac, pulmonary, renal, infectious disease, etc.)
- EXCLUDE management plans from other specialties (cardiology, pulmonary, medicine, etc.)
- Present Neurology plan recommended by the neurologist/neurology team ONLY
- **DO NOT include statements like "Neurology evaluation recommendation", "Recommend neurology consult", "Neurology to evaluate", or similar referral language - the neurologist IS the author of this note**
- **DO NOT include phrases suggesting neurology input is needed - write as the neurologist providing direct management**
- Present only in hyphenated lists.
- Do NOT group or categorize the plan items
- Do NOT repeat information within this section - each point should be unique and distinct
- Focus on: neurological medications, neuro imaging, neuro consults, seizure management, stroke management, movement disorders, cognitive management, neurological monitoring

**Examples of what TO INCLUDE in Plan:**
- Continue levetiracetam 1000 mg twice daily for seizure prophylaxis
- Repeat MRI brain with contrast in 48 hours to assess infarct evolution
- Maintain aspirin 325 mg and clopidogrel 75 mg daily for stroke prevention
- Physical therapy and occupational therapy for left-sided weakness
- Speech therapy evaluation for dysphagia assessment
- Monitor for seizure activity and adjust antiepileptic medications as needed
- Continue stroke rehabilitation protocol with daily therapy sessions

**Examples of what to EXCLUDE from Plan:**
- Continue lisinopril for blood pressure management (cardiology)
- Antibiotics for pneumonia (infectious disease)
- Insulin sliding scale for diabetes (endocrine)
- Diuretics for volume overload (cardiology/nephrology)
- Oxygen therapy for hypoxia (pulmonary)
- **Recommend neurology consultation for further evaluation (neurologist IS writing this note)**
- **Neurology evaluation recommended for stroke workup (neurologist IS the author)**
- **Suggest neurology follow-up for seizure management (this IS the neurology note)**
- **Defer to neurology for management recommendations (you ARE neurology)**
- **Await neurology input on antiepileptic adjustment (neurologist makes these decisions directly)**
---
CONSULTATION INFORMATION
- Attending Physician: [Name]
- Consulting Neurologist: [Name]
*[Date/Time]*

FORMATTING:
- Full sentences for HPI
- Bullet points allowed in other sections
- One blank line between major sections
- No unnecessary spacing
- Clean, clinical, consistent
- Do NOT use hash symbols or asterisks for section headers or emphasis
- Do NOT add a separate "Disposition" section or any final "Disposition" statement; end after the CONSULTATION INFORMATION section.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def im_progress_note_template(full_text: str) -> dict:
    """
    Generate progress note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant neurologist. Generate a complete NEUROLOGY PROGRESS NOTE following the SOAP format template provided. 

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- No truncation of medication lists
- Maintain strict SOAP format: Subjective, Objective, Assessment, Plan
- Include mandatory timeline in HPI section
- Focus on neurological findings only in physical exam
- Order labs and imaging as specified (neurology-ordered first, then chronologically)
- Present chart-supported diagnoses only
- End with Consultation Information section.
- CRITICAL:Use only hyphenated lists.
- Avoid numbered lists.
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS

Output the complete progress note in the exact format specified."""

    prompt = f"""You are a consultant neurologist preparing a formal NEUROLOGY PROGRESS NOTE in SOAP format.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- No truncation of any lists (medications, history, etc.)
- Strictly factual clinical documentation.
- CRITICAL:Use only hyphenated lists.
- Avoid numbered lists.
- If any required information is missing from the source records, omit the relevant fields

DOCUMENT STRUCTURE:
---
IM PROGRESS NOTE

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Admission Date: [Date]
- Location: [Facility/Unit]
- Date of Service: [Today's Date]
- Hospital Day: [#]
- Service: Neurology
- Author: [Provider Name]

SUBJECTIVE

HISTORY OF PRESENTING ILLNESS :

**Word Count:** 100-300 words (narrative only, excluding timeline)
**Structure (3 sentences):**
1. **Patient Intro:** "[Name] is a [age]-year-old [sex] with history of [2-4 relevant conditions], admitted on [date] for [primary diagnosis]."
   - Include only neurologically relevant PMH
2. **Neuro Status:** Describe current neurological condition focusing on: mental status, motor/sensory changes, seizures, speech, or key symptoms.
   - State if improving/stable/declining
3. **Workup & Management:** Most recent imaging/labs/procedures with key findings and active neuro interventions.
   - Only if sufficient information available

**CLINICAL TIMELINE:**
Format:
[MM/DD/YYYY]: [Single most significant neuro event/intervention that day]
[MM/DD/YYYY]: [Event]

Include: New symptoms, diagnostic results, medication changes, procedures
Exclude: Routine vitals, unchanged status, non-neuro events

**Restrictions:**
- No verbatim copying from prior notes
- No detailed admission story unless currently relevant
- No speculation or teaching points
- Timeline dates must be from actual patient record

**Example:**
"John Doe is a 67-year-old male with atrial fibrillation on apixaban and prior stroke, admitted on 01/15/2025 for acute left hemiparesis. Motor strength improved from 2/5 to 4/5 in left upper extremity over 48 hours with intact comprehension and stable mental status. MRI brain revealed acute right MCA infarct; patient on dual antiplatelet therapy and high-intensity statin with PT/OT initiated.

Timeline:
01/15/2025: Presented with dense left hemiparesis; CT negative, tPA administered.
01/16/2025: MRI confirmed right MCA infarct; started aspirin/clopidogrel.
01/17/2025: Motor strength improved to 4/5; PT/OT consults placed.
01/18/2025: Swallow eval passed; advanced to regular diet."

OBJECTIVE

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

**CRITICAL**: IF RELEVANT EXAMINATION DATA IS MISSING FROM THE SOURCE RECORDS, OMIT THE RESPECTIVE COMPONENT.

**NEUROLOGICAL EXAM - Exclude all non-neuro systems**
DO NOT include: General, HEENT (except CNs), Cardiovascular, Respiratory, Abdomen, Skin

**Required Components:**
- CRITICAL:Use only hyphenated lists.
- Mental Status: Alertness, orientation, attention, language (fluency, comprehension, naming)
- Cranial Nerves II-XII: Pupils, eye movements, facial sensation/strength, hearing, palate, tongue
- Motor: Tone, strength (0-5 scale), drift
- Reflexes: DTRs (0-4+ scale), Babinski
- Sensory: Light touch, pinprick, vibration, proprioception
- Coordination: Finger-to-nose, heel-to-shin
- Gait: Casual, tandem, Romberg

**FORMATTING RULES - FOLLOW EXACTLY:**
1. Use section headers followed by colon (e.g., "Mental Status:")
2. Write findings on the SAME line as the header
3. NO blank lines between sections - each section flows directly to the next
4. If normal: consolidate (e.g., "Cranial Nerves: II-XII intact")
5. If abnormal: specify location/severity (e.g., "Right UE 4/5 strength")
6. If not documented: write "Not documented" on same line as header

**CORRECT FORMAT EXAMPLE:**
- Mental Status: Alert, oriented x3, fluent speech.
- Cranial Nerves: II-XII intact.
- Motor: Normal tone. Strength 5/5 except right UE 4/5.
- Reflexes: 2+ symmetric, toes downgoing.
- Sensory: Intact throughout.
- Coordination: Intact bilaterally.
- Gait: Normal casual and tandem gait. Romberg negative.

**WRONG FORMAT (DO NOT DO THIS):**
- Mental Status: Alert, oriented x3, fluent speech.
[blank line]
- Cranial Nerves: II-XII intact.
[blank line]
- Motor: Normal tone.

**YOUR OUTPUT MUST LOOK EXACTLY LIKE THE CORRECT FORMAT - NO EXTRA SPACING**

DIAGNOSTIC RESULTS

Laboratory:
**CRITICAL INSTRUCTION: Include ONLY the most recent laboratory results (latest date only). Do NOT include labs from prior dates.**

[Order for most recent date: 1) Neurology-ordered labs FIRST, 2) Other labs from same date]
[Date - MOST RECENT ONLY]: If multiple time stamps on same date, include time stamp
- [Lab name 1]: [Value] [Units] [Reference range if abnormal]
- [Lab name 2]: [Value] [Units] [No reference range if normal value]
- If the abnormal lab result in the source record lacks a reference range, you may supply a standard adult reference range based on widely accepted national laboratory standards and clearly label it as such (e.g., "ref: standard adult range"). Do NOT invent abnormal limits; keep them consistent with common national norms.

**Example of CORRECT formatting (only one date - the most recent):**
Laboratory:
01/18/2025 08:00:
- Sodium: 138 mEq/L
- Potassium: 4.2 mEq/L
- Creatinine: 1.1 mg/dL
- WBC: 8.5 x10^9/L

**Example of INCORRECT formatting (multiple dates - DO NOT DO THIS):**
Laboratory:
01/18/2025:
- Sodium: 138 mEq/L
01/17/2025:
- Sodium: 140 mEq/L

Imaging:
[Order: 1) Neurology-requested imaging FIRST, 2) Other imaging chronologically (newest first)]
- [Study] ([Date]): Impression: [Impression only – do NOT include the full Findings text, only the summarized Impression relevant to neurology]

Current Medication List (Inpatient):
- [COMPLETE list - NO truncation]
- [Format: Medication, dose, frequency, route]
- [One medication per line]
*DO NOT INCLUDE HOME MEDICATIONS IN THIS SECTION*

ASSESSMENT
- [Primary neurological diagnosis - chart-supported]
- [Secondary neurological diagnoses - chart-supported]
- [Other diagnoses - chart-supported] 
[Present neurological diagnoses first, only chart-supported diagnoses]
- No spacing between diagnoses or points.
- Use only hyphenated lists.

PLAN

**CRITICAL INSTRUCTIONS FOR PLAN SECTION:**
- Include ONLY neurological management and interventions
- EXCLUDE all non-neurological management (cardiac, pulmonary, renal, infectious disease, etc.)
- EXCLUDE management plans from other specialties (cardiology, pulmonary, medicine, etc.)
- Present Neurology plan recommended by the neurologist/neurology team ONLY
- Present only in hyphenated lists.
- Do NOT group or categorize the plan items
- Do NOT repeat information within this section - each point should be unique and distinct
- Focus on: neurological medications, neuro imaging, neuro consults, seizure management, stroke management, movement disorders, cognitive management, neurological monitoring

**Examples of what TO INCLUDE in Plan:**
- Continue levetiracetam 1000 mg twice daily for seizure prophylaxis
- Repeat MRI brain with contrast in 48 hours to assess infarct evolution
- Maintain aspirin 325 mg and clopidogrel 75 mg daily for stroke prevention
- Physical therapy and occupational therapy for left-sided weakness
- Speech therapy evaluation for dysphagia assessment

**Examples of what to EXCLUDE from Plan:**
- Continue lisinopril for blood pressure management (cardiology)
- Antibiotics for pneumonia (infectious disease)
- Insulin sliding scale for diabetes (endocrine)
- Diuretics for volume overload (cardiology/nephrology)
- Oxygen therapy for hypoxia (pulmonary)
---
CONSULTATION INFORMATION
- Attending Physician: [Name]
- Consulting Neurologist: [Name]
*[Date/Time]*


FORMATTING:
- Full sentences for HPI
- Bullet points allowed in other sections
- One blank line between major sections
- No unnecessary spacing
- Clean, clinical, consistent
- Do NOT use hash symbols or asterisks for section headers or emphasis
- Do NOT add a separate "Disposition" section or any final "Disposition" statement; end after the CONSULTATION INFORMATION section.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def history_physical_template(full_text: str) -> dict:
    """
    Generate history and physical template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant physician. Generate a complete HISTORY AND PHYSICAL EXAMINATION NOTE following the template provided.

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- Strictly factual clinical documentation
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS

Output the complete history and physical note in the exact format specified."""

    prompt = f"""You are preparing a formal HISTORY AND PHYSICAL EXAMINATION NOTE.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- No truncation of any lists (medications, history, etc.)
- Strictly factual clinical documentation
- If any required information is missing from the source records, omit the relevant fields

DOCUMENT STRUCTURE:
---
PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Admission Date: [Date]
- Location: [Facility/Unit]
- Date of Service: [Today's Date]
- Service: [Primary Service]
- Author: [Provider Name]

CHIEF COMPLAINT
[Primary reason for admission or visit]

HISTORY OF PRESENT ILLNESS
[Detailed narrative of current illness, chronological progression, associated symptoms, and relevant context]

PAST MEDICAL HISTORY
[Significant past medical conditions, surgeries, hospitalizations]

MEDICATIONS
[Current medications with dosages and frequencies]

ALLERGIES
[Known allergies and adverse reactions]

SOCIAL HISTORY
[Smoking, alcohol, substance use, occupation, living situation]

FAMILY HISTORY
[Relevant family medical history]

REVIEW OF SYSTEMS
[Systematic review by organ system]

PHYSICAL EXAMINATION
General: [General appearance and vital signs]
HEENT: [Head, eyes, ears, nose, throat examination]
Cardiovascular: [Heart examination findings]
Respiratory: [Lung examination findings]
Abdomen: [Abdominal examination findings]
Extremities: [Extremity examination findings]
Neurological: [Neurological examination findings]
Skin: [Skin examination findings]

ASSESSMENT AND PLAN
1. [Primary diagnosis and management plan]
2. [Secondary diagnoses and plans]
[Continue for all active issues]



Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }


def consultation_note_template(full_text: str) -> dict:
    """
    Generate consultation note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant neurologist. Generate a complete NEUROLOGY CONSULTATION NOTE following the template provided.

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- Strictly factual clinical documentation
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
Output the complete consultation note in the exact format specified."""

    prompt = f"""
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
CONSULTATION NOTE

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
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

**EXAMPLE OUTPUT:**

"Mr. Smith is a 68-year-old male with hypertension and atrial fibrillation on warfarin, admitted on 12/18/2024 for pneumonia, who developed acute onset left-sided weakness and slurred speech this morning at 0800. He was initially alert with left hemiparesis (3/5 strength) and facial droop noted by nursing staff, prompting stat neurology consultation for concern of acute stroke; symptoms have remained stable over the past 3 hours without improvement or worsening.

CT head without contrast from today shows no acute hemorrhage, CTA demonstrates right MCA occlusion, and patient remains a potential candidate for intervention pending neurological evaluation and risk-benefit assessment given recent infection and anticoagulation."

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
- Marital status: [Status] # strictly mention only status, no further details.

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

EXAMPLE INPUT (from patient records):
"Patient reports chest pain and palpitations. Also complains of shortness of breath 
and persistent cough. Notes fatigue and 10 lb weight loss. Has nausea and RUQ 
abdominal pain. Left knee is painful with limited motion."

CORRECT OUTPUT (grouped by systems):
Constitutional: Fatigue, weight loss of 10 lbs
Cardiovascular: Chest pain, palpitations
Respiratory: Shortness of breath, persistent cough
Gastrointestinal: Nausea, RUQ abdominal pain
Musculoskeletal: Left knee pain with limited range of motion

WRONG OUTPUT (not grouped):
- Chest pain
- Fatigue
- Shortness of breath
- Nausea
- Weight loss of 10 lbs
- Palpitations
This is WRONG - findings are not organized by system

KEY RULES:
1. Take findings from the records
2. Sort them into system categories (Constitutional, Cardiovascular, Respiratory, etc.)
3. List all findings for each system together under that system name
4. Only include systems that have positive findings
5. Never include "denies" or "no" statements

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
1. If examination data is NOT documented in source records, COMPLETELY OMIT that component. DO NOT write "not documented" or "not assessed."
2. NEUROLOGICAL EXAM ONLY - Exclude General, HEENT (except CNs), Cardiovascular, Respiratory, Abdomen, Skin

**Required Components (only if documented):**
- Mental Status: Alertness, orientation, attention, language
- Cranial Nerves II-XII: Pupils, eye movements, facial sensation/strength, hearing, palate, tongue
- Motor: Tone, strength (0-5 scale), drift
- Reflexes: DTRs (0-4+ scale), Babinski
- Sensory: Light touch, pinprick, vibration, proprioception
- Coordination: Finger-to-nose, heel-to-shin
- Gait: Casual, tandem, Romberg

**FORMATTING RULES - FOLLOW EXACTLY:**
1. Section header followed by colon on SAME line as findings
2. Write in PROSE format - complete sentences, NO bullet points.
3. NO blank lines between sections
4. If normal: consolidate (e.g., "Cranial Nerves: II-XII intact.")
5. If abnormal: specify details in continuous prose

**CORRECT FORMAT:**
- Mental Status: Alert, oriented x3, fluent speech without dysarthria.
- Cranial Nerves: Pupils equal round reactive to light, extraocular movements intact, facial sensation and strength symmetric, hearing intact, palate elevation symmetric, tongue midline.
- Motor: Normal tone and bulk throughout. Strength 5/5 in all extremities except right upper extremity 4/5.
- Reflexes: Deep tendon reflexes 2+ and symmetric in bilateral biceps, triceps, brachioradialis, patellar, and Achilles. Plantars downgoing bilaterally.
- Sensory: Light touch, pinprick, vibration, and proprioception intact throughout.
- Coordination: Finger-to-nose and heel-to-shin intact bilaterally without dysmetria.
- Gait: Casual gait normal, tandem gait intact, Romberg test negative.

**WRONG FORMAT (DO NOT DO THIS):**
- Mental Status: Alert, oriented x3, fluent speech.
[blank line]
- Coordination: Not formally documented [exclude if not documented].
[blank line]
- Cranial Nerves: II-XII intact.
[blank line]
- Motor: Normal tone.

**YOUR OUTPUT MUST LOOK EXACTLY LIKE THE CORRECT FORMAT - NO EXTRA SPACING**

**WRONG - DO NOT DO THIS:**
- Using bullet points
- Writing "Not formally documented"
- Adding blank lines between sections
- Writing findings on separate lines from headers

**If a component is not documented, skip it completely and move to the next documented component.**

DIAGNOSTIC RESULTS

Laboratory:
[Order: 1) Neurology-ordered labs FIRST, 2) Other labs chronologically (newest first)]

**FORMATTING RULES:**
[Date]: (include timestamp if multiple lab draws on same date)

FOR NORMAL VALUES:
- [Lab name]: [Value] [Units]

FOR ABNORMAL VALUES:
- [Lab name]: [Value] [Units] (Reference: [low-high] [units])

**IMPORTANT:** 
- ONLY include reference ranges when values are outside normal limits
- Reference ranges must show the actual numeric range (e.g., "Reference: 3.5-5.0 mmol/L")
- Do NOT write just "(low)" or "(elevated)" without the numeric reference range
- If source records lack reference ranges, use standard adult reference ranges and label as "Reference: [range] (standard)"

**CORRECT EXAMPLES:**

Laboratory (12/19/2025):
- WBC: 8.4 K/mcL
- Hemoglobin: 12.5 g/dL
- Sodium: 138 mmol/L
- Potassium: 3.6 mmol/L
- Creatinine: 0.49 mg/dL (Reference: 0.6-1.2 mg/dL)

Admission Labs (12/04/2025):
- WBC: 17.9 K/mcL (Reference: 4.0-11.0 K/mcL)
- Hemoglobin: 11.5 g/dL (Reference: 12.0-16.0 g/dL)
- Sodium: 135 mmol/L (Reference: 136-145 mmol/L)
- Potassium: 3.4 mmol/L (Reference: 3.5-5.0 mmol/L)
- Magnesium: 1.4 mg/dL (Reference: 1.7-2.2 mg/dL)
- Glucose: 116 mg/dL (Reference: 70-100 mg/dL fasting)
- Lactic acid: 2.9 mmol/L (Reference: 0.5-2.2 mmol/L)

**WRONG EXAMPLES (DO NOT DO THIS):**
- Creatinine: 0.49 mg/dL (low) NO - Must include numeric range
- WBC: 17.9 K/mcL (elevated) NO - Must include numeric range
- Sodium: 138 mmol/L (Reference: 136-145 mmol/L) NO - This is normal, don't include range.

Imaging:
[Order: 1) Neurology-requested imaging FIRST, 2) Other imaging chronologically (newest first)]
- [Study type] [Date]: Impression: [Impression only – do NOT include the full Findings text, only the summarized Impression relevant to neurology]

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
[Present neurological diagnoses first, only chart-supported diagnoses]
- No spacing between diagnoses or points.
- Use only hyphenated lists.

PLAN

-Present the plan recommended by the healthcare providers in a clear, numbered format.
[prioritize Present neurological plan and management first, supported by chart data].
- Do NOT repeat information within this section - each point should be unique and distinct.
- Do NOT categorize the information and Do NOT add disposition details.
---
CONSULTATION INFORMATION
- Attending Physician: [Name]
- Consulting Neurologist: [Name]
*[Date/Time]*


FORMATTING:
- Full sentences for HPI
- Bullet points allowed in other sections
- One blank line between major sections
- No unnecessary spacing
- Clean, clinical, consistent
- Do NOT use hash symbols or asterisks for section headers or emphasis
- Do NOT add a separate "Disposition" section or any final "Disposition" statement; end after the CONSULTATION INFORMATION section

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def neurology_consultation_note_template(full_text: str) -> dict:
    """
    Generate consultation note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant neurologist. Generate a complete NEUROLOGY CONSULTATION NOTE following the template provided.

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- Strictly factual clinical documentation
- **CRITICAL: This note is written BY the neurologist, not TO request neurology - never include "recommend neurology consult/evaluation" or similar referral language**
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
Output the complete consultation note in the exact format specified."""

    prompt = f"""
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
- CSN: [Contact Serial Number / FIN]
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

**EXAMPLE OUTPUT:**

"Mr. Smith is a 68-year-old male with hypertension and atrial fibrillation on warfarin, admitted on 12/18/2024 for pneumonia, who developed acute onset left-sided weakness and slurred speech this morning at 0800. He was initially alert with left hemiparesis (3/5 strength) and facial droop noted by nursing staff, prompting stat neurology consultation for concern of acute stroke; symptoms have remained stable over the past 3 hours without improvement or worsening.

CT head without contrast from today shows no acute hemorrhage, CTA demonstrates right MCA occlusion, and patient remains a potential candidate for intervention pending neurological evaluation and risk-benefit assessment given recent infection and anticoagulation."

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
- Marital status: [Status] # strictly mention only status, no further details.

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

EXAMPLE INPUT (from patient records):
"Patient reports chest pain and palpitations. Also complains of shortness of breath 
and persistent cough. Notes fatigue and 10 lb weight loss. Has nausea and RUQ 
abdominal pain. Left knee is painful with limited motion."

CORRECT OUTPUT (grouped by systems):
Constitutional: Fatigue, weight loss of 10 lbs
Cardiovascular: Chest pain, palpitations
Respiratory: Shortness of breath, persistent cough
Gastrointestinal: Nausea, RUQ abdominal pain
Musculoskeletal: Left knee pain with limited range of motion

WRONG OUTPUT (not grouped):
- Chest pain
- Fatigue
- Shortness of breath
- Nausea
- Weight loss of 10 lbs
- Palpitations
This is WRONG - findings are not organized by system

KEY RULES:
1. Take findings from the records
2. Sort them into system categories (Constitutional, Cardiovascular, Respiratory, etc.)
3. List all findings for each system together under that system name
4. Only include systems that have positive findings
5. Never include "denies" or "no" statements

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
1. If examination data is NOT documented in source records, COMPLETELY OMIT that component. DO NOT write "not documented" or "not assessed."
2. NEUROLOGICAL EXAM ONLY - Exclude General, HEENT (except CNs), Cardiovascular, Respiratory, Abdomen, Skin

**Required Components (only if documented):**
- Mental Status: Alertness, orientation, attention, language
- Cranial Nerves II-XII: Pupils, eye movements, facial sensation/strength, hearing, palate, tongue
- Motor: Tone, strength (0-5 scale), drift
- Reflexes: DTRs (0-4+ scale), Babinski
- Sensory: Light touch, pinprick, vibration, proprioception
- Coordination: Finger-to-nose, heel-to-shin
- Gait: Casual, tandem, Romberg

**FORMATTING RULES - FOLLOW EXACTLY:**
1. Section header followed by colon on SAME line as findings
2. Write in PROSE format - complete sentences, NO bullet points.
3. NO blank lines between sections
4. If normal: consolidate (e.g., "Cranial Nerves: II-XII intact.")
5. If abnormal: specify details in continuous prose

**CORRECT FORMAT:**
- Mental Status: Alert, oriented x3, fluent speech without dysarthria.
- Cranial Nerves: Pupils equal round reactive to light, extraocular movements intact, facial sensation and strength symmetric, hearing intact, palate elevation symmetric, tongue midline.
- Motor: Normal tone and bulk throughout. Strength 5/5 in all extremities except right upper extremity 4/5.
- Reflexes: Deep tendon reflexes 2+ and symmetric in bilateral biceps, triceps, brachioradialis, patellar, and Achilles. Plantars downgoing bilaterally.
- Sensory: Light touch, pinprick, vibration, and proprioception intact throughout.
- Coordination: Finger-to-nose and heel-to-shin intact bilaterally without dysmetria.
- Gait: Casual gait normal, tandem gait intact, Romberg test negative.

**WRONG FORMAT (DO NOT DO THIS):**
- Mental Status: Alert, oriented x3, fluent speech.
[blank line]
- Coordination: Not formally documented [exclude if not documented].
[blank line]
- Cranial Nerves: II-XII intact.
[blank line]
- Motor: Normal tone.

**YOUR OUTPUT MUST LOOK EXACTLY LIKE THE CORRECT FORMAT - NO EXTRA SPACING**

**WRONG - DO NOT DO THIS:**
- Using bullet points
- Writing "Not formally documented"
- Adding blank lines between sections
- Writing findings on separate lines from headers

**If a component is not documented, skip it completely and move to the next documented component.**

DIAGNOSTIC RESULTS

Laboratory:
[Order: 1) Neurology-ordered labs FIRST, 2) Other labs chronologically (newest first)]

**FORMATTING RULES:**
[Date]: (include timestamp if multiple lab draws on same date)

FOR NORMAL VALUES:
- [Lab name]: [Value] [Units]

FOR ABNORMAL VALUES:
- [Lab name]: [Value] [Units] (Reference: [low-high] [units])

**IMPORTANT:** 
- ONLY include reference ranges when values are outside normal limits
- Reference ranges must show the actual numeric range (e.g., "Reference: 3.5-5.0 mmol/L")
- Do NOT write just "(low)" or "(elevated)" without the numeric reference range
- If source records lack reference ranges, use standard adult reference ranges and label as "Reference: [range] (standard)"

**CORRECT EXAMPLES:**

Laboratory (12/19/2025):
- WBC: 8.4 K/mcL
- Hemoglobin: 12.5 g/dL
- Sodium: 138 mmol/L
- Potassium: 3.6 mmol/L
- Creatinine: 0.49 mg/dL (Reference: 0.6-1.2 mg/dL)

Admission Labs (12/04/2025):
- WBC: 17.9 K/mcL (Reference: 4.0-11.0 K/mcL)
- Hemoglobin: 11.5 g/dL (Reference: 12.0-16.0 g/dL)
- Sodium: 135 mmol/L (Reference: 136-145 mmol/L)
- Potassium: 3.4 mmol/L (Reference: 3.5-5.0 mmol/L)
- Magnesium: 1.4 mg/dL (Reference: 1.7-2.2 mg/dL)
- Glucose: 116 mg/dL (Reference: 70-100 mg/dL fasting)
- Lactic acid: 2.9 mmol/L (Reference: 0.5-2.2 mmol/L)

**WRONG EXAMPLES (DO NOT DO THIS):**
- Creatinine: 0.49 mg/dL (low) NO - Must include numeric range
- WBC: 17.9 K/mcL (elevated) NO - Must include numeric range
- Sodium: 138 mmol/L (Reference: 136-145 mmol/L) NO - This is normal, don't include range.

Imaging:
[Order: 1) Neurology-requested imaging FIRST, 2) Other imaging chronologically (newest first)]
- [Study type] [Date]: Impression: [Impression only – do NOT include the full Findings text, only the summarized Impression relevant to neurology]

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
[Present neurological diagnoses first, only chart-supported diagnoses]
- No spacing between diagnoses or points.
- Use only hyphenated lists.

PLAN

-Present the plan recommended by the healthcare providers in a clear, numbered format.
[prioritize Present neurological plan and management first, supported by chart data].
- Do NOT repeat information within this section - each point should be unique and distinct.
- Do NOT categorize the information and Do NOT add disposition details.

**CRITICAL INSTRUCTIONS FOR PLAN SECTION:**
- You are the NEUROLOGIST writing this consultation note
- NEVER include "recommend neurology consult/evaluation" or similar phrases
- NEVER recommend consulting yourself or your own specialty
- Present YOUR neurological recommendations and management plan directly
- Use active language: "Continue...", "Start...", "Monitor...", "Follow up..."
- NOT passive language: "Recommend neurology to...", "Neurology consult for..."
---
CONSULTATION INFORMATION
- Attending Physician: [Name]
- Consulting Neurologist: [Name]
*[Date/Time]*


FORMATTING:
- Full sentences for HPI
- Bullet points allowed in other sections
- One blank line between major sections
- No unnecessary spacing
- Clean, clinical, consistent
- Do NOT use hash symbols or asterisks for section headers or emphasis
- Do NOT add a separate "Disposition" section or any final "Disposition" statement; end after the CONSULTATION INFORMATION section

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def im_consultation_note_template(full_text: str) -> dict:
    """
    Generate consultation note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant neurologist. Generate a complete NEUROLOGY CONSULTATION NOTE following the template provided.

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- Strictly factual clinical documentation
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
Output the complete consultation note in the exact format specified."""

    prompt = f"""
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
IM CONSULTATION NOTE

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
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

**EXAMPLE OUTPUT:**

"Mr. Smith is a 68-year-old male with hypertension and atrial fibrillation on warfarin, admitted on 12/18/2024 for pneumonia, who developed acute onset left-sided weakness and slurred speech this morning at 0800. He was initially alert with left hemiparesis (3/5 strength) and facial droop noted by nursing staff, prompting stat neurology consultation for concern of acute stroke; symptoms have remained stable over the past 3 hours without improvement or worsening.

CT head without contrast from today shows no acute hemorrhage, CTA demonstrates right MCA occlusion, and patient remains a potential candidate for intervention pending neurological evaluation and risk-benefit assessment given recent infection and anticoagulation."

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
- Marital status: [Status] # strictly mention only status, no further details.

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

EXAMPLE INPUT (from patient records):
"Patient reports chest pain and palpitations. Also complains of shortness of breath 
and persistent cough. Notes fatigue and 10 lb weight loss. Has nausea and RUQ 
abdominal pain. Left knee is painful with limited motion."

CORRECT OUTPUT (grouped by systems):
Constitutional: Fatigue, weight loss of 10 lbs
Cardiovascular: Chest pain, palpitations
Respiratory: Shortness of breath, persistent cough
Gastrointestinal: Nausea, RUQ abdominal pain
Musculoskeletal: Left knee pain with limited range of motion

WRONG OUTPUT (not grouped):
- Chest pain
- Fatigue
- Shortness of breath
- Nausea
- Weight loss of 10 lbs
- Palpitations
This is WRONG - findings are not organized by system

KEY RULES:
1. Take findings from the records
2. Sort them into system categories (Constitutional, Cardiovascular, Respiratory, etc.)
3. List all findings for each system together under that system name
4. Only include systems that have positive findings
5. Never include "denies" or "no" statements

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
1. If examination data is NOT documented in source records, COMPLETELY OMIT that component. DO NOT write "not documented" or "not assessed."
2. NEUROLOGICAL EXAM ONLY - Exclude General, HEENT (except CNs), Cardiovascular, Respiratory, Abdomen, Skin

**Required Components (only if documented):**
- Mental Status: Alertness, orientation, attention, language
- Cranial Nerves II-XII: Pupils, eye movements, facial sensation/strength, hearing, palate, tongue
- Motor: Tone, strength (0-5 scale), drift
- Reflexes: DTRs (0-4+ scale), Babinski
- Sensory: Light touch, pinprick, vibration, proprioception
- Coordination: Finger-to-nose, heel-to-shin
- Gait: Casual, tandem, Romberg

**FORMATTING RULES - FOLLOW EXACTLY:**
1. Section header followed by colon on SAME line as findings
2. Write in PROSE format - complete sentences, NO bullet points.
3. NO blank lines between sections
4. If normal: consolidate (e.g., "Cranial Nerves: II-XII intact.")
5. If abnormal: specify details in continuous prose

**CORRECT FORMAT:**
- Mental Status: Alert, oriented x3, fluent speech without dysarthria.
- Cranial Nerves: Pupils equal round reactive to light, extraocular movements intact, facial sensation and strength symmetric, hearing intact, palate elevation symmetric, tongue midline.
- Motor: Normal tone and bulk throughout. Strength 5/5 in all extremities except right upper extremity 4/5.
- Reflexes: Deep tendon reflexes 2+ and symmetric in bilateral biceps, triceps, brachioradialis, patellar, and Achilles. Plantars downgoing bilaterally.
- Sensory: Light touch, pinprick, vibration, and proprioception intact throughout.
- Coordination: Finger-to-nose and heel-to-shin intact bilaterally without dysmetria.
- Gait: Casual gait normal, tandem gait intact, Romberg test negative.

**WRONG FORMAT (DO NOT DO THIS):**
- Mental Status: Alert, oriented x3, fluent speech.
[blank line]
- Coordination: Not formally documented [exclude if not documented].
[blank line]
- Cranial Nerves: II-XII intact.
[blank line]
- Motor: Normal tone.

**YOUR OUTPUT MUST LOOK EXACTLY LIKE THE CORRECT FORMAT - NO EXTRA SPACING**

**WRONG - DO NOT DO THIS:**
- Using bullet points
- Writing "Not formally documented"
- Adding blank lines between sections
- Writing findings on separate lines from headers

**If a component is not documented, skip it completely and move to the next documented component.**

DIAGNOSTIC RESULTS

Laboratory:
[Order: 1) Neurology-ordered labs FIRST, 2) Other labs chronologically (newest first)]

**FORMATTING RULES:**
[Date]: (include timestamp if multiple lab draws on same date)

FOR NORMAL VALUES:
- [Lab name]: [Value] [Units]

FOR ABNORMAL VALUES:
- [Lab name]: [Value] [Units] (Reference: [low-high] [units])

**IMPORTANT:** 
- ONLY include reference ranges when values are outside normal limits
- Reference ranges must show the actual numeric range (e.g., "Reference: 3.5-5.0 mmol/L")
- Do NOT write just "(low)" or "(elevated)" without the numeric reference range
- If source records lack reference ranges, use standard adult reference ranges and label as "Reference: [range] (standard)"

**CORRECT EXAMPLES:**

Laboratory (12/19/2025):
- WBC: 8.4 K/mcL
- Hemoglobin: 12.5 g/dL
- Sodium: 138 mmol/L
- Potassium: 3.6 mmol/L
- Creatinine: 0.49 mg/dL (Reference: 0.6-1.2 mg/dL)

Admission Labs (12/04/2025):
- WBC: 17.9 K/mcL (Reference: 4.0-11.0 K/mcL)
- Hemoglobin: 11.5 g/dL (Reference: 12.0-16.0 g/dL)
- Sodium: 135 mmol/L (Reference: 136-145 mmol/L)
- Potassium: 3.4 mmol/L (Reference: 3.5-5.0 mmol/L)
- Magnesium: 1.4 mg/dL (Reference: 1.7-2.2 mg/dL)
- Glucose: 116 mg/dL (Reference: 70-100 mg/dL fasting)
- Lactic acid: 2.9 mmol/L (Reference: 0.5-2.2 mmol/L)

**WRONG EXAMPLES (DO NOT DO THIS):**
- Creatinine: 0.49 mg/dL (low) NO - Must include numeric range
- WBC: 17.9 K/mcL (elevated) NO - Must include numeric range
- Sodium: 138 mmol/L (Reference: 136-145 mmol/L) NO - This is normal, don't include range.

Imaging:
[Order: 1) Neurology-requested imaging FIRST, 2) Other imaging chronologically (newest first)]
- [Study type] [Date]: Impression: [Impression only – do NOT include the full Findings text, only the summarized Impression relevant to neurology]

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
[Present neurological diagnoses first, only chart-supported diagnoses]
- No spacing between diagnoses or points.
- Use only hyphenated lists.

PLAN

-Present the plan recommended by the healthcare providers in a clear, numbered format.
[prioritize Present neurological plan and management first, supported by chart data].
- Do NOT repeat information within this section - each point should be unique and distinct.
- Do NOT categorize the information and Do NOT add disposition details.
---
CONSULTATION INFORMATION
- Attending Physician: [Name]
- Consulting Neurologist: [Name]
*[Date/Time]*


FORMATTING:
- Full sentences for HPI
- Bullet points allowed in other sections
- One blank line between major sections
- No unnecessary spacing
- Clean, clinical, consistent
- Do NOT use hash symbols or asterisks for section headers or emphasis
- Do NOT add a separate "Disposition" section or any final "Disposition" statement; end after the CONSULTATION INFORMATION section

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def soap_template(full_text: str) -> dict:
    """
    Generate SOAP template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a medical professional creating a comprehensive SOAP note from raw clinical data.

Generate a complete SOAP note with four distinct sections:
- SUBJECTIVE: Patient-reported information, symptoms, concerns, history of present illness
- OBJECTIVE: Clinical observations, vital signs, exam findings, test results, imaging
- ASSESSMENT: Clinical evaluation, diagnoses, differential diagnoses, clinical reasoning
- PLAN: Treatment recommendations, medications, procedures, follow-up instructions

CRITICAL REQUIREMENTS:
- Use ONLY information from the source records
- No assumptions or invented data
- Clear section headers (SUBJECTIVE, OBJECTIVE, ASSESSMENT, PLAN)
- Organized, professional medical documentation format
- Plain text output suitable for clinical use
- Strictly factual clinical documentation
- Include all relevant clinical details without omission
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
"""

    prompt = f"""Create a comprehensive SOAP note from this clinical data.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- Strictly factual clinical documentation
- Include all relevant clinical information
- Format with clear section headers

Format the output with clear section headers:

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Admission Date: [Date]
- Consultation Date: [Date of Service]
- Location: [Facility/Unit]
- Provider: [Attending/Consulting Physician]

SUBJECTIVE
[Chief complaint, history of present illness, patient-reported symptoms, pain assessment, functional status, review of systems, pertinent past medical history, current medications, allergies, social history relevant to current condition]

OBJECTIVE
Vital Signs: [Temperature, BP, HR, RR, O2 saturation, weight, BMI]
Physical Examination: [General appearance, systematic exam findings by body system]
Laboratory Results: [Recent lab values with dates]
Imaging Studies: [Radiology findings, dates performed]
Diagnostic Tests: [EKG, pulmonary function, other diagnostic results]
Current Medications: [Active medication list with dosages]

ASSESSMENT
Primary Diagnosis: [Main diagnosis with ICD code if available]
Secondary Diagnoses: [Additional diagnoses]
Clinical Summary: [Clinical reasoning, severity assessment, disease progression, response to treatment]
Differential Diagnoses Considered: [Alternative diagnoses ruled out or under consideration]

PLAN
Diagnostic Plan: [Further testing, monitoring needed]
Therapeutic Plan: [Medications with dosing, procedures, interventions]
Follow-up: [Appointments, timeframe, monitoring parameters]
Patient Education: [Instructions provided to patient]
Disposition: [Admit, discharge, transfer plans]
Code Status: [If documented]



Use only information from the provided clinical data. Do not add assumptions or invented information.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }


def discharge_summary_template(full_text: str) -> dict:
    """
    Generate discharge summary template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a medical professional creating a comprehensive discharge summary from clinical records.

Generate a complete discharge summary documenting the patient's hospital course:
- Hospital course from admission through discharge
- All diagnoses, procedures, and treatments provided
- Discharge medications and instructions
- Follow-up care requirements

CRITICAL REQUIREMENTS:
- Use ONLY information from the source records
- No assumptions or invented data
- Chronological presentation of hospital course
- Complete medication reconciliation
- Clear discharge instructions
- Professional medical documentation format
- Strictly factual clinical documentation
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
"""

    prompt = f"""Create a comprehensive discharge summary from this clinical data.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- Strictly factual clinical documentation
- Include complete hospital course timeline
- Format with clear section headers

Format the output with clear section headers:

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Admission Date: [Date]
- Discharge Date: [Date]
- Length of Stay: [Days]
- Attending Physician: [Name]
- Facility: [Hospital/Unit]

ADMISSION INFORMATION
Chief Complaint: [Reason for admission]
Admitting Diagnosis: [Primary diagnosis on admission]

HOSPITAL COURSE
[Chronological narrative of patient's hospitalization including: daily progress, significant events, complications, consultations obtained, procedures performed, response to treatment, clinical improvement or deterioration]

DISCHARGE DIAGNOSES
Primary Diagnosis: [Main diagnosis]
Secondary Diagnoses: [Additional diagnoses numbered/listed]
Complications: [Any complications during stay]

PROCEDURES PERFORMED
[List all procedures with dates: surgeries, interventions, diagnostic procedures]

SIGNIFICANT FINDINGS
Laboratory: [Key lab results and trends]
Imaging: [Important imaging findings]
Pathology: [Biopsy or surgical pathology results if applicable]
Cultures: [Microbiology results if applicable]

HOSPITAL MEDICATIONS
[Medications administered during hospitalization with significant changes noted]

DISCHARGE MEDICATIONS
[Complete list with: medication name, dosage, frequency, route, duration, indication]
New Medications: [Specifically note new prescriptions]
Changed Medications: [Dosage adjustments or modifications]
Discontinued Medications: [Medications stopped and why]

DISCHARGE CONDITION
[Patient's condition at discharge: stable, improved, resolved symptoms, functional status, mobility, mental status]

DISCHARGE DISPOSITION
[Home, home with services, skilled nursing facility, rehabilitation facility, transfer to another facility]

DISCHARGE INSTRUCTIONS
Activity: [Activity restrictions or recommendations]
Diet: [Dietary instructions or restrictions]
Wound Care: [If applicable]
Equipment Needs: [DME, oxygen, etc.]
Restrictions: [Driving, work, lifting restrictions]

FOLLOW-UP CARE
Appointments: [Provider, specialty, timeframe]
Monitoring: [Labs to be drawn, vital signs to monitor, symptoms to watch]
Warning Signs: [When to seek emergency care or call physician]
Pending Results: [Tests pending at discharge that need follow-up]

PATIENT EDUCATION
[Topics discussed with patient/family, educational materials provided, understanding verified]



Use only information from the provided clinical data. Do not add assumptions or invented information.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def procedure_note_template(full_text: str) -> dict:
    """
    Generate procedure note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a medical professional documenting a procedure note.

Generate a complete procedure note documenting:
- Indication and consent for procedure
- Technique and equipment used
- Step-by-step procedure details
- Findings and any complications
- Patient tolerance and post-procedure plan

CRITICAL REQUIREMENTS:
- Use ONLY information from the source records
- No assumptions or invented data
- Detailed procedure description
- Document all findings and complications
- Clear post-procedure instructions
- Professional medical documentation format
- Strictly factual clinical documentation
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
"""

    prompt = f"""Create a comprehensive procedure note from this clinical data.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- Strictly factual clinical documentation
- Include all procedural details
- Format with clear section headers

Format the output with clear section headers:

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Location: [Procedure location]
- Date of Procedure: [Date and time]

PROCEDURE PERFORMED
[Full name of procedure(s) with CPT codes if available]

OPERATORS
Primary Operator: [Physician name]
Assistants: [Names of assisting personnel]
Anesthesia Provider: [Name if applicable]

INDICATION
[Clinical indication for procedure, relevant history, diagnostic findings leading to procedure]

PRE-PROCEDURE INFORMATION
Diagnosis: [Pre-procedure diagnosis]
Allergies: [Known allergies]
Anticoagulation Status: [INR, antiplatelet agents, timing of last dose]
NPO Status: [Time of last oral intake]
Pre-procedure Vital Signs: [BP, HR, RR, O2 sat]
Pre-procedure Medications: [Medications given before procedure]

CONSENT
[Documentation that informed consent was obtained, risks/benefits discussed]

ANESTHESIA/SEDATION
Type: [Local, moderate sedation, general anesthesia]
Agents Used: [Medications and doses]
Monitoring: [ASA classification, monitoring used]

PROCEDURE DETAILS
Position: [Patient positioning]
Preparation: [Skin prep, sterile technique, draping]
Equipment: [Specific instruments, devices, catheters used with sizes]
Technique: [Step-by-step description of procedure performed, anatomical approach, landmarks identified, technical details]
Fluoroscopy Time: [If applicable]
Contrast Used: [Type and amount if applicable]

FINDINGS
[Detailed description of procedure findings, anatomical observations, pathology identified, measurements, visual findings]

SPECIMENS
[Specimens obtained, sent for pathology/culture, labeling]

COMPLICATIONS
[Any complications during procedure or state "None"]
Estimated Blood Loss: [Amount]

HEMOSTASIS
[Method of achieving hemostasis]

DEVICE/IMPLANT INFORMATION
[Any devices implanted with manufacturer, model, serial numbers, lot numbers]

POST-PROCEDURE INFORMATION
Patient Tolerance: [How patient tolerated procedure]
Post-procedure Vital Signs: [BP, HR, RR, O2 sat]
Immediate Post-procedure Condition: [Patient status]
Dressings Applied: [Type and location]

POST-PROCEDURE DIAGNOSIS
[Diagnosis after procedure completed]

POST-PROCEDURE PLAN
Monitoring: [Vitals, neuro checks, other monitoring]
Activity: [Bed rest, ambulation restrictions]
Diet: [NPO, clear liquids, etc.]
Medications: [Post-procedure medications, pain control]
Follow-up Imaging: [If needed]
Complications to Monitor For: [Specific complications to watch]
Follow-up: [When to follow up, with whom]
Pathology/Lab Follow-up: [Pending results to follow up]

DISPOSITION
[Disposition after procedure: to recovery, to floor, to ICU, discharged]



Use only information from the provided clinical data. Do not add assumptions or invented information.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }


def ed_note_template(full_text: str) -> dict:
    """
    Generate Emergency Department note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are an emergency medicine physician creating a comprehensive ED note.

Generate a complete Emergency Department note documenting:
- Chief complaint and presenting symptoms
- Emergency assessment and workup
- Treatment provided in the ED
- Disposition and follow-up plan

CRITICAL REQUIREMENTS:
- Use ONLY information from the source records
- No assumptions or invented data
- Document triage and acuity level
- Time-stamped interventions
- Clear disposition and follow-up
- Professional medical documentation format
- Strictly factual clinical documentation
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
"""

    prompt = f"""Create a comprehensive Emergency Department note from this clinical data.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- Strictly factual clinical documentation
- Include timeline of ED course
- Format with clear section headers

Format the output with clear section headers:

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Arrival Date/Time: [Date and time]
- ED Physician: [Attending name]
- Facility: [Hospital ED]

TRIAGE INFORMATION
Arrival Time: [Time]
Triage Acuity: [ESI level 1-5 or other triage system]
Arrival Mode: [Ambulatory, wheelchair, ambulance, police]
Chief Complaint: [Brief statement]

HISTORY OF PRESENT ILLNESS
[Detailed narrative of current illness/injury including: onset, duration, character, aggravating/alleviating factors, associated symptoms, prior treatments attempted, reason for ED visit today]

Past Medical History: [Relevant chronic conditions]
Past Surgical History: [Relevant surgeries]
Medications: [Home medications]
Allergies: [Drug allergies and reactions]
Social History: [Smoking, alcohol, drug use]
Family History: [Relevant for acute presentation]

REVIEW OF SYSTEMS
- Constitutional: [Fever, chills, weight loss]
- Cardiovascular: [Chest pain, palpitations]
- Respiratory: [Dyspnea, cough]
- Gastrointestinal: [Nausea, vomiting, diarrhea, abdominal pain]
- Genitourinary: [Dysuria, hematuria]
- Neurological: [Headache, weakness, numbness]
- [Other pertinent systems]

PHYSICAL EXAMINATION
- Time of Examination: [Time]
- Vital Signs: [Temp, BP, HR, RR, O2 sat, pain score]
- General: [Appearance, distress level, mental status]
- HEENT: [Head, eyes, ears, nose, throat examination]
- Neck: [Examination findings]
- Cardiovascular: [Heart examination]
- Respiratory: [Lung examination]
- Abdomen: [Abdominal examination]
- Extremities: [Examination of extremities]
Neurological: [Mental status, cranial nerves, motor, sensory, reflexes, gait, coordination]
Skin: [Rashes, wounds, color]
Psychiatric: [Mood, affect, behavior if relevant]

DIAGNOSTIC STUDIES
Laboratory Results:
[Lab test name: result (normal range) - time obtained]

Imaging Studies:
[Study type, time performed, findings, radiologist interpretation]

EKG:
[Time performed, rate, rhythm, intervals, findings]

Other Diagnostics:
[Point of care testing, other studies]

ED COURSE/TREATMENT
[Chronological narrative of patient's ED stay including: interventions performed, medications administered with times and doses, procedures done, consultations obtained, patient's response to treatment, clinical decision-making]

Interventions Timeline:
[Time - Intervention/medication/procedure]

CONSULTATIONS
[Specialty consulted, time contacted, recommendations provided]

MEDICAL DECISION MAKING
Differential Diagnoses Considered: [List]
Risk Stratification: [Assessment of patient risk]
Clinical Reasoning: [Why certain diagnoses ruled in or out]
Complexity: [Factors contributing to medical decision making]

EMERGENCY DEPARTMENT DIAGNOSIS
Primary: [Main ED diagnosis]
Secondary: [Additional diagnoses]

DISPOSITION
Disposition: [Discharge home, admit to hospital, transfer, left against medical advice, observation]
Disposition Time: [Time]
Condition at Discharge: [Stable, improved, unchanged]
Admitting Service: [If admitted - which service]
Admitting Diagnosis: [If admitted]

DISCHARGE INSTRUCTIONS (if discharged)
Activity: [Activity level, restrictions]
Diet: [Dietary instructions]
Medications: [Prescriptions given - name, dose, frequency, duration, indication]
Wound Care: [If applicable]
Follow-up: [Who to follow up with and timeframe]
Return Precautions: [Specific symptoms that should prompt return to ED]
Work/School: [Return to work/school instructions]
Understanding: [Patient verbalized understanding]

PRESCRIPTIONS PROVIDED
[Medication name, strength, quantity, directions, refills]

PATIENT EDUCATION
[Topics discussed, instructions given, written materials provided]



Use only information from the provided clinical data. Do not add assumptions or invented information.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }


def generic_note_template(full_text: str) -> dict:
    """
    Generate generic clinical note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a medical professional creating a comprehensive clinical note from medical records.

Generate a complete clinical note that appropriately documents:
- Patient information and encounter details
- Clinical findings and assessment
- Medical decision-making
- Plan of care

CRITICAL REQUIREMENTS:
- Use ONLY information from the source records
- No assumptions or invented data
- Adapt structure to available information
- Include all relevant clinical details
- Professional medical documentation format
- Strictly factual clinical documentation
- Organize information logically
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
- **CRITICAL**: OUTPUT MUST NOT CONTAIN HASH OR ASTERISK SYMBOLS
"""

    prompt = f"""Create a comprehensive clinical note from this clinical data.

CRITICAL RULES:
- Use ONLY information from the provided source records
- No assumptions, no invented data
- Strictly factual clinical documentation
- Adapt structure based on available information
- Format with clear section headers

Format the output with clear section headers (include only sections with available information):

PATIENT INFORMATION
- Name: [Patient Name]
- MRN: [Medical Record Number]
- CSN: [Contact Serial Number / FIN]
- DOB: [Date of Birth]
- Age: [Age]
- Sex: [Sex]
- Date of Service: [Date]
- Provider: [Physician name]
- Location: [Facility/clinic/unit]
- Encounter Type: [Office visit, progress note, follow-up, etc.]

CHIEF COMPLAINT
[Primary reason for encounter]

HISTORY OF PRESENT ILLNESS
[Detailed narrative of current medical issue, onset, duration, symptoms, prior treatments, progression]

PAST MEDICAL HISTORY
[Chronic conditions, significant past illnesses]

PAST SURGICAL HISTORY
[Previous surgeries with dates if available]

CURRENT MEDICATIONS
[Medication list with dosages]

ALLERGIES
[Drug allergies and reactions]

SOCIAL HISTORY
[Smoking, alcohol, drug use, occupation, living situation]

FAMILY HISTORY
[Relevant hereditary conditions]

REVIEW OF SYSTEMS
[Systematic review by body system - include pertinent positives and negatives]

PHYSICAL EXAMINATION
Vital Signs: [Temperature, BP, HR, RR, O2 saturation, weight, BMI, pain score]
General: [Overall appearance, mental status]
[System-based examination findings]

DIAGNOSTIC DATA
Laboratory: [Lab results with dates and values]
Imaging: [Imaging studies with findings]
Other Tests: [EKG, pulmonary function, other diagnostics]

ASSESSMENT
[Clinical evaluation, diagnoses numbered/listed, clinical reasoning, severity assessment]

Primary Diagnosis: [Main diagnosis]
Secondary Diagnoses: [Additional diagnoses]
Clinical Impression: [Overall assessment]

PLAN
[Detailed plan organized by problem or system]

Diagnostic: [Further testing ordered, monitoring needed]
Therapeutic: [Medications, procedures, treatments with specific details]
Education: [Patient counseling provided]
Follow-up: [When and with whom]
Referrals: [Specialists to see]
Preventive Care: [Screenings, immunizations]

PATIENT INSTRUCTIONS
[Specific instructions given to patient]

TIME SPENT
[Total encounter time and time spent on counseling/coordination if documented]

Use only information from the provided clinical data. Do not add assumptions or invented information. Adapt the note structure based on what information is available in the source records.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def notes_digest_template(full_text: str) -> dict:
    """
    Generate notes digest template with system and user prompts.

    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are a consultant preparing a notes digest. Follow the template provided strictly.

CRITICAL REQUIREMENTS:
- Use ONLY information from the source records
- No assumptions or invented data
- Strictly factual clinical documentation
- PATIENT NAME EXTRACTION: Look for patient name in headers, patient information sections, or anywhere it appears in the medical record. Common patterns include "Patient Name:", "Name:", or patient identification sections.

Output the complete notes digest in the exact JSON format specified. Return ONLY valid JSON - no additional text, explanations, or formatting.
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
"""

    prompt = f"""You are processing medical records to create a comprehensive patient digest in JSON format matching the PreVisitBrief interface.

Extract and structure ALL information into the following JSON structure:

{{
  "cpt": {{
    "content": ""
  }},
  "lab": {{
    "content": [
      {{
        "test_name": "Name of laboratory test",
        "test_code": "Lab code if mentioned",
        "date": "Date of the test",
        "value": "Test result value with units and flags (e.g., '11.0 (L)', '37 (H)')",
        "reason": "Clinical indication for ordering the test",
        "timing": "When test should be completed",
        "follow_up_instructions": "Any special instructions for the test",
        "uom": "Unit of measure"
      }}
    ]
  }},
  "plan": {{
    "content": ""
  }},
  "vitals": {{
    "content": ""
  }},
  "allergies": {{
    "content": ""
  }},
  "red_flags": {{
    "content": ""
  }},
  "impression": {{
    "content": ""
  }},
  "medications": {{
    "past": [
      {{
        "medication_name": "Generic and/or brand name",
        "dosage": "Strength and amount",
        "route": "What is the route? ex: Oral, Topical, Injection etc",
        "frequency": "How often to take",
        "duration": "Length of treatment",
        "quantity": "Number of pills/refills",
        "instructions": "Special instructions (with food, etc.)",
        "indication": "What condition this treats",
        "formatted_prescription": "Brand/Generic name with strength, route, timing pattern (duration) - e.g., 'Amlopres 5 mg tab Oral, 0-0-1 (for 30 days)'",
        "sig_format": "Standard pharmacy SIG format - e.g., 'Take 1 tablet by mouth once daily at bedtime for 30 days'"
      }}
    ],
    "current": [
      {{
        "medication_name": "Generic and/or brand name",
        "dosage": "Strength and amount",
        "route": "What is the route? ex: Oral, Topical, Injection etc",
        "frequency": "How often to take",
        "duration": "Length of treatment",
        "quantity": "Number of pills/refills",
        "instructions": "Special instructions (with food, etc.)",
        "indication": "What condition this treats",
        "formatted_prescription": "Brand/Generic name with strength, route, timing pattern (duration) - e.g., 'Amlopres 5 mg tab Oral, 0-0-1 (for 30 days)'",
        "sig_format": "Standard pharmacy SIG format - e.g., 'Take 1 tablet by mouth once daily at bedtime for 30 days'"
      }}
    ],
    "infusing": [
      {{
        "medication_name": "Generic and/or brand name",
        "dosage": "Strength and amount",
        "route": "What is the route? ex: Oral, Topical, Injection etc",
        "frequency": "How often to take",
        "duration": "Length of treatment",
        "quantity": "Number of pills/refills",
        "instructions": "Special instructions (with food, etc.)",
        "indication": "What condition this treats",
        "formatted_prescription": "Brand/Generic name with strength, route, timing pattern (duration) - e.g., 'Amlopres 5 mg tab Oral, 0-0-1 (for 30 days)'",
        "sig_format": "Standard pharmacy SIG format - e.g., 'Take 1 tablet by mouth once daily at bedtime for 30 days'"
      }}
    ],
    "PRN": [
      {{
        "medication_name": "Generic and/or brand name",
        "dosage": "Strength and amount",
        "route": "What is the route? ex: Oral, Topical, Injection etc",
        "frequency": "How often to take",
        "duration": "Length of treatment",
        "quantity": "Number of pills/refills",
        "instructions": "Special instructions (with food, etc.)",
        "indication": "What condition this treats",
        "formatted_prescription": "Brand/Generic name with strength, route, timing pattern (duration) - e.g., 'Amlopres 5 mg tab Oral, 0-0-1 (for 30 days)'",
        "sig_format": "Standard pharmacy SIG format - e.g., 'Take 1 tablet by mouth once daily at bedtime for 30 days'"
      }}
    ]
  }},
  "demographics": {{
    "patientName": "[patient Full Name]",
    "mrn": "[MRN Value]",
    "age": "[Age]",
    "sex": "[Male/Female]",
    "dateofbirth": "[MM/DD/YYYY]",
    "dateofadmission": "[MM/DD/YYYY or No relevant information on file]",
    "dateofdischarge": "[MM/DD/YYYY or No relevant information on file]",
    "dateofservice": "[MM/DD/YYYY]",
    "CSN_FIN": "[Value]"
  }},
  "service_details":{{
    "consultant_name": "[Name, Credentials]",
    "department": "[Department/Specialty]",
    "signature_information": "[Signer, Date/Time]",
    "practice_name": "[Practice Name]",
    "location":"[Location]",
    "contact_information": "[Phone/Fax]",
    "additional_providers": "[List of names/roles]",
    "attending_details": "[Name, Contact]",
    "pcp_details": "[Name, Contact]"
  }},
  "identifiers": {{
    "content": ""
  }},
  "overview": {{
    "content": ""
  }},
  "chief_complaint": {{
    "content": ""
  }},
  "history_of_present_illness": {{
    "content": ""
  }},
  "past_medical_history": {{
    "content": ""
  }},
  "surgical_history": {{
    "content": ""
  }},
  "family_history": {{
    "content": ""
  }},
  "social_history": {{
    "content": ""
  }},
  "review_of_systems": {{
    "content": ""
  }},
  "physical_exam": {{
    "content": ""
  }},
  "secondary_diagnoses": {{
    "content": ""
  }},
  "differential_diagnoses": {{
    "content": ""
  }},
  "comorbidities": {{
    "content": ""
  }},
  "procedures": {{
    "content": ""
  }},
  "clinical_timeline": {{
    "content": ""
  }},
  "clinical_course": {{
    "content": ""
  }},
  "care_coordination": {{
    "content": ""
  }},
  "risk_assessment": {{
    "content": ""
  }},
  "continuity_recommendations": {{
    "content": ""
  }},
  "follow_up": {{
    "content": ""
  }}
}}

Field descriptions:
- cpt: Current Procedural Terminology codes and procedures performed. Include ALL procedures, imaging studies, and diagnostic tests mentioned (EEG, CT, MRI, Echo, Duplex, etc.). Extract every procedure and study mentioned in the "Studies" section or elsewhere in the note.
- lab: Laboratory test results, imaging studies, and diagnostic tests. Format as an array of objects with: test_name, test_code (if mentioned), date (date of the test), value (test result with units and flags like H/L), reason (clinical indication for ordering), timing (when test should be completed), follow_up_instructions (special instructions). Extract ALL lab tests mentioned in the record.
- plan: Treatment plan, follow-up recommendations, and care plan
- vitals: Vital signs including blood pressure, heart rate, temperature, respiratory rate, oxygen saturation, weight, height, BMI
- allergies: All known allergies and adverse reactions
- red_flags: Critical findings, warning signs, or urgent concerns that require immediate attention
- impression: Clinical impression, assessment, and diagnostic conclusions
- medications: Medications organized by status with four arrays: "past" (past medications), "current" (current/scheduled medications), "infusing" (medications being infused), and "PRN" (as-needed medications). Each medication object contains: medication_name (generic/brand), dosage (strength and amount), route (Oral, Topical, Injection, Ophthalmic, etc.), frequency (how often - e.g., Daily, BID, q6h, q8h), duration (length of treatment if mentioned), quantity (number of pills/refills if mentioned), instructions (special instructions like with food, Both Eyes, etc.), indication (what condition it treats if mentioned), formatted_prescription (e.g., 'Amlopres 5 mg tab Oral, 0-0-1 (for 30 days)'), sig_format (standard pharmacy SIG format, e.g., 'Take 1 tablet by mouth once daily at bedtime for 30 days'). Extract ALL medications mentioned in the record. Include all available information for each medication.
- demographics: Patient demographics including name, age, gender, date of birth, MRN, and other identifiers. CRITICAL: Extract the patient's full name from the medical record - look for "Patient Name:", "Name:", patient headers, or identification sections. If patient name is clearly stated anywhere in the record, include it in the Patientname field.
- identifiers: Medical record numbers, patient IDs (CSN/FIN), and other identifying information (optional). If CSN is present, use it; else if FIN is present, use FIN; else leave empty.
- overview: Overall patient summary and key highlights (optional)
- chief_complaint: Primary reason for visit or chief complaint
- history_of_present_illness: Detailed history of the current illness or presenting problem
- past_medical_history: Past medical conditions, chronic diseases, and medical history
- surgical_history: Past surgical procedures, dates, and outcomes
- family_history: Family medical history and hereditary conditions
- social_history: Social history including smoking, alcohol, substance use, occupation, living situation
- review_of_systems: Review of systems findings
- physical_exam: Physical examination findings and observations
- secondary_diagnoses: Secondary or additional diagnoses (optional)
- differential_diagnoses: Differential diagnoses being considered (optional)
- comorbidities: Comorbid conditions and their relationships (optional)
- procedures: Procedures performed, dates, outcomes, and complications (optional)
- clinical_timeline: Chronological timeline of clinical events and visits (optional)
- clinical_course: Overall clinical course, improvements, complications, response to treatment (optional)
- care_coordination: Consultations, specialists involved, care transitions (optional)
- risk_assessment: Identified risks, monitoring needs, preventive measures (optional)
- continuity_recommendations: Critical information for continuity of care, monitoring parameters, follow-up actions (optional)
- follow_up: Follow-up appointments, specialty referrals, timeframes, and purposes (optional)

Extract ALL relevant information from the medical records into the appropriate fields. Be comprehensive and accurate.

CRITICAL: You MUST extract EVERY SINGLE medication and EVERY SINGLE lab test mentioned in the record. Do not skip any. Count them carefully.

For medications and lab fields:
- medications: Organize medications into four arrays based on their status: "past" (past medications), "current" (current/scheduled medications), "infusing" (medications being infused), and "PRN" (as-needed medications). Extract EACH AND EVERY medication as a separate object in the appropriate array. If a medication list says "Scheduled" or "Current medications", extract ALL of them into the "current" array. If it says "PRN", extract ALL of them into the "PRN" array. Include ALL available information for each medication (medication_name, dosage, route, frequency, duration if mentioned, quantity if mentioned, instructions, indication if mentioned, formatted_prescription, sig_format). Do not skip any medications - if you see 12 medications listed, extract all 12. If no medications are found for a particular status, use an empty array [] for that status.
- lab: Extract EACH AND EVERY lab test as a separate object in the "content" array. If you see a lab results table with multiple rows, extract EVERY row. If lab results are mentioned in narrative text, extract those too. Include ALL available information for each test (test_name, test_code if mentioned, date, value with units and flags, reason if mentioned, timing if mentioned, follow_up_instructions if mentioned). Do not skip any lab tests - if you see 20+ lab tests mentioned, extract all 20+. Extract all lab results mentioned in tables, lists, and narrative text. If no lab tests are found, use an empty array [].

For all other fields, provide a clear, well-formatted text summary in the "content" field.

Field inclusion rules:
- Required fields (cpt, lab, plan, vitals, allergies, red_flags, impression, medications, demographics, chief_complaint, history_of_present_illness, past_medical_history, surgical_history, family_history, social_history, review_of_systems, physical_exam): Always include, use empty string "" if no information available (for medications, always include all four arrays: "past", "current", "infusing", and "PRN", using empty array [] for each status with no medications; for lab, use empty array [] if no information available)
- Optional fields (identifiers, overview, secondary_diagnoses, differential_diagnoses, comorbidities, procedures, clinical_timeline, clinical_course, care_coordination, risk_assessment, continuity_recommendations, follow_up): Only include if relevant information exists, otherwise omit the field entirely from the JSON output

IMPORTANT: Tag ONLY specific values, findings, or measurements that are medically important - NOT entire sentences or paragraphs.

### Tagging Schema:

Use XML-like tags with an 'alert' attribute for INDIVIDUAL VALUES ONLY:

<diagnosis alert="High/Medium"> → Specific diagnosis name only
<symptom alert="High/Medium/Low"> → Specific symptom only
<vitals alert="High/Medium"> → Individual vital sign VALUE only (e.g., just the number)
<lab alert="High/Medium"> → Individual lab VALUE only (e.g., just the result)
<medication alert="Low"> → Specific medication name only
<procedure alert="Medium"> → Specific procedure name only
<allergy alert="High"> → Specific allergen only

### Alert Level Rules:

- High → Abnormal/critical values, life-threatening conditions, urgent findings
- Medium → Moderately abnormal values, important chronic conditions
- Low → Normal values mentioned for context, routine information

### Tagging Rules - CRITICAL:

1. Tag ONLY the specific value, measurement, or finding - NOT the label or entire phrase
2. DO NOT tag normal values unless they're clinically significant in context
3. For labs: Tag only abnormal values with their numbers
4. For vitals: Tag only abnormal readings with their numbers
5. Keep surrounding text untagged for readability

### Lab and Vital Formatting Rules:

When tagging lab or vital information:
- Always write them in the format: *ComponentName Value Unit*
- If the component name is missing, infer it from context
- Preserve the original unit (mg/dL, mmHg, %, etc.)
- Example: <lab alert="High">Total Cholesterol 245 mg/dL</lab>
- Example: <vitals alert="High">Blood Pressure 180/110 mmHg</vitals>
- Example: <lab alert="High">HDL 38 mg/dL</lab>

### Examples:

CORRECT:
- Total Cholesterol: <lab alert="High">Total Cholesterol 245 mg/dL</lab> (High)
- HDL: <lab alert="High">HDL 38 mg/dL</lab> (Low)
- BP: <vitals alert="High">Blood Pressure 180/110 mmHg</vitals>
- Patient has <diagnosis alert="High">ST elevation</diagnosis>
- <symptom alert="High">Chest pain</symptom> and shortness of breath
- Prescribed <medication alert="Low">aspirin</medication>
- Risk of <diagnosis alert="Medium">stroke progression</diagnosis>
- Heart Rate: <vitals alert="Medium">Heart Rate 104 bpm</vitals>

INCORRECT:
- <lab alert="High">Total Cholesterol: 245 mg/dL (High)</lab> (includes colon and extra text)
- <lab alert="High">245 mg/dL</lab> (missing component name)
- <vitals alert="Medium">BP: 104/66</vitals> (this is normal, don't tag)
- <vitals alert="High">180/110 mmHg</vitals> (missing component name)
- <diagnosis alert="High">1. Slurred speech with worsening right-sided weakness</diagnosis>
- <plan alert="Low">- Telemetry monitoring\n- Neurochecks</plan>

### Content Formatting:

Write naturally flowing text with tags embedded inline around specific values only. Do not create lists of tagged items. Tag values where they appear in natural sentences and clinical descriptions.

Example format:
"Patient presents with <symptom alert="High">chest pain</symptom>. Blood pressure was <vitals alert="High">Blood Pressure 180/110 mmHg</vitals>. Lab results show <lab alert="High">Total Cholesterol 245 mg/dL</lab> and <lab alert="High">HDL 38 mg/dL</lab>. Diagnosed with <diagnosis alert="High">ST elevation MI</diagnosis>. Started on <medication alert="Low">aspirin</medication> and <medication alert="Low">atorvastatin</medication>."

Output ONLY valid JSON with no additional text, no markdown, no code blocks.
Do NOT wrap the JSON in ```json``` or ``` code blocks.
Start directly with {{ and end directly with }}.
Return raw JSON only.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }

def op_follow_up_visit_template(full_text: str) -> dict:
    """
    Generate outpatient follow-up visit note template with system and user prompts.
    
    Args:
        full_text: The medical note content to process
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
    """
    system_prompt = """You are preparing a formal OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE.

CRITICAL REQUIREMENTS:
- Follow the exact structure provided in the template
- Use ONLY information from the source records
- No assumptions or invented data
- Preserve all dates and timestamps exactly as they appear in source documents
- Use appropriate medical terminology and abbreviations
- Ensure chronological accuracy throughout the document
- NEVER fabricate or infer information not present in the provided records
- If information for a required section is not available, omit that section entirely
- Use clear section headers as specified
- Maintain consistent date format: MM-DD-YYYY for specific dates; MM-YYYY if day unknown; YYYY if only year known
- Always include at least month and year for all events
- Include timestamps HH:MM AM/PM when available
- Use only hyphenated lists where lists are required
- Preserve exact attribution from source - never change who said/did/reported something
- Maintain cautious medical language - keep hedging phrases like "supportive of," "consistent with," "appears to be" exactly as stated
- Keep patient voice - maintain "she says," "he reports," "patient feels" as stated in source
- CRITICAL FORMATTING: Do NOT use any asterisks, hashtags, or markdown formatting symbols in the output
- Do NOT use bold, italics, or any text emphasis markers
- Use only plain text with hyphenated lists

Output the complete outpatient follow-up visit note in the exact format specified.
- **CSN/FIN Extraction**: If "CSN" is present in the source record, include it. If "CSN" is missing but "FIN" is present, use its value. If neither is found, omit the field.
"""

    prompt = f"""You are preparing a formal OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE.

CRITICAL FIRST STEP: INCONSISTENCY IDENTIFICATION REPORT (PRESENT BEFORE THE MEDICAL NOTE)

BEFORE generating the note, you MUST compare the latest note with all previous
information and identify any inconsistencies or conflicting details across these
three areas:

1. History of Presenting Illness (HPI)
2. Current Medications
3. Assessment and Plans

FORMAT FOR PRESENTING INCONSISTENCIES:

Inconsistency Identification Report
------------------------------------

HPI Inconsistencies:
- Conflict: [Describe the conflicting details and which documents/notes they appear in]
  Suggestion: [If a resolution can be identified from the provided information, state it here. Otherwise, flag for physician review.]

Current Medication Inconsistencies:
- Conflict: [Describe the conflicting details (e.g., dosage discrepancy, medication listed in one note but not another) and which documents/notes they appear in]
  Suggestion: [If a resolution can be identified from the provided information, state it here. Otherwise, flag for physician review.]

Assessment and Plan Inconsistencies:
- Conflict: [Describe conflicting details between assessment/plan entries across notes]
  Suggestion: [If a resolution can be identified from the provided information, state it here. Otherwise, flag for physician review.]

RULES FOR THIS SECTION:
- Present conflicts in an organised manner grouped by the three categories above
- If a solution/resolution is identifiable within the given information, present it as a suggestion alongside the conflict
- If no conflicts are found in a category, state: "No inconsistencies identified."
- This section appears BEFORE the medical note begins
- Do NOT include explanatory notes about how conflicts were resolved in the medical note itself; simply apply the resolution

After presenting the inconsistency report, resolve conflicts internally using the following priority before generating the note:
- HIGHEST PRIORITY: Information from the Assessment section (most recent clinical synthesis)
- SECOND PRIORITY: Most recent date-stamped information
- THIRD PRIORITY: Most specific/detailed information
- Attribution: NEVER change who said/did something - preserve exact attribution from source
- Cautious language: Keep hedging phrases like "supportive of," "consistent with," "appears to be" exactly as stated

State at the end of your inconsistency report: "Consistency analysis performed. Resolved [X] discrepancies. Applying resolutions to the note below."

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
"It was a pleasure to evaluate [Patient Name], a [Age] [Sex] at the [Location] in follow up.

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

"The following history sections were reviewed: Medical History, Social History, Family History and Allergies."

CRITICAL RULE: Do NOT include any details under Medical History, Social History, Family History, or Allergies unless that specific information is explicitly stated in the previous neurology outpatient note. If the previous neurology outpatient note does not contain these details, do not expand this section beyond the statement above.

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

All systems were reviewed and pertinent positives are included in the section on interim updates.

CRITICAL RULE: This section contains ONLY the statement above. Do NOT list individual systems, positive or negative findings, or any other details in this section. All pertinent positive findings are documented within the Interim Updates section.

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
[Document alert and oriented status (AAO x [number]) and whether the patient is in distress or not. Limit this section to these two elements only.]

Neurological Examination:

INSTRUCTION: Copy from the most recent note since neurological examination findings typically remain stable over extended periods.

Structure:
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
- Inconsistency Identification Report is presented before the medical note
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
- History section contains only the reviewed-sections statement unless details are in the previous neurology outpatient note
- Review of Systems contains only the single prescribed statement; pertinent positives are in Interim Updates
- General Examination is limited to AAO status and distress assessment only
- Case Summary opens with "It was a pleasure to evaluate [Patient Name], a [Age] [Sex] at the [Location] in follow up."
- Vitals section omits any undocumented measurements
- Medication changes integrated naturally into Interim Updates narrative without separate subsection

---
Begin your response with the Inconsistency Identification Report, followed by the medical note starting from "OUTPATIENT FOLLOW-UP VISIT MEDICAL NOTE." Populate all sections systematically following this exact structure.

Medical Note to Process:
{full_text}"""
    
    return {
        "system_prompt": system_prompt,
        "prompt": prompt
    }
# ============================================================================
# TEMPLATE REGISTRY - Maps note types to their template methods
# ============================================================================

NOTE_TEMPLATES = {
    "history_physical": history_physical_template,
    "progress_note": progress_note_template,
    "consultation_note": consultation_note_template,
    "discharge_summary": discharge_summary_template,
    "soap": soap_template,
    "procedure_note": procedure_note_template,
    "ed_note": ed_note_template,
    "generic_note": generic_note_template,
    "notes_digest": notes_digest_template,
    "op_follow_up_visit": op_follow_up_visit_template,

    # neurology department notes
    "neurology_progress_note": neurology_progress_note_template,
    "neurology_consultation_note": neurology_consultation_note_template,

    # IM department notes
    # "im_progress_note": im_progress_note_template,
    # "im_consultation_note": im_consultation_note_template
}


def get_note_template(note_type: str, medical_note_text: str) -> dict:
    """
    Get the template for a specific note type.
    
    Args:
        note_type: Type of note (progress_note, consultation_note, etc.)
        medical_note_text: The actual medical note content
        
    Returns:
        dict: {"system_prompt": str, "prompt": str}
        
    Example:
        config = get_note_template("progress_note", medical_text)
        # Use config["system_prompt"] and config["prompt"] to generate note
    """
    if note_type not in NOTE_TEMPLATES:
        raise ValueError(f"Unknown note type: {note_type}. Available types: {list(NOTE_TEMPLATES.keys())}")
    
    template_method = NOTE_TEMPLATES[note_type]
    return template_method(medical_note_text)