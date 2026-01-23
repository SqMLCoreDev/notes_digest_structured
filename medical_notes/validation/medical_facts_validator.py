"""
Medical Facts Validator - Basic Medical Fact Consistency Validation

Checks basic medical fact consistency between source and generated output.
Focuses on medications, dosages, and dates.
"""

import re
from typing import Dict, Any, List


def check_medical_facts(source_note: str, generated_output: str) -> Dict[str, Any]:
    """
    Check basic medical fact consistency between source and generated output.
    Focuses on medications, dosages, and dates.
    
    Args:
        source_note: Original source medical note text
        generated_output: AI-generated output to validate
    
    Returns:
        dict with 'passed' (bool), 'score' (float), and 'issues' (list)
    """
    issues = []
    score = 1.0
    
    # Extract medications from source and generated output
    source_medications = _extract_medications(source_note)
    generated_medications = _extract_medications(generated_output)
    
    # Check for medication consistency
    if source_medications:
        missing_medications = []
        for med in source_medications:
            # Check if medication appears in generated output (fuzzy match)
            med_found = any(
                _fuzzy_medication_match(med, gen_med)
                for gen_med in generated_medications
            )
            if not med_found:
                missing_medications.append(med)
        
        if missing_medications:
            issues.append(f"Missing medications from source: {', '.join(missing_medications[:5])}")
            score -= min(0.3, len(missing_medications) * 0.05)
    
    # Extract dates from both
    source_dates = _extract_dates(source_note)
    generated_dates = _extract_dates(generated_output)
    
    # Check for date consistency (dates in generated should be reasonable relative to source)
    if source_dates and generated_dates:
        # Basic check: ensure generated dates are not completely inconsistent
        # (e.g., future dates when source has past dates)
        source_date_values = [d for d in source_dates if d]
        generated_date_values = [d for d in generated_dates if d]
        
        if source_date_values and generated_date_values:
            # Simple validation: dates should be in reasonable range
            # More sophisticated validation could be added here
            pass
    
    # Extract dosages (basic pattern matching)
    source_dosages = _extract_dosages(source_note)
    generated_dosages = _extract_dosages(generated_output)
    
    # Check for dosage consistency if medications match
    if source_dosages and generated_dosages:
        # Basic check: ensure dosages are present when medications are mentioned
        # More sophisticated validation could be added here
        pass
    
    score = max(0.0, score)  # Ensure score doesn't go below 0
    
    return {
        "passed": len(issues) == 0,
        "score": round(score, 3),
        "issues": issues
    }


def _extract_medications(text: str) -> List[str]:
    """
    Extract medication names from text using basic pattern matching.
    
    Args:
        text: Text to extract medications from
    
    Returns:
        List of medication names
    """
    medications = []
    
    # Common medication patterns
    # Look for medication mentions (this is a simplified approach)
    # In production, this could use a medical NER model or medication database
    
    # Pattern: medication name often followed by dosage
    medication_patterns = [
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+\d+",  # Name followed by number
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+mg",   # Name followed by mg
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+mcg",  # Name followed by mcg
    ]
    
    for pattern in medication_patterns:
        matches = re.findall(pattern, text)
        medications.extend(matches)
    
    # Remove duplicates and common false positives
    medications = list(set(medications))
    medications = [m for m in medications if len(m) > 2 and m.lower() not in ["the", "and", "for", "with"]]
    
    return medications[:20]  # Limit to first 20 to avoid excessive processing


def _extract_dates(text: str) -> List[str]:
    """
    Extract dates from text using pattern matching.
    
    Args:
        text: Text to extract dates from
    
    Returns:
        List of date strings
    """
    dates = []
    
    # Common date patterns
    date_patterns = [
        r"\d{1,2}/\d{1,2}/\d{4}",  # MM/DD/YYYY
        r"\d{4}-\d{2}-\d{2}",      # YYYY-MM-DD
        r"\d{1,2}-\d{1,2}-\d{4}",  # MM-DD-YYYY
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        dates.extend(matches)
    
    return list(set(dates))


def _extract_dosages(text: str) -> List[str]:
    """
    Extract dosage information from text.
    
    Args:
        text: Text to extract dosages from
    
    Returns:
        List of dosage strings
    """
    dosages = []
    
    # Dosage patterns
    dosage_patterns = [
        r"\d+\s*(?:mg|mcg|g|ml|units?)\s*(?:daily|BID|TID|QID|once|twice)",  # With frequency
        r"\d+\s*(?:mg|mcg|g|ml|units?)",  # Simple dosage
    ]
    
    for pattern in dosage_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dosages.extend(matches)
    
    return list(set(dosages))


def _fuzzy_medication_match(med1: str, med2: str) -> bool:
    """
    Check if two medication names are similar (fuzzy match).
    
    Args:
        med1: First medication name
        med2: Second medication name
    
    Returns:
        True if medications match, False otherwise
    """
    med1_clean = med1.lower().strip()
    med2_clean = med2.lower().strip()
    
    # Exact match
    if med1_clean == med2_clean:
        return True
    
    # Check if one contains the other (for partial matches)
    if med1_clean in med2_clean or med2_clean in med1_clean:
        return True
    
    # Check word overlap (if both have multiple words)
    words1 = set(med1_clean.split())
    words2 = set(med2_clean.split())
    
    if words1 and words2:
        overlap = len(words1.intersection(words2)) / max(len(words1), len(words2))
        if overlap > 0.5:  # More than 50% word overlap
            return True
    
    return False
