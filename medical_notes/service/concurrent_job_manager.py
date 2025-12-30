"""
Concurrent Job Manager for Medical Notes Processing
Handles parallel processing of multiple note IDs with resource management
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List, Any
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from enum import Enum
import uuid

from medical_notes.config.config import (
    MAX_CONCURRENT_NOTES,
    MAX_QUEUE_SIZE,
    NOTE_PROCESSING_TIMEOUT
)


class JobStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class JobInfo:
    job_id: str
    note_id: str
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    future: Optional[Future] = None


class ConcurrentJobManager:
    """
    Manages concurrent processing of medical notes with resource limits and queue management.
    """
    
    def __init__(self, max_workers: int = MAX_CONCURRENT_NOTES, max_queue_size: int = MAX_QUEUE_SIZE):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="MedicalNotes")
        
        # Job tracking
        self.jobs: Dict[str, JobInfo] = {}
        self.active_jobs: Dict[str, JobInfo] = {}  # Currently processing
        self.job_lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_timeout": 0,
            "current_active": 0,
            "current_queued": 0
        }
        
        print(f"🚀 ConcurrentJobManager initialized with {max_workers} workers, max queue size: {max_queue_size}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current job manager statistics."""
        with self.job_lock:
            # Update current counts
            self.stats["current_active"] = len(self.active_jobs)
            self.stats["current_queued"] = len([j for j in self.jobs.values() if j.status == JobStatus.QUEUED])
            return self.stats.copy()
    
    def is_queue_full(self) -> bool:
        """Check if the job queue is full."""
        with self.job_lock:
            total_jobs = len([j for j in self.jobs.values() if j.status in [JobStatus.QUEUED, JobStatus.PROCESSING]])
            return total_jobs >= self.max_queue_size
    
    def submit_job(self, note_id: str, process_function, *args, **kwargs) -> str:
        """
        Submit a new job for processing.
        
        Args:
            note_id: The note ID to process
            process_function: The function to execute for processing
            *args, **kwargs: Arguments to pass to the process function
            
        Returns:
            str: Job ID for tracking
            
        Raises:
            RuntimeError: If queue is full or system is overloaded
        """
        if self.is_queue_full():
            raise RuntimeError(f"Job queue is full (max: {self.max_queue_size}). Please try again later.")
        
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        with self.job_lock:
            # Create job info
            job_info = JobInfo(
                job_id=job_id,
                note_id=note_id,
                status=JobStatus.QUEUED,
                created_at=datetime.now()
            )
            
            # Submit to thread pool
            future = self.executor.submit(self._execute_job, job_info, process_function, *args, **kwargs)
            job_info.future = future
            
            # Store job
            self.jobs[job_id] = job_info
            self.stats["total_submitted"] += 1
            
            print(f"📝 Job {job_id} submitted for note {note_id} (queue size: {len(self.jobs)})")
            
        return job_id
    
    def _execute_job(self, job_info: JobInfo, process_function, *args, **kwargs) -> Any:
        """
        Execute a job with timeout and error handling.
        
        Args:
            job_info: Job information
            process_function: Function to execute
            *args, **kwargs: Arguments for the function
            
        Returns:
            Any: Result from the process function
        """
        try:
            # Mark job as processing
            with self.job_lock:
                job_info.status = JobStatus.PROCESSING
                job_info.started_at = datetime.now()
                self.active_jobs[job_info.job_id] = job_info
            
            print(f"🔄 Job {job_info.job_id} started processing note {job_info.note_id}")
            
            # Execute with timeout
            start_time = time.time()
            result = process_function(job_info.job_id, job_info.note_id, *args, **kwargs)
            duration = time.time() - start_time
            
            # Mark as completed
            with self.job_lock:
                job_info.status = JobStatus.COMPLETED
                job_info.completed_at = datetime.now()
                job_info.result = result
                self.stats["total_completed"] += 1
                
                # Remove from active jobs
                if job_info.job_id in self.active_jobs:
                    del self.active_jobs[job_info.job_id]
            
            print(f"✅ Job {job_info.job_id} completed successfully in {duration:.2f}s")
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            # Mark as failed
            with self.job_lock:
                job_info.status = JobStatus.FAILED
                job_info.completed_at = datetime.now()
                job_info.error = error_msg
                self.stats["total_failed"] += 1
                
                # Remove from active jobs
                if job_info.job_id in self.active_jobs:
                    del self.active_jobs[job_info.job_id]
            
            print(f"❌ Job {job_info.job_id} failed: {error_msg}")
            raise e
    
    def get_job_status(self, job_id: str) -> Optional[JobInfo]:
        """Get status of a specific job."""
        with self.job_lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[JobInfo]:
        """Get all jobs with their current status."""
        with self.job_lock:
            return list(self.jobs.values())
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job if it's still queued or try to interrupt if processing.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            bool: True if successfully cancelled, False otherwise
        """
        with self.job_lock:
            job_info = self.jobs.get(job_id)
            if not job_info:
                return False
            
            if job_info.status == JobStatus.QUEUED and job_info.future:
                # Cancel queued job
                cancelled = job_info.future.cancel()
                if cancelled:
                    job_info.status = JobStatus.FAILED
                    job_info.error = "Job cancelled by user"
                    job_info.completed_at = datetime.now()
                    print(f"🚫 Job {job_id} cancelled")
                return cancelled
            
            elif job_info.status == JobStatus.PROCESSING and job_info.future:
                # Try to interrupt processing job (may not work for all operations)
                job_info.future.cancel()
                print(f"⚠️ Attempted to cancel processing job {job_id}")
                return True
            
            return False
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Clean up old completed/failed jobs to prevent memory leaks.
        
        Args:
            max_age_hours: Maximum age in hours for keeping job records
        """
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self.job_lock:
            jobs_to_remove = []
            
            for job_id, job_info in self.jobs.items():
                if job_info.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.TIMEOUT]:
                    if job_info.created_at.timestamp() < cutoff_time:
                        jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
            
            if jobs_to_remove:
                print(f"🧹 Cleaned up {len(jobs_to_remove)} old job records")
    
    def shutdown(self, wait: bool = True, timeout: float = 30.0):
        """
        Shutdown the job manager and cleanup resources.
        
        Args:
            wait: Whether to wait for running jobs to complete
            timeout: Maximum time to wait for shutdown
        """
        print("🛑 Shutting down ConcurrentJobManager...")
        
        with self.job_lock:
            active_count = len(self.active_jobs)
            if active_count > 0:
                print(f"⏳ Waiting for {active_count} active jobs to complete...")
        
        self.executor.shutdown(wait=wait, timeout=timeout)
        print("✅ ConcurrentJobManager shutdown complete")


# Global job manager instance
_job_manager: Optional[ConcurrentJobManager] = None
_manager_lock = threading.Lock()


def get_job_manager() -> ConcurrentJobManager:
    """Get the global job manager instance (singleton pattern)."""
    global _job_manager
    
    if _job_manager is None:
        with _manager_lock:
            if _job_manager is None:
                _job_manager = ConcurrentJobManager()
    
    return _job_manager


def shutdown_job_manager():
    """Shutdown the global job manager."""
    global _job_manager
    
    if _job_manager is not None:
        with _manager_lock:
            if _job_manager is not None:
                _job_manager.shutdown()
                _job_manager = None