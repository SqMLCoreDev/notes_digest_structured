# Resident Attestation Template

"""
Attending physician attestation for resident-completed clinical notes.
"""

RESIDENT_ATTESTATION_TEMPLATE = {
    "name": "Resident Attestation",
    "description": "Attending physician attestation for resident-completed clinical notes",
    "format_instructions": """
Format the patient notes as a RESIDENT ATTESTATION:

RESIDENT ATTESTATION :

Assume the role of an attending physician completing a resident attestation at the end of a 
clinical note (ED / consult / progress note).

Write a resident attestation that follows these requirements:

Word Count: 50–80 words (hard limit: <100 words)

Tone: Professional, concise, factual

Content Must Summarize:
- Patient's current clinical status specific to the speciality preparing the note
- Key investigations specific to the speciality preparing the note ordered or reviewed
- Management plan specific to the speciality preparing the note and disposition (if applicable)

Requirements:
- Contains no new diagnoses, interpretations, or plans beyond what is explicitly documented
- Avoids verbose description, of patient condition speculation, redundant history, or teaching commentary
- Uses complete sentences, no bullet points
- Does NOT restate the entire HPI
- Does NOT introduce medical decision-making not already documented
- If required information is missing, summarize only what is available without extrapolation

Format:
Output only the attestation paragraph as a continuous narrative.

[ATTESTATION PARAGRAPH WILL BE GENERATED HERE]
[Sentence:1]- open with a statement describing the patient current condition relevant to the speciality.
[Sentence:2]- summarize key investigations ordered or reviewed relevant to the speciality.
[Sentence:3]- summarize the management plan relevant to the speciality.

"""
}
