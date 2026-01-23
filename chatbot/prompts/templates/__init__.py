# Templates Package - Clinical Note Templates

"""
Templates package containing all clinical note templates.
Each template is in a separate file for maintainability.
"""

from prompts.templates.neurology_consult import NEUROLOGY_CONSULT_TEMPLATE
from prompts.templates.neurology_progress import NEUROLOGY_PROGRESS_TEMPLATE
from prompts.templates.soap_note import SOAP_NOTE_TEMPLATE
from prompts.templates.comprehensive_consult import COMPREHENSIVE_CONSULT_TEMPLATE
from prompts.templates.resident_attestation import RESIDENT_ATTESTATION_TEMPLATE
from prompts.templates.day_by_day_summary import DAY_BY_DAY_SUMMARY_TEMPLATE
from prompts.templates.op_followup_visit import OP_FOLLOWUP_VISIT_TEMPLATE

# Combine all templates into a single dictionary
patient_note_templates = {
    "neurology_consult": NEUROLOGY_CONSULT_TEMPLATE,
    "neurology_progress": NEUROLOGY_PROGRESS_TEMPLATE,
    "soap_note": SOAP_NOTE_TEMPLATE,
    "comprehensive_consult": COMPREHENSIVE_CONSULT_TEMPLATE,
    "resident_attestation": RESIDENT_ATTESTATION_TEMPLATE,
    "day_by_day_summary": DAY_BY_DAY_SUMMARY_TEMPLATE,
    "op_followup_visit": OP_FOLLOWUP_VISIT_TEMPLATE,
}

__all__ = [
    'patient_note_templates',
    'NEUROLOGY_CONSULT_TEMPLATE',
    'NEUROLOGY_PROGRESS_TEMPLATE',
    'SOAP_NOTE_TEMPLATE',
    'COMPREHENSIVE_CONSULT_TEMPLATE',
    'RESIDENT_ATTESTATION_TEMPLATE',
    'DAY_BY_DAY_SUMMARY_TEMPLATE',
    'OP_FOLLOWUP_VISIT_TEMPLATE',
]
