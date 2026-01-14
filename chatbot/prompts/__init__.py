# Prompts Package - Modular Prompt Management
# prompts/__init__.py

"""
Prompts package for clinical note templates and dataset-specific prompts.

This module provides:
- patient_note_templates: Dictionary of clinical note formats
- prompts: Dictionary of index-specific prompts
- Helper functions for template selection and detection

Structure:
prompts/
├── __init__.py           # This file - exports and helpers
├── templates/            # Clinical note templates
│   ├── neurology_consult.py
│   ├── neurology_progress.py
│   ├── soap_note.py
│   ├── comprehensive_consult.py
│   ├── resident_attestation.py
│   └── day_by_day_summary.py
└── datasets/             # Index-specific prompts
    ├── processed_notes.py
    ├── processed_notes_json.py
    └── processed_notes_json_nested.py
"""

import re
from typing import Optional, Tuple, Dict

# Import templates
from prompts.templates import patient_note_templates

# Import dataset prompts
from prompts.datasets import prompts


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_template_options_text() -> str:
    """Generate formatted text of available templates for LLM to present to users."""
    options = []
    for idx, (key, template) in enumerate(patient_note_templates.items(), 1):
        options.append(f"  {idx}. {template['name']} - {template['description']}")
    return "\n".join(options)


def get_template_by_selection(selection: str) -> Optional[Dict]:
    """
    Get template by user selection (number or name).
    
    Args:
        selection: User's selection (number, key, or partial name)
        
    Returns:
        Template dict or None if not found
    """
    selection = selection.strip().lower()
    
    # Try by number
    if selection.isdigit():
        idx = int(selection) - 1
        keys = list(patient_note_templates.keys())
        if 0 <= idx < len(keys):
            return patient_note_templates[keys[idx]]
    
    # Try by key
    if selection in patient_note_templates:
        return patient_note_templates[selection]
    
    # Try by name (partial match)
    for key, template in patient_note_templates.items():
        if selection in template['name'].lower():
            return template
    
    return None


# ============================================================
# NOTE TEMPLATE DETECTION CONFIGURATION
# ============================================================

NOTE_TEMPLATE_TRIGGERS = {
    "note_keywords": [
        r'\bnotes?\b',
        r'\bclinical\s+notes?\b',
        r'\bprogress\s+notes?\b',
        r'\bsoap\s+notes?\b',
        r'\bconsult(?:ation)?\s+notes?\b',
        r'\bpatient\s+notes?\b',
        r'\bneurology\s+notes?\b',
    ],
    "patient_keywords": [
        r'\bpatient\b',
        r'\bpatient\s+name\b',
        r'\bpatient\s*id\b',
        r'\bmrn\b',
        r'\bmedical\s+record\b',
    ],
    "identifier_patterns": [
        r'^\s*\d{6,12}\s*$',
        r'^\s*[A-Z][a-z]+\s*,\s*[A-Z][a-z]+\s*$',
    ]
}

# Pre-compile regex patterns for performance
_compiled_patterns = None


def _get_compiled_patterns():
    """Compile and cache regex patterns for performance."""
    global _compiled_patterns
    if _compiled_patterns is None:
        _compiled_patterns = {
            "note_keywords": [re.compile(p, re.IGNORECASE) for p in NOTE_TEMPLATE_TRIGGERS["note_keywords"]],
            "patient_keywords": [re.compile(p, re.IGNORECASE) for p in NOTE_TEMPLATE_TRIGGERS["patient_keywords"]],
            "identifier_patterns": [re.compile(p) for p in NOTE_TEMPLATE_TRIGGERS["identifier_patterns"]]
        }
    return _compiled_patterns


def should_show_note_templates(user_input: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if user is asking about patient notes and should see template options.
    
    Returns:
        tuple: (should_show: bool, template_options_text: str or None)
    """
    if not user_input or not user_input.strip():
        return False, None
    
    user_input = user_input.strip()
    patterns = _get_compiled_patterns()
    
    # Check note-related keywords
    for pattern in patterns["note_keywords"]:
        if pattern.search(user_input):
            return True, get_template_options_text()
    
    # Check patient-related keywords
    for pattern in patterns["patient_keywords"]:
        if pattern.search(user_input):
            return True, get_template_options_text()
    
    # Check for standalone identifiers
    for pattern in patterns["identifier_patterns"]:
        if pattern.match(user_input):
            return True, get_template_options_text()
    
    return False, None


def get_note_template_prompt() -> str:
    """Get a formatted prompt to ask users which template they want to use."""
    template_options = get_template_options_text()
    
    prompt = f"""
I can help you with patient notes. Please select a template format for the notes:

{template_options}

Please reply with the number or name of the template you'd like to use.
"""
    return prompt.strip()


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    # Main dictionaries
    'patient_note_templates',
    'prompts',
    # Helper functions
    'get_template_options_text',
    'get_template_by_selection',
    'should_show_note_templates',
    'get_note_template_prompt',
    # Configuration
    'NOTE_TEMPLATE_TRIGGERS',
]
