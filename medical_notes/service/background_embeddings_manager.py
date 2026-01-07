"""
Background Embeddings Manager for Medical Notes Processing
Handles asynchronous embeddings generation using a background task queue
"""

import threading
import time
import queue
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
import uuid

from medical_notes.config.config import (
    MAX_EMBEDDINGS_WORKERS,
    EMBEDDINGS_QUEUE_SIZE,
    EMBEDDINGS_PROCESSING_TIMEOUT
)

# Set up logging
logger = logging.getLogger(__name__)


class EmbeddingsTaskStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class EmbeddingsTask:
    task_id: str
    note_id: str
    status: EmbeddingsTaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3


class BackgroundEmbeddingsManager:
    """
    Manages background processing of embeddings with queue management and worker threads.
    """
    
    def __init__(self, max_workers: int = None, queue_size: int = None):
        # Import config values with fallbacks
        try:
            from medical_notes.config.config import MAX_EMBEDDINGS_WORKERS, EMBEDDINGS_QUEUE_SIZE
            self.max_workers = max_workers or MAX_EMBEDDINGS_WORKERS
            self.queue_size = queue_size or EMBEDDINGS_QUEUE_SIZE
        except ImportError:
            # Fallback values if config import fails
            self.max_workers = max_workers or 2
            self.queue_size = queue_size or 100
        
        # Task queue and tracking
        self.task_queue = queue.Queue(maxsize=self.queue_size)
        self.tasks: Dict[str, EmbeddingsTask] = {}
        self.task_lock = threading.RLock()
        
        # Worker threads
        self.workers: List[threading.Thread] = []
        self.shutdown_event = threading.Event()
        self.running = False
        
        # Statistics
        self.stats = {
            "total_queued": 0,
            "total_completed": 0,
            "total_failed": 0,
            "current_queue_size": 0,
            "active_workers": 0
        }
        
        logger.info(f"BackgroundEmbeddingsManager initialized with {self.max_workers} workers, queue size: {self.queue_size}")
    
    def start(self):
        """Start the background embeddings workers."""
        if self.running:
            logger.warning("BackgroundEmbeddingsManager is already running")
            return
        
        self.running = True
        self.shutdown_event.clear()
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"EmbeddingsWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {len(self.workers)} embeddings worker threads")
    
    def stop(self, timeout: float = 30.0):
        """Stop the background embeddings workers."""
        if not self.running:
            logger.warning("BackgroundEmbeddingsManager is not running")
            return
        
        logger.info("Stopping BackgroundEmbeddingsManager...")
        self.shutdown_event.set()
        self.running = False
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=timeout)
            if worker.is_alive():
                logger.warning(f"Worker {worker.name} did not stop gracefully")
        
        self.workers.clear()
        logger.info("BackgroundEmbeddingsManager stopped")
    
    def queue_embeddings_task(self, note_id: str, priority: bool = False) -> str:
        """
        Queue an embeddings task for background processing.
        
        Args:
            note_id: The note ID to process embeddings for
            priority: If True, add to front of queue (for failed processing cases)
            
        Returns:
            str: Task ID for tracking
            
        Raises:
            RuntimeError: If queue is full
        """
        if not self.running:
            raise RuntimeError("BackgroundEmbeddingsManager is not running. Call start() first.")
        
        task_id = f"emb_{uuid.uuid4().hex[:12]}"
        
        try:
            # Create task
            task = EmbeddingsTask(
                task_id=task_id,
                note_id=note_id,
                status=EmbeddingsTaskStatus.QUEUED,
                created_at=datetime.now()
            )
            
            with self.task_lock:
                # Store task
                self.tasks[task_id] = task
                
                # Add to queue
                if priority:
                    # For priority tasks (failed processing), we'll use a simple approach
                    # In a production system, you might want a priority queue
                    self.task_queue.put(task, block=False)
                else:
                    self.task_queue.put(task, block=False)
                
                self.stats["total_queued"] += 1
                self.stats["current_queue_size"] = self.task_queue.qsize()
            
            logger.info(f"Queued embeddings task {task_id} for note {note_id} (priority: {priority})")
            return task_id
            
        except queue.Full:
            raise RuntimeError(f"Embeddings queue is full (max: {self.queue_size}). Please try again later.")
    
    def _worker_loop(self):
        """Main worker loop for processing embeddings tasks."""
        worker_name = threading.current_thread().name
        logger.info(f"{worker_name} started")
        
        while not self.shutdown_event.is_set():
            try:
                # Get task from queue with timeout
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the task
                self._process_embeddings_task(task, worker_name)
                
                # Mark task as done
                self.task_queue.task_done()
                
                # Update queue size stat
                with self.task_lock:
                    self.stats["current_queue_size"] = self.task_queue.qsize()
                
            except Exception as e:
                logger.error(f"{worker_name} encountered error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        logger.info(f"{worker_name} stopped")
    
    def _process_embeddings_task(self, task: EmbeddingsTask, worker_name: str):
        """Process a single embeddings task."""
        try:
            # Mark task as processing
            with self.task_lock:
                task.status = EmbeddingsTaskStatus.PROCESSING
                task.started_at = datetime.now()
                self.stats["active_workers"] += 1
            
            logger.info(f"{worker_name} processing embeddings for note {task.note_id}")
            
            # Import and process embeddings
            from medical_notes.service.embeddings import process_note_embeddings, EmbeddingsServiceError
            
            start_time = time.time()
            result = process_note_embeddings(task.note_id)
            duration = time.time() - start_time
            
            # Mark as completed
            with self.task_lock:
                task.status = EmbeddingsTaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result
                self.stats["total_completed"] += 1
                self.stats["active_workers"] -= 1
            
            logger.info(f"{worker_name} completed embeddings for note {task.note_id} in {duration:.2f}s: "
                       f"{result.get('chunks_processed', 0)} chunks processed")
            
        except EmbeddingsServiceError as e:
            self._handle_task_failure(task, worker_name, str(e), retry=True)
        except Exception as e:
            self._handle_task_failure(task, worker_name, str(e), retry=False)
    
    def _handle_task_failure(self, task: EmbeddingsTask, worker_name: str, error_msg: str, retry: bool = True):
        """Handle task failure with optional retry logic."""
        with self.task_lock:
            task.error = error_msg
            task.retry_count += 1
            self.stats["active_workers"] -= 1
            
            # Check if we should retry
            if retry and task.retry_count <= task.max_retries:
                logger.warning(f"{worker_name} embeddings failed for note {task.note_id} "
                              f"(attempt {task.retry_count}/{task.max_retries}): {error_msg}")
                
                # Reset status and requeue
                task.status = EmbeddingsTaskStatus.QUEUED
                task.started_at = None
                
                try:
                    # Add back to queue for retry
                    self.task_queue.put(task, block=False)
                    logger.info(f"Requeued embeddings task for note {task.note_id} (retry {task.retry_count})")
                except queue.Full:
                    logger.error(f"Failed to requeue embeddings task for note {task.note_id}: queue full")
                    task.status = EmbeddingsTaskStatus.FAILED
                    task.completed_at = datetime.now()
                    self.stats["total_failed"] += 1
            else:
                # Max retries exceeded or no retry requested
                task.status = EmbeddingsTaskStatus.FAILED
                task.completed_at = datetime.now()
                self.stats["total_failed"] += 1
                
                logger.error(f"{worker_name} embeddings permanently failed for note {task.note_id} "
                            f"after {task.retry_count} attempts: {error_msg}")
    
    def get_task_status(self, task_id: str) -> Optional[EmbeddingsTask]:
        """Get status of a specific embeddings task."""
        with self.task_lock:
            return self.tasks.get(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current embeddings manager statistics."""
        with self.task_lock:
            stats = self.stats.copy()
            stats["current_queue_size"] = self.task_queue.qsize()
            return stats
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks to prevent memory leaks."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self.task_lock:
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                if task.status in [EmbeddingsTaskStatus.COMPLETED, EmbeddingsTaskStatus.FAILED]:
                    if task.created_at.timestamp() < cutoff_time:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
            
            if tasks_to_remove:
                logger.info(f"Cleaned up {len(tasks_to_remove)} old embeddings task records")


# Global embeddings manager instance
_embeddings_manager: Optional[BackgroundEmbeddingsManager] = None
_manager_lock = threading.Lock()


def get_embeddings_manager() -> BackgroundEmbeddingsManager:
    """Get the global embeddings manager instance (singleton pattern)."""
    global _embeddings_manager
    
    if _embeddings_manager is None:
        with _manager_lock:
            if _embeddings_manager is None:
                _embeddings_manager = BackgroundEmbeddingsManager()
    
    return _embeddings_manager


def start_embeddings_manager():
    """Start the global embeddings manager."""
    manager = get_embeddings_manager()
    manager.start()


def stop_embeddings_manager():
    """Stop the global embeddings manager."""
    global _embeddings_manager
    
    if _embeddings_manager is not None:
        with _manager_lock:
            if _embeddings_manager is not None:
                _embeddings_manager.stop()
                _embeddings_manager = None


def queue_note_for_embeddings(note_id: str, priority: bool = False) -> str:
    """
    Convenience function to queue a note for embeddings processing.
    
    Args:
        note_id: The note ID to process embeddings for
        priority: If True, prioritize this task (for failed processing cases)
        
    Returns:
        str: Task ID for tracking
    """
    manager = get_embeddings_manager()
    return manager.queue_embeddings_task(note_id, priority=priority)


def get_embeddings_task_status(task_id: str) -> Optional[EmbeddingsTask]:
    """Get status of a specific embeddings task."""
    manager = get_embeddings_manager()
    return manager.get_task_status(task_id)


def get_embeddings_stats() -> Dict[str, Any]:
    """Get embeddings manager statistics."""
    manager = get_embeddings_manager()
    return manager.get_stats()