"""
Debug Routes - Medical Notes Processing API
Handles debug and administrative endpoints
"""

from fastapi import APIRouter

# Import services
from medical_notes.service.concurrent_job_manager import get_job_manager

# Create router
router = APIRouter(tags=["debug"], prefix="/debug")


@router.get("/jobs")
async def debug_jobs():
    """Debug endpoint to see detailed job information"""
    # Import jobs_db from service layer
    from medical_notes.service.app import jobs_db
    
    job_manager = get_job_manager()
    
    # Get all jobs from job manager
    concurrent_jobs = []
    for job_info in job_manager.get_all_jobs():
        concurrent_jobs.append({
            "job_id": job_info.job_id,
            "note_id": job_info.note_id,
            "status": job_info.status.value,
            "created_at": job_info.created_at.isoformat(),
            "started_at": job_info.started_at.isoformat() if job_info.started_at else None,
            "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
            "error": job_info.error,
            "result": job_info.result
        })
    
    # Get legacy jobs
    legacy_jobs = []
    for job_id, job_data in jobs_db.items():
        legacy_jobs.append({
            "job_id": job_id,
            "note_id": job_data.get('noteId'),
            "status": job_data.get('status'),
            "started_at": job_data.get('started_at'),
            "completed_at": job_data.get('completed_at'),
            "error": job_data.get('error'),
            "result": job_data.get('result')
        })
    
    return {
        "concurrent_jobs": concurrent_jobs,
        "legacy_jobs": legacy_jobs,
        "job_manager_stats": job_manager.get_stats(),
        "total_jobs": len(concurrent_jobs) + len(legacy_jobs)
    }