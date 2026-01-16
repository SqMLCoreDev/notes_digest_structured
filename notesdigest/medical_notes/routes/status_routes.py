"""
Status Routes - Medical Notes Processing API
Handles system status, job listing, and health check endpoints
"""

from fastapi import APIRouter
from datetime import datetime

# Import configuration and services
from medical_notes.config.config import (
    MAX_CONCURRENT_NOTES,
    MAX_QUEUE_SIZE,
    N_PREVIOUS_VISITS,
    ENABLE_DATA_FLATTENING,
    ES_INDEX_TOKEN_USAGE
)
from medical_notes.service.concurrent_job_manager import get_job_manager
from medical_notes.service.rate_limiter import get_bedrock_rate_limiter

# Create router
router = APIRouter(tags=["status"])


@router.get("/")
async def root():
    """API documentation"""
    return {
        "service": "Medical Notes Processing API - Concurrent Processing",
        "version": "4.0.0",
        "environment": "production",
        "processing_mode": "concurrent",
        "configuration": {
            "n_previous_visits": N_PREVIOUS_VISITS,
            "max_concurrent_notes": MAX_CONCURRENT_NOTES,
            "max_queue_size": MAX_QUEUE_SIZE,
            "note": "Concurrent processing is enabled by default - multiple notes process in parallel"
        },
        "features": {
            "concurrent_processing": f"Process up to {MAX_CONCURRENT_NOTES} notes simultaneously",
            "rate_limiting": "AWS Bedrock API rate limiting to prevent service overload",
            "queue_management": f"Queue up to {MAX_QUEUE_SIZE} jobs with automatic overflow protection",
            "mrn_extraction": "Automatically extracts patient MRN from raw text using LLM",
            "historical_context": f"Fetches {N_PREVIOUS_VISITS} previous visit(s) by dateOfService (not noteId sequence)",
            "date_based_query": "Previous visits are fetched based on dateOfService < current_date for the same MRN"
        },
        "processing_logic": {
            "on_success": "status='processed' in both indices, patientMRN updated, historical context included",
            "on_failure": "status='' (unchanged) in clinical_notes, record pushed to processed_notes with issues",
            "concurrent_behavior": "Each note processes independently - one failure doesn't affect others"
        },
        "tracking_fields": {
            "patientMRN": "Extracted patient MRN (updated in tiamd_prod_clinical_notes)",
            "dateOfServiceEpoch": "Date of service in epoch milliseconds format",
            "processedDateTime": "Timestamp when data was processed",
            "processingIssues": "Issues during processing (empty if none)",
            "submitDateTime": "Timestamp when submitted to API",
            "submittingIssues": "Issues during API submission (empty if none)"
        },
        "concurrency_details": {
            "worker_threads": MAX_CONCURRENT_NOTES,
            "queue_capacity": MAX_QUEUE_SIZE,
            "rate_limiting": "Token bucket algorithm for AWS Bedrock API calls",
            "resource_management": "Automatic cleanup and memory management for concurrent operations"
        },
        "token_usage_tracking": {
            "description": "Token usage is tracked per section and pushed to Elasticsearch",
            "elasticsearch_index": ES_INDEX_TOKEN_USAGE,
            "model": "claude-haiku-3-5",
            "pricing": {
                "input_per_1k_tokens": "$0.001",
                "output_per_1k_tokens": "$0.005"
            },
            "sections_tracked": [
                "note_type_mrn_extraction",
                "extraction_demographics",
                "extraction_clinical_timeline",
                "extraction_history_of_present_illness",
                "... (all extraction sections)",
                "extraction_json_extraction",
                "soap_demographics_subjective",
                "soap_objective_assessment",
                "soap_plan",
                "soap_json_extraction"
            ],
            "es_document_format": {
                "documentId": "The noteId being processed",
                "model": "LLM model used",
                "processedAt": "Timestamp (MM/dd/yyyy HH:mm:ss)",
                "processingTimeDurationSeconds": "Total processing duration",
                "totalsInputTokens": "Total input tokens across all sections",
                "totalsOutputTokens": "Total output tokens across all sections",
                "totalsTotalTokens": "Combined total tokens",
                "totalsCostUSD": "Total cost in USD",
                "sectionName": "Name of the section",
                "sectionInputTokens": "Input tokens for this section",
                "sectionOutputTokens": "Output tokens for this section",
                "sectionTotalTokens": "Total tokens for this section",
                "sectionCostUSD": "Cost for this section"
            }
        },
        "usage": {
            "step_1": "POST /process with {noteId: '12345'}",
            "step_2": "GET /progress/{job_id} to check status",
            "step_3": "GET /jobs to list all jobs"
        },
        "processing_stages": [
            "1. validation - Check noteId exists and not processed",
            "2. fetch - Fetch noteId, rawdata, dateOfService",
            "3. extraction - Extract note type AND patient MRN using LLM",
            "4. update_mrn - Update patientMRN and dateOfServiceEpoch in tiamd_prod_clinical_notes",
            f"5. historical_context - Fetch {N_PREVIOUS_VISITS} previous visit(s) by dateOfService from tiamd_prod_processed_notes",
            "6. combine_context - Combine previous visits' notesProcessedText with current rawdata",
            "7. data_extraction - Extract structured data using unified template system (includes SOAP generation)",
            "8. push_to_index - Push to tiamd_prod_processed_notes with status='processed' and dateOfServiceEpoch",
            "8b. push_digest_to_index - Push notes_digest to tiamd_prod_notes_digest",
            "9. api_push - Push to external API",
            "10. status_update - Update status in tiamd_prod_clinical_notes",
            "11. submit_tracking - Update submitDateTime and submittingIssues",
            "12. final_status_update - Update to 'note submitted'"
        ],
        "example_flow": {
            "noteId_110": "Current note with dateOfService=2025-10-22",
            "mrn_extracted": "MRN12345",
            "previous_visits_query": "Find all notes with MRN12345 WHERE dateOfService < 2025-10-22 ORDER BY dateOfService DESC LIMIT N",
            "previous_visits_found": "noteId=108 (2025-10-15), noteId=105 (2025-10-01)",
            "note": "Previous visits are fetched by DATE, not by sequential noteId"
        },
        "example": {
            "curl_submit": 'curl -X POST "http://localhost:8000/process" -H "Content-Type: application/json" -d \'{"noteId": "12345"}\'',
            "curl_status": 'curl -X GET "http://localhost:8000/progress/{job_id}"',
            "note": f"Historical context is fixed at {N_PREVIOUS_VISITS} previous visit(s) by dateOfService"
        }
    }


