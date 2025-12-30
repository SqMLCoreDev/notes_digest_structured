"""
Process Routes - Medical Notes Processing API
Handles note processing and progress tracking endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

# Import processing functions from service layer
from medical_notes.service.concurrent_job_manager import get_job_manager
from medical_notes.config.config import N_PREVIOUS_VISITS

# Create router
router = APIRouter(tags=["processing"])

# Pydantic Models
class ProcessRequest(BaseModel):
    noteId: str
    
    @field_validator('noteId')
    @classmethod
    def validate_noteid(cls, v):
        if not v:
            raise ValueError('noteId cannot be empty')
        if not v.isdigit():
            raise ValueError('noteId must be numeric')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {"noteId": "12345"}
        }
    }


class ProcessResponse(BaseModel):
    job_id: str
    noteId: str
    status: str
    message: str
    check_status_url: str


class LogEntry(BaseModel):
    timestamp: str
    stage: str
    status: str
    message: str


class ProgressResponse(BaseModel):
    job_id: str
    noteId: str
    status: str
    current_stage: str
    logs: List[LogEntry]
    result: Optional[dict] = None
    started_at: str
    actual_started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None


@router.post("/process", response_model=ProcessResponse)
async def process_note(request: ProcessRequest):
    """Submit a medical note for concurrent processing (default behavior)"""
    note_id = request.noteId
    
    try:
        # Import the wrapper function from service layer
        from medical_notes.service.app import concurrent_process_note_wrapper
        
        # Get job manager
        job_manager = get_job_manager()
        
        # Check if queue is full
        if job_manager.is_queue_full():
            raise HTTPException(
                status_code=503, 
                detail=f"Service temporarily unavailable. Processing queue is full ({job_manager.max_queue_size} jobs). Please try again later."
            )
        
        # Submit job for concurrent processing
        job_id = job_manager.submit_job(
            note_id=note_id,
            process_function=concurrent_process_note_wrapper
        )
        
        return ProcessResponse(
            job_id=job_id,
            noteId=note_id,
            status="queued",
            message=f"Job queued for concurrent processing (noteId: {note_id}, historical context: {N_PREVIOUS_VISITS} previous visits)",
            check_status_url=f"/progress/{job_id}"
        )
        
    except RuntimeError as e:
        # Queue full or other runtime error
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Unexpected error
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")


@router.get("/progress/{job_id}", response_model=ProgressResponse)
async def get_progress(job_id: str):
    """Check the processing status and logs of a job"""
    # Import jobs_db from service layer
    from medical_notes.service.app import jobs_db
    
    # First check job manager
    job_manager = get_job_manager()
    job_info = job_manager.get_job_status(job_id)
    
    if job_info:
        # Convert job manager info to response format
        logs = []
        if job_info.status.value == "processing":
            logs.append(LogEntry(
                timestamp=job_info.started_at.isoformat() if job_info.started_at else job_info.created_at.isoformat(),
                stage="processing",
                status="in_progress",
                message=f"Processing note {job_info.note_id}"
            ))
        elif job_info.status.value == "completed":
            logs.append(LogEntry(
                timestamp=job_info.completed_at.isoformat() if job_info.completed_at else datetime.now().isoformat(),
                stage="completed",
                status="success",
                message=f"Successfully processed note {job_info.note_id}"
            ))
        elif job_info.status.value == "failed":
            logs.append(LogEntry(
                timestamp=job_info.completed_at.isoformat() if job_info.completed_at else datetime.now().isoformat(),
                stage="failed",
                status="failed",
                message=job_info.error or "Processing failed"
            ))
        
        # Calculate duration
        duration_seconds = None
        if job_info.started_at and job_info.completed_at:
            duration_seconds = (job_info.completed_at - job_info.started_at).total_seconds()
        
        return ProgressResponse(
            job_id=job_id,
            noteId=job_info.note_id,
            status=job_info.status.value,
            current_stage=job_info.status.value,
            logs=logs,
            result=job_info.result,
            started_at=job_info.created_at.isoformat(),
            actual_started_at=job_info.started_at.isoformat() if job_info.started_at else None,
            completed_at=job_info.completed_at.isoformat() if job_info.completed_at else None,
            duration_seconds=duration_seconds,
            error=job_info.error
        )
    
    # Fallback to legacy jobs_db for compatibility
    job = jobs_db.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['status'] == 'failed':
        raise HTTPException(
            status_code=500,
            detail={
                "job_id": job_id,
                "noteId": job['noteId'],
                "status": job['status'],
                "current_stage": job['current_stage'],
                "logs": [LogEntry(**log) for log in job['logs']],
                "started_at": job['started_at'],
                "actual_started_at": job.get('actual_started_at'),
                "completed_at": job.get('completed_at'),
                "duration_seconds": job.get('duration_seconds'),
                "error": job.get('error')
            }
        )
    
    return ProgressResponse(
        job_id=job_id,
        noteId=job['noteId'],
        status=job['status'],
        current_stage=job['current_stage'],
        logs=[LogEntry(**log) for log in job['logs']],
        result=job.get('result'),
        started_at=job['started_at'],
        actual_started_at=job.get('actual_started_at'),
        completed_at=job.get('completed_at'),
        duration_seconds=job.get('duration_seconds'),
        error=job.get('error')
    )