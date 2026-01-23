"""
Template Validator - SOAP Template Completeness Validation

Checks if generated output follows the required SOAP template structure for the note type.
"""

import re
from typing import Dict, Any, List


def check_template_completeness(generated_output: str, note_type: str) -> Dict[str, Any]:
    """
    Check if generated output follows the required SOAP template structure for the note type.
    
    Args:
        generated_output: AI-generated output to validate
        note_type: Type of note (e.g., 'progress_note', 'history_physical', etc.)
    
    Returns:
        dict with 'passed' (bool), 'score' (float), and 'issues' (list)
    """
    issues = []
    score = 1.0
    
    # Normalize note type
    note_type_normalized = note_type.strip().lower().replace(" ", "_")
    
    # Define required sections for each note type
    required_sections = _get_required_sections(note_type_normalized)
    
    if not required_sections:
        # Unknown note type - use generic SOAP structure
        required_sections = ["SUBJECTIVE", "OBJECTIVE", "ASSESSMENT", "PLAN"]
    
    # Check for required sections (case-insensitive)
    output_upper = generated_output.upper()
    missing_sections = []
    
    for section in required_sections:
        # Check for section header (with various formats)
        section_patterns = [
            rf"\b{re.escape(section)}\b",
            rf"{re.escape(section)}:",
            rf"{re.escape(section)}\s*:",
        ]
        
        found = False
        for pattern in section_patterns:
            if re.search(pattern, output_upper):
                found = True
                break
        
        if not found:
            missing_sections.append(section)
            issues.append(f"Missing required section: {section}")
            score -= 0.15  # Penalty per missing section
    
    # Check for SOAP structure if applicable
    if note_type_normalized in ["progress_note", "history_physical", "consultation_note"]:
        soap_sections = ["SUBJECTIVE", "OBJECTIVE", "ASSESSMENT", "PLAN"]
        soap_found = sum(1 for section in soap_sections if re.search(rf"\b{re.escape(section)}\b", output_upper))
        
        if soap_found < 3:
            issues.append("Incomplete SOAP structure - missing critical sections")
            score -= 0.2
    
    # Check for patient information section (common requirement)
    patient_info_patterns = [
        r"PATIENT\s+INFORMATION",
        r"PATIENT\s+INFO",
        r"PATIENT\s+DATA"
    ]
    
    patient_info_found = any(re.search(pattern, output_upper) for pattern in patient_info_patterns)
    if not patient_info_found and note_type_normalized != "generic_note":
        issues.append("Missing patient information section")
        score -= 0.1
    
    score = max(0.0, score)  # Ensure score doesn't go below 0
    
    return {
        "passed": len(issues) == 0,
        "score": round(score, 3),
        "issues": issues
    }


def _get_required_sections(note_type: str) -> List[str]:
    """
    Get required sections for a given note type.
    
    Args:
        note_type: Normalized note type
    
    Returns:
        List of required section names
    """
    section_map = {
        "progress_note": [
            "PATIENT INFORMATION",
            "SUBJECTIVE",
            "HISTORY OF PRESENTING ILLNESS",
            "OBJECTIVE",
            "PHYSICAL EXAMINATION",
            "ASSESSMENT",
            "PLAN"
        ],
        "history_physical": [
            "PATIENT INFORMATION",
            "SUBJECTIVE",
            "HISTORY OF PRESENTING ILLNESS",
            "OBJECTIVE",
            "PHYSICAL EXAMINATION",
            "ASSESSMENT",
            "PLAN"
        ],
        "discharge_summary": [
            "PATIENT INFORMATION",
            "HISTORY OF PRESENTING ILLNESS",
            "HOSPITAL COURSE",
            "DISCHARGE DIAGNOSIS",
            "DISCHARGE MEDICATIONS",
            "DISCHARGE INSTRUCTIONS"
        ],
        "consultation_note": [
            "PATIENT INFORMATION",
            "SUBJECTIVE",
            "OBJECTIVE",
            "ASSESSMENT",
            "PLAN",
            "CONSULTATION INFORMATION"
        ],
        "procedure_note": [
            "PATIENT INFORMATION",
            "PROCEDURE",
            "INDICATIONS",
            "FINDINGS",
            "COMPLICATIONS"
        ],
        "ed_note": [
            "PATIENT INFORMATION",
            "CHIEF COMPLAINT",
            "HISTORY OF PRESENT ILLNESS",
            "PHYSICAL EXAMINATION",
            "ASSESSMENT",
            "PLAN"
        ],
        "generic_note": [
            "SUBJECTIVE",
            "OBJECTIVE",
            "ASSESSMENT",
            "PLAN"
        ]
    }
    
    return section_map.get(note_type, [])
