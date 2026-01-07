"""
Embeddings Status Routes for Medical Notes Processing API
Provides endpoints for monitoring background embeddings processing
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from medical_notes.service.background_embeddings_manager import (
    get_embeddings_manager,
    get_embeddings_task_status,
    get_embeddings_stats,
    queue_note_for_embeddings
)

router = APIRouter(prefix="/embeddings", tags=["embeddings-status"])


class EmbeddingsTaskResponse(BaseModel):
    task_id: str
    note_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


class EmbeddingsStatsResponse(BaseModel):
    total_queued: int
    total_completed: int
    total_failed: int
    current_queue_size: int
    active_workers: int
    manager_running: bool


class QueueEmbeddingsRequest(BaseModel):
    note_id: str
    priority: bool = False


class QueueEmbeddingsResponse(BaseModel):
    success: bool
    task_id: str
    message: str


@router.get("/stats", response_model=EmbeddingsStatsResponse)
async def get_embeddings_statistics():
    """
    Get current embeddings processing statistics.
    
    Returns:
        EmbeddingsStatsResponse: Current statistics including queue size, completed tasks, etc.
    """
    try:
        manager = get_embeddings_manager()
        stats = get_embeddings_stats()
        
        return EmbeddingsStatsResponse(
            total_queued=stats["total_queued"],
            total_completed=stats["total_completed"],
            total_failed=stats["total_failed"],
            current_queue_size=stats["current_queue_size"],
            active_workers=stats["active_workers"],
            manager_running=manager.running
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get embeddings statistics: {str(e)}")


@router.get("/task/{task_id}", response_model=EmbeddingsTaskResponse)
async def get_embeddings_task_status_endpoint(task_id: str):
    """
    Get status of a specific embeddings task.
    
    Args:
        task_id: The embeddings task ID to check
        
    Returns:
        EmbeddingsTaskResponse: Task status and details
    """
    try:
        task = get_embeddings_task_status(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Embeddings task {task_id} not found")
        
        return EmbeddingsTaskResponse(
            task_id=task.task_id,
            note_id=task.note_id,
            status=task.status.value,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error=task.error,
            result=task.result,
            retry_count=task.retry_count,
            max_retries=task.max_retries
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get embeddings task status: {str(e)}")


@router.post("/queue", response_model=QueueEmbeddingsResponse)
async def queue_embeddings_manually(request: QueueEmbeddingsRequest):
    """
    Manually queue a note for embeddings processing.
    
    Args:
        request: QueueEmbeddingsRequest containing note_id and priority
        
    Returns:
        QueueEmbeddingsResponse: Success status and task ID
    """
    try:
        task_id = queue_note_for_embeddings(request.note_id, priority=request.priority)
        
        return QueueEmbeddingsResponse(
            success=True,
            task_id=task_id,
            message=f"Note {request.note_id} queued for embeddings processing (priority: {request.priority})"
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))  # Service Unavailable
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue embeddings: {str(e)}")


@router.get("/queue/status")
async def get_queue_status():
    """
    Get detailed queue status information.
    
    Returns:
        Dict containing queue details and worker information
    """
    try:
        manager = get_embeddings_manager()
        stats = get_embeddings_stats()
        
        # Get recent tasks (last 10 completed/failed)
        recent_tasks = []
        with manager.task_lock:
            sorted_tasks = sorted(
                manager.tasks.values(),
                key=lambda t: t.created_at,
                reverse=True
            )
            
            for task in sorted_tasks[:10]:
                if task.status.value in ['completed', 'failed']:
                    recent_tasks.append({
                        'task_id': task.task_id,
                        'note_id': task.note_id,
                        'status': task.status.value,
                        'created_at': task.created_at.isoformat(),
                        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                        'error': task.error,
                        'retry_count': task.retry_count
                    })
        
        return {
            'queue_status': {
                'current_size': stats['current_queue_size'],
                'max_size': manager.queue_size,
                'is_full': manager.task_queue.full() if hasattr(manager.task_queue, 'full') else False
            },
            'workers': {
                'active_count': stats['active_workers'],
                'max_workers': manager.max_workers,
                'running': manager.running
            },
            'statistics': stats,
            'recent_tasks': recent_tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")


@router.post("/manager/start")
async def start_embeddings_manager():
    """
    Start the embeddings manager (if not already running).
    
    Returns:
        Dict with success status and message
    """
    try:
        manager = get_embeddings_manager()
        
        if manager.running:
            return {
                'success': True,
                'message': 'Embeddings manager is already running',
                'status': 'already_running'
            }
        
        manager.start()
        
        return {
            'success': True,
            'message': 'Embeddings manager started successfully',
            'status': 'started'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start embeddings manager: {str(e)}")


@router.post("/manager/stop")
async def stop_embeddings_manager():
    """
    Stop the embeddings manager.
    
    Returns:
        Dict with success status and message
    """
    try:
        manager = get_embeddings_manager()
        
        if not manager.running:
            return {
                'success': True,
                'message': 'Embeddings manager is not running',
                'status': 'already_stopped'
            }
        
        manager.stop()
        
        return {
            'success': True,
            'message': 'Embeddings manager stopped successfully',
            'status': 'stopped'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop embeddings manager: {str(e)}")


@router.post("/cleanup")
async def cleanup_old_embeddings_tasks(max_age_hours: int = 24):
    """
    Clean up old completed/failed embeddings tasks.
    
    Args:
        max_age_hours: Maximum age in hours for keeping task records (default: 24)
        
    Returns:
        Dict with cleanup results
    """
    try:
        manager = get_embeddings_manager()
        
        # Count tasks before cleanup
        with manager.task_lock:
            tasks_before = len(manager.tasks)
        
        # Perform cleanup
        manager.cleanup_old_tasks(max_age_hours=max_age_hours)
        
        # Count tasks after cleanup
        with manager.task_lock:
            tasks_after = len(manager.tasks)
        
        cleaned_count = tasks_before - tasks_after
        
        return {
            'success': True,
            'message': f'Cleaned up {cleaned_count} old embeddings task records',
            'tasks_before': tasks_before,
            'tasks_after': tasks_after,
            'cleaned_count': cleaned_count,
            'max_age_hours': max_age_hours
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup embeddings tasks: {str(e)}")