@router.get("/status")
async def get_system_status():
    """Get comprehensive system status including concurrency and rate limiting statistics"""
    job_manager = get_job_manager()
    rate_limiter = get_bedrock_rate_limiter()
    
    # Get job manager statistics
    job_stats = job_manager.get_stats()
    
    # Get rate limiter statistics
    rate_stats = rate_limiter.get_stats()
    
    return {
        "service": "Medical Notes Processing API - Concurrent Processing",
        "version": "4.0.0",
        "timestamp": datetime.now().isoformat(),
        "processing_mode": "concurrent",
        "configuration": {
            "max_concurrent_notes": MAX_CONCURRENT_NOTES,
            "max_queue_size": MAX_QUEUE_SIZE,
            "n_previous_visits": N_PREVIOUS_VISITS,
            "enable_data_flattening": ENABLE_DATA_FLATTENING
        },
        "job_statistics": job_stats,
        "rate_limiting": rate_stats,
        "system_health": {
            "queue_utilization_percent": round((job_stats["current_queued"] / MAX_QUEUE_SIZE) * 100, 2),
            "worker_utilization_percent": round((job_stats["current_active"] / MAX_CONCURRENT_NOTES) * 100, 2),
            "total_processed": job_stats["total_completed"] + job_stats["total_failed"],
            "success_rate_percent": round(
                (job_stats["total_completed"] / max(1, job_stats["total_completed"] + job_stats["total_failed"])) * 100, 2
            ) if (job_stats["total_completed"] + job_stats["total_failed"]) > 0 else 0
        }
    }


@router.get("/jobs")
async def list_jobs():
    """List all jobs with their current status (includes both concurrent and legacy jobs)"""
    # Import jobs_db from service layer
    from medical_notes.service.app import jobs_db
    
    job_manager = get_job_manager()
    
    # Get jobs from job manager
    concurrent_jobs = []
    for job_info in job_manager.get_all_jobs():
        duration_seconds = None
        if job_info.started_at and job_info.completed_at:
            duration_seconds = (job_info.completed_at - job_info.started_at).total_seconds()
        
        concurrent_jobs.append({
            "job_id": job_info.job_id,
            "noteId": job_info.note_id,
            "status": job_info.status.value,
            "current_stage": job_info.status.value,
            "started_at": job_info.created_at.isoformat(),
            "actual_started_at": job_info.started_at.isoformat() if job_info.started_at else None,
            "completed_at": job_info.completed_at.isoformat() if job_info.completed_at else None,
            "duration_seconds": duration_seconds,
            "duration_minutes": round(duration_seconds / 60, 2) if duration_seconds else None,
            "error": job_info.error
        })
    
    # Get legacy jobs from jobs_db
    legacy_jobs = [
        {
            "job_id": job['job_id'],
            "noteId": job['noteId'],
            "status": job['status'],
            "current_stage": job['current_stage'],
            "started_at": job['started_at'],
            "actual_started_at": job.get('actual_started_at'),
            "completed_at": job.get('completed_at'),
            "duration_seconds": job.get('duration_seconds'),
            "duration_minutes": round(job['duration_seconds'] / 60, 2) if job.get('duration_seconds') else None,
            "error": job.get('error')
        }
        for job in jobs_db.values()
        if job['job_id'] not in [j['job_id'] for j in concurrent_jobs]  # Avoid duplicates
    ]
    
    all_jobs = concurrent_jobs + legacy_jobs
    
    return {
        "total_jobs": len(all_jobs),
        "concurrent_jobs": len(concurrent_jobs),
        "legacy_jobs": len(legacy_jobs),
        "configured_previous_visits": N_PREVIOUS_VISITS,
        "concurrency_settings": {
            "max_concurrent_notes": MAX_CONCURRENT_NOTES,
            "max_queue_size": MAX_QUEUE_SIZE
        },
        "jobs": all_jobs
    }


@router.get("/health")
async def health():
    """Health check endpoint"""
    # Import jobs_db from service layer
    from medical_notes.service.app import jobs_db
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "configured_previous_visits": N_PREVIOUS_VISITS,
        "jobs_count": len(jobs_db),
        "active_jobs": sum(1 for job in jobs_db.values() if job['status'] in ['queued', 'processing'])
    }