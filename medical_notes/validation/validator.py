"""
Clinical Validation Module for AI-Generated Medical Note Summaries

Main integration point for validation. Orchestrates all validation checks
and stores results to Elasticsearch.
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd

# Import individual validators
from medical_notes.validation.faithfulness_validator import check_faithfulness
from medical_notes.validation.template_validator import check_template_completeness
from medical_notes.validation.medical_facts_validator import check_medical_facts
from medical_notes.validation.rouge_validator import check_rouge_scores
from medical_notes.validation.hallucination_validator import check_hallucination_score
from medical_notes.validation.geval_validator import check_geval_score


def validate_note(source_note: str, generated_output: str, note_type: str, 
                  note_id: str = None, store_to_es: bool = True) -> Dict[str, Any]:
    """
    Perform end-to-end clinical validation for AI-generated medical note summaries.
    
    This is the single integration touchpoint for validation.
    
    Args:
        source_note: Original source medical note text
        generated_output: AI-generated output to validate
        note_type: Type of note (e.g., 'progress_note', 'history_physical', etc.)
        note_id: Optional note ID for tracking and ES storage
        store_to_es: Whether to store validation results to Elasticsearch (default: True)
    
    Returns:
        dict with keys:
            - decision: "APPROVE" | "REVIEW" | "REJECT"
            - score: float between 0 and 1 (weighted average of all metrics)
            - issues: dict with faithfulness, template, medical_facts, rouge, hallucination, geval issues
            - scores: dict with individual metric scores
            - rouge_scores: dict with ROUGE-1, ROUGE-2, ROUGE-L scores
            - hallucination_rate: float (0.0-1.0, lower is better)
            - hallucinated_sentences: list of hallucinated sentences
            - geval_scores: dict with G-Eval dimension scores
            - validation_id: Unique validation ID (if stored to ES)
            - timestamp: Validation timestamp
    """
    issues = {
        "faithfulness": [],
        "template": [],
        "medical_facts": [],
        "rouge": [],
        "hallucination": [],
        "geval": []
    }
    
    # 1. Faithfulness check using LLM-as-judge
    faithfulness_result = check_faithfulness(source_note, generated_output)
    if not faithfulness_result["passed"]:
        issues["faithfulness"] = faithfulness_result.get("issues", [])
    
    # 2. SOAP template completeness check
    template_result = check_template_completeness(generated_output, note_type)
    if not template_result["passed"]:
        issues["template"] = template_result.get("issues", [])
    
    # 3. Basic medical fact consistency check
    medical_facts_result = check_medical_facts(source_note, generated_output)
    if not medical_facts_result["passed"]:
        issues["medical_facts"] = medical_facts_result.get("issues", [])
    
    # 4. ROUGE scores (statistical metric)
    rouge_result = check_rouge_scores(source_note, generated_output)
    if not rouge_result["passed"]:
        issues["rouge"] = rouge_result.get("issues", [])
    
    # 5. Hallucination score (statistical metric)
    hallucination_result = check_hallucination_score(source_note, generated_output)
    if not hallucination_result["passed"]:
        issues["hallucination"] = hallucination_result.get("issues", [])
    
    # 6. G-Eval score (statistical metric)
    geval_result = check_geval_score(source_note, generated_output, note_type)
    if not geval_result["passed"]:
        issues["geval"] = geval_result.get("issues", [])
    
    # Calculate overall score (weighted average)
    faithfulness_score = faithfulness_result.get("score", 0.0)
    template_score = template_result.get("score", 0.0)
    medical_facts_score = medical_facts_result.get("score", 0.0)
    rouge_score = rouge_result.get("score", 0.0)
    hallucination_score = hallucination_result.get("score", 0.0)
    geval_score = geval_result.get("score", 0.0)
    
    # Weighted scoring with all metrics:
    # Core validations: faithfulness 25%, template 15%, medical_facts 10%
    # Statistical metrics: ROUGE 15%, hallucination 20%, G-Eval 15%
    overall_score = (
        faithfulness_score * 0.25 +
        template_score * 0.15 +
        medical_facts_score * 0.10 +
        rouge_score * 0.15 +
        hallucination_score * 0.20 +
        geval_score * 0.15
    )
    
    # Determine decision based on score and critical issues
    decision = _determine_decision(overall_score, issues)
    
    # Prepare validation result
    validation_result = {
        "decision": decision,
        "score": round(overall_score, 3),
        "issues": issues,
        "timestamp": datetime.now().isoformat(),
        "note_type": note_type,
        "scores": {
            "faithfulness": round(faithfulness_score, 3),
            "template": round(template_score, 3),
            "medical_facts": round(medical_facts_score, 3),
            "rouge": round(rouge_score, 3),
            "hallucination": round(hallucination_score, 3),
            "geval": round(geval_score, 3)
        },
        "rouge_scores": rouge_result.get("rouge_scores", {}),
        "hallucination_rate": hallucination_result.get("hallucination_rate", 1.0),
        "hallucinated_sentences": hallucination_result.get("hallucinated_sentences", []),
        "geval_scores": geval_result.get("geval_scores", {})
    }
    
    # Store to Elasticsearch if requested
    if store_to_es and note_id:
        validation_id = _store_validation_to_es(note_id, validation_result, source_note, generated_output)
        validation_result["validation_id"] = validation_id
    
    return validation_result


def _determine_decision(score: float, issues: Dict[str, list]) -> str:
    """
    Determine the validation decision based on score and issues.
    
    Args:
        score: Overall validation score (0.0-1.0)
        issues: Dictionary of issues by category
    
    Returns:
        "APPROVE", "REVIEW", or "REJECT"
    """
    # Count critical issues
    critical_issues = []
    
    # Faithfulness issues are critical
    if issues.get("faithfulness"):
        critical_issues.extend(issues["faithfulness"])
    
    # Multiple template issues are concerning
    if len(issues.get("template", [])) > 2:
        critical_issues.extend(issues["template"][:3])
    
    # Medical fact issues are critical
    if issues.get("medical_facts"):
        critical_issues.extend(issues["medical_facts"])
    
    # Hallucination issues are critical
    if issues.get("hallucination"):
        critical_issues.extend(issues["hallucination"][:3])
    
    # G-Eval issues are important
    if len(issues.get("geval", [])) > 2:
        critical_issues.extend(issues["geval"][:2])
    
    # Decision logic
    if score >= 0.9 and len(critical_issues) == 0:
        return "APPROVE"
    elif score >= 0.7 and len(critical_issues) <= 1:
        return "REVIEW"
    else:
        return "REJECT"


def _store_validation_to_es(note_id: str, validation_result: Dict[str, Any], 
                           source_note: str, generated_output: str) -> str:
    """
    Store validation results to Elasticsearch.
    
    Args:
        note_id: Note ID
        validation_result: Validation result dictionary
        source_note: Original source note (truncated for storage)
        generated_output: Generated output (truncated for storage)
    
    Returns:
        Validation ID (composite key)
    """
    try:
        from medical_notes.repository.elastic_search import df_to_es_load
        from medical_notes.config.config import ES_INDEX_VALIDATION
        import uuid
        
        # Generate validation ID
        validation_id = f"{note_id}_{uuid.uuid4().hex[:8]}"
        
        # Prepare ES record
        es_record = {
            "_id": validation_id,
            "noteId": note_id,
            "validationId": validation_id,
            "timestamp": validation_result["timestamp"],
            "decision": validation_result["decision"],
            "score": validation_result["score"],
            "noteType": validation_result["note_type"],
            "scores": validation_result["scores"],
            "issues": validation_result["issues"],
            "rougeScores": validation_result.get("rouge_scores", {}),
            "hallucinationRate": validation_result.get("hallucination_rate", 1.0),
            "hallucinatedSentences": validation_result.get("hallucinated_sentences", []),
            "gevalScores": validation_result.get("geval_scores", {}),
            "sourceNoteLength": len(source_note),
            "generatedOutputLength": len(generated_output),
            # Store truncated versions for reference (first 1000 chars)
            "sourceNotePreview": source_note[:1000] if len(source_note) > 1000 else source_note,
            "generatedOutputPreview": generated_output[:1000] if len(generated_output) > 1000 else generated_output
        }
        
        # Convert to DataFrame and load to ES
        es_df = pd.DataFrame([es_record])
        df_to_es_load(es_df, ES_INDEX_VALIDATION)
        
        return validation_id
    
    except Exception as e:
        # Log error but don't fail validation
        print(f"Warning: Failed to store validation to Elasticsearch: {str(e)}")
        return f"storage_failed_{note_id}"
