"""
Embeddings API Routes - Manual Processing and Testing
Provides endpoints for manual embeddings generation and health checks
"""


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any
import logging

from medical_notes.service.embeddings import process_note_embeddings, EmbeddingsServiceError

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


class EmbeddingsRequest(BaseModel):
    """Request model for manual embeddings generation"""
    note_id: str = Field(..., description="The unique identifier of the clinical note")


class EmbeddingsResponse(BaseModel):
    """Response model for embeddings generation"""
    success: bool
    message: str
    note_id: str
    chunks_processed: int = None
    processing_time_seconds: float = None
    note_type: str = None
    patient_mrn: str = None
    service_date: str = None
    rawdata_length: int = None
    processed_at: str = None


@router.post("/generate", response_model=EmbeddingsResponse, summary="Generate Embeddings Manually")
async def generate_embeddings_manually(request: EmbeddingsRequest):
    """
    Manually generate embeddings for a clinical note
    
    **Use Cases:**
    - Test embeddings functionality
    - Reprocess embeddings for existing notes
    - Generate embeddings for notes processed before embeddings were enabled
    
    **Note:** Embeddings are automatically generated during normal note processing.
    This endpoint is for manual/testing purposes only.
    """
    try:
        logger.info(f"Manual embeddings generation request for note {request.note_id}")
        
        # Process embeddings
        result = process_note_embeddings(request.note_id)
        
        # Return success response
        return EmbeddingsResponse(
            success=True,
            message=f"Successfully generated embeddings for note {request.note_id}",
            note_id=result["note_id"],
            chunks_processed=result["chunks_processed"],
            processing_time_seconds=result["processing_time_seconds"],
            note_type=result.get("note_type"),
            patient_mrn=result.get("patient_mrn"),
            service_date=result.get("service_date"),
            rawdata_length=result.get("rawdata_length"),
            processed_at=result["processed_at"]
        )
        
    except EmbeddingsServiceError as e:
        logger.error(f"Embeddings service error for note {request.note_id}: {str(e)}")
        
        # Determine appropriate HTTP status code based on error message
        if "not found" in str(e).lower():
            status_code = 404
        elif "empty" in str(e).lower() or "missing" in str(e).lower():
            status_code = 422  # Unprocessable Entity
        else:
            status_code = 500  # Internal Server Error
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "success": False,
                "message": str(e),
                "note_id": request.note_id
            }
        )
    
    except Exception as e:
        logger.error(f"Unexpected error generating embeddings for note {request.note_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "note_id": request.note_id
            }
        )


@router.get("/config", summary="Embeddings Configuration")
async def get_embeddings_config():
    """
    Get current embeddings configuration
    
    **Returns:**
    - Current embeddings settings
    - Useful for debugging configuration issues
    """
    try:
        from medical_notes.config.config import (
            ENABLE_EMBEDDINGS_PROCESSING, VECTOR_DB_COLLECTION_NAME, 
            EMBEDDINGS_MODEL_ID, EMBEDDINGS_CHUNK_SIZE, EMBEDDINGS_CHUNK_OVERLAP,
            EMBEDDINGS_MAX_RETRIES, EMBEDDINGS_RETRY_DELAY
        )
        
        return {
            "embeddings_enabled": ENABLE_EMBEDDINGS_PROCESSING,
            "vector_database": {
                "collection_name": VECTOR_DB_COLLECTION_NAME
            },
            "model": {
                "model_id": EMBEDDINGS_MODEL_ID
            },
            "text_processing": {
                "chunk_size": EMBEDDINGS_CHUNK_SIZE,
                "chunk_overlap": EMBEDDINGS_CHUNK_OVERLAP
            },
            "retry_settings": {
                "max_retries": EMBEDDINGS_MAX_RETRIES,
                "retry_delay": EMBEDDINGS_RETRY_DELAY
            },
            "integration": "Automatic processing during note workflow"
        }
        
    except Exception as e:
        logger.error(f"Error getting embeddings config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to get embeddings configuration: {str(e)}"
            }
        )