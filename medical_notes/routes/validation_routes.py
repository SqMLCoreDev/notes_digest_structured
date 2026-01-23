"""
Validation Routes - Medical Notes Validation API

Handles validation endpoints for AI-generated medical note summaries.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List

# Import validation function
from medical_notes.validation.validator import validate_note

# Create router
router = APIRouter(tags=["validation"])


# Pydantic Models
class ValidationRequest(BaseModel):
    source_note: str
    generated_output: str
    note_type: str
    note_id: Optional[str] = None
    store_to_es: bool = True
    
    @field_validator('source_note')
    @classmethod
    def validate_source_note(cls, v):
        if not v or not v.strip():
            raise ValueError('source_note cannot be empty')
        return v.strip()
    
    @field_validator('generated_output')
    @classmethod
    def validate_generated_output(cls, v):
        if not v or not v.strip():
            raise ValueError('generated_output cannot be empty')
        return v.strip()
    
    @field_validator('note_type')
    @classmethod
    def validate_note_type(cls, v):
        if not v or not v.strip():
            raise ValueError('note_type cannot be empty')
        return v.strip()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "source_note": "Patient presents with headache...",
                "generated_output": "PROGRESS NOTE\nPATIENT INFORMATION...",
                "note_type": "progress_note",
                "note_id": "12345",
                "store_to_es": True
            }
        }
    }


class ValidationIssue(BaseModel):
    faithfulness: List[str]
    template: List[str]
    medical_facts: List[str]
    rouge: List[str]
    hallucination: List[str]
    geval: List[str]


class ValidationScores(BaseModel):
    faithfulness: float
    template: float
    medical_facts: float
    rouge: float
    hallucination: float
    geval: float


class RougeScores(BaseModel):
    rouge_1: float
    rouge_2: float
    rouge_l: float


class GevalScores(BaseModel):
    relevance: float
    coherence: float
    consistency: float
    completeness: float
    relevance_reasoning: Optional[str] = ""
    coherence_reasoning: Optional[str] = ""
    consistency_reasoning: Optional[str] = ""
    completeness_reasoning: Optional[str] = ""


class ValidationResponse(BaseModel):
    decision: str
    score: float
    issues: ValidationIssue
    scores: ValidationScores
    timestamp: str
    note_type: str
    validation_id: Optional[str] = None
    note_id: Optional[str] = None
    rouge_scores: Optional[RougeScores] = None
    hallucination_rate: Optional[float] = None
    hallucinated_sentences: Optional[List[str]] = None
    geval_scores: Optional[GevalScores] = None


@router.post("/validate", response_model=ValidationResponse)
async def validate_medical_note(request: ValidationRequest):
    """
    Validate an AI-generated medical note summary.
    
    Performs six validation checks:
    1. Faithfulness check (LLM-as-judge)
    2. SOAP template completeness check
    3. Basic medical fact consistency check
    4. ROUGE scores (ROUGE-1, ROUGE-2, ROUGE-L)
    5. Hallucination score (LLM-as-judge)
    6. G-Eval score (LLM-as-judge with chain-of-thought)
    
    Results are stored to Elasticsearch if store_to_es is True and note_id is provided.
    """
    try:
        result = validate_note(
            source_note=request.source_note,
            generated_output=request.generated_output,
            note_type=request.note_type,
            note_id=request.note_id,
            store_to_es=request.store_to_es
        )
        
        # Build response with all metrics
        response_data = {
            "decision": result["decision"],
            "score": result["score"],
            "issues": ValidationIssue(
                faithfulness=result["issues"].get("faithfulness", []),
                template=result["issues"].get("template", []),
                medical_facts=result["issues"].get("medical_facts", []),
                rouge=result["issues"].get("rouge", []),
                hallucination=result["issues"].get("hallucination", []),
                geval=result["issues"].get("geval", [])
            ),
            "scores": ValidationScores(
                faithfulness=result["scores"]["faithfulness"],
                template=result["scores"]["template"],
                medical_facts=result["scores"]["medical_facts"],
                rouge=result["scores"].get("rouge", 0.0),
                hallucination=result["scores"].get("hallucination", 0.0),
                geval=result["scores"].get("geval", 0.0)
            ),
            "timestamp": result["timestamp"],
            "note_type": result["note_type"],
            "validation_id": result.get("validation_id"),
            "note_id": request.note_id
        }
        
        # Add ROUGE scores if available
        if result.get("rouge_scores"):
            response_data["rouge_scores"] = RougeScores(**result["rouge_scores"])
        
        # Add hallucination data if available
        if "hallucination_rate" in result:
            response_data["hallucination_rate"] = result["hallucination_rate"]
        if result.get("hallucinated_sentences"):
            response_data["hallucinated_sentences"] = result["hallucinated_sentences"]
        
        # Add G-Eval scores if available
        if result.get("geval_scores"):
            response_data["geval_scores"] = GevalScores(**result["geval_scores"])
        
        return ValidationResponse(**response_data)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/validate/{note_id}")
async def get_validation_history(note_id: str):
    """
    Get validation history for a specific note ID.
    
    Retrieves all validation results stored in Elasticsearch for the given note_id.
    """
    try:
        from medical_notes.repository.elastic_search import get_notes_by_noteid
        from medical_notes.config.config import ES_INDEX_VALIDATION
        
        # Query ES for validation records
        validations = get_notes_by_noteid(ES_INDEX_VALIDATION, note_id)
        
        if not validations:
            raise HTTPException(
                status_code=404, 
                detail=f"No validation records found for note_id: {note_id}"
            )
        
        # Format response
        validation_list = []
        for val in validations:
            validation_list.append({
                "validation_id": val.get("validationId"),
                "timestamp": val.get("timestamp"),
                "decision": val.get("decision"),
                "score": val.get("score"),
                "note_type": val.get("noteType"),
                "scores": val.get("scores", {}),
                "issues": val.get("issues", {})
            })
        
        return {
            "note_id": note_id,
            "count": len(validation_list),
            "validations": validation_list
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve validation history: {str(e)}"
        )
