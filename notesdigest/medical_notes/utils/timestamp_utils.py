"""
Timestamp Utility Infrastructure for Medical Notes Processing
Provides consistent epoch timestamp generation and processing lifecycle tracking
"""

from datetime import datetime
from typing import Optional, Dict
import logging

# Configure logging
logger = logging.getLogger(__name__)


class TimestampManager:
    """
    Utility class for generating consistent epoch timestamps and managing timestamp calculations.
    All timestamps are in UTC and use millisecond precision (13-digit integers).
    """
    
    @staticmethod
    def current_epoch_ms() -> int:
        """
        Generate current timestamp in epoch milliseconds format.
        
        Returns:
            int: Current timestamp as 13-digit epoch milliseconds
        """
        try:
            from datetime import timezone
            return int(datetime.now(timezone.utc).timestamp() * 1000)
        except Exception as e:
            logger.error(f"Failed to generate current epoch timestamp: {str(e)}")
            # Fallback to basic timestamp generation
            return int(datetime.now(timezone.utc).timestamp() * 1000)
    
    @staticmethod
    def datetime_to_epoch_ms(dt: datetime) -> int:
        """
        Convert datetime object to epoch milliseconds format.
        
        Args:
            dt: datetime object to convert
            
        Returns:
            int: Timestamp as 13-digit epoch milliseconds
            
        Raises:
            ValueError: If datetime conversion fails
        """
        try:
            if dt is None:
                raise ValueError("Datetime object cannot be None")
            return int(dt.timestamp() * 1000)
        except Exception as e:
            logger.error(f"Failed to convert datetime to epoch: {str(e)}")
            raise ValueError(f"Invalid datetime conversion: {str(e)}")
    
    @staticmethod
    def parse_datetime_to_epoch_ms(dt_str: str) -> Optional[int]:
        """
        Parse datetime string and convert to epoch milliseconds format.
        
        Args:
            dt_str: Datetime string in various formats
            
        Returns:
            Optional[int]: Epoch milliseconds or None if parsing fails
        """
        if not dt_str or not str(dt_str).strip():
            return None
            
        try:
            from dateutil import parser as date_parser
            dt_obj = date_parser.parse(str(dt_str))
            return TimestampManager.datetime_to_epoch_ms(dt_obj)
        except Exception as e:
            logger.warning(f"Failed to parse datetime string '{dt_str}': {str(e)}")
            return None
    
    @staticmethod
    def validate_epoch_timestamp(timestamp: int) -> bool:
        """
        Validate that a timestamp is a valid 13-digit epoch milliseconds value.
        
        Args:
            timestamp: Timestamp to validate
            
        Returns:
            bool: True if valid epoch timestamp, False otherwise
        """
        try:
            # Check if it's an integer
            if not isinstance(timestamp, int):
                return False
            
            # Check if it's 13 digits (epoch milliseconds)
            if len(str(timestamp)) != 13:
                return False
            
            # Check if it represents a reasonable date (after 2000, before 2100)
            # 2000-01-01: 946684800000, 2100-01-01: 4102444800000
            if timestamp < 946684800000 or timestamp > 4102444800000:
                return False
                
            return True
        except Exception:
            return False


class ProcessingTracker:
    """
    Tracks processing lifecycle timestamps throughout the note processing pipeline.
    Maintains temporal ordering and provides access to all processing timestamps.
    """
    
    def __init__(self, note_id: str):
        """
        Initialize processing tracker for a specific note.
        
        Args:
            note_id: Unique identifier for the note being processed
        """
        self.note_id = note_id
        self.timestamps: Dict[str, int] = {}
        self._start_time = TimestampManager.current_epoch_ms()
        
        logger.info(f"ProcessingTracker initialized for note {note_id}")
    
    def mark_ingestion(self) -> int:
        """
        Mark the timestamp when the note was ingested into the system.
        
        Returns:
            int: Ingestion timestamp in epoch milliseconds
        """
        try:
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['ingestion'] = timestamp
            logger.debug(f"Note {self.note_id}: Ingestion marked at {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Failed to mark ingestion for note {self.note_id}: {str(e)}")
            # Use fallback timestamp
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['ingestion'] = timestamp
            return timestamp
    
    def mark_submission(self) -> int:
        """
        Mark the timestamp when the note was submitted for processing.
        
        Returns:
            int: Submission timestamp in epoch milliseconds
        """
        try:
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['submission'] = timestamp
            logger.debug(f"Note {self.note_id}: Submission marked at {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Failed to mark submission for note {self.note_id}: {str(e)}")
            # Use fallback timestamp
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['submission'] = timestamp
            return timestamp
    
    def mark_processing_start(self) -> int:
        """
        Mark the timestamp when note processing began.
        
        Returns:
            int: Processing start timestamp in epoch milliseconds
        """
        try:
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['processing_start'] = timestamp
            logger.debug(f"Note {self.note_id}: Processing start marked at {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Failed to mark processing start for note {self.note_id}: {str(e)}")
            # Use fallback timestamp
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['processing_start'] = timestamp
            return timestamp
    
    def mark_processing_end(self) -> int:
        """
        Mark the timestamp when note processing completed (success or failure).
        
        Returns:
            int: Processing end timestamp in epoch milliseconds
        """
        try:
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['processing_end'] = timestamp
            logger.debug(f"Note {self.note_id}: Processing end marked at {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Failed to mark processing end for note {self.note_id}: {str(e)}")
            # Use fallback timestamp
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['processing_end'] = timestamp
            return timestamp
    
    def mark_processed_at(self) -> int:
        """
        Mark the timestamp when the note was stored/indexed.
        
        Returns:
            int: Processed at timestamp in epoch milliseconds
        """
        try:
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['processed_at'] = timestamp
            logger.debug(f"Note {self.note_id}: Processed at marked at {timestamp}")
            return timestamp
        except Exception as e:
            logger.error(f"Failed to mark processed at for note {self.note_id}: {str(e)}")
            # Use fallback timestamp
            timestamp = TimestampManager.current_epoch_ms()
            self.timestamps['processed_at'] = timestamp
            return timestamp
    
    def get_timestamps(self) -> Dict[str, int]:
        """
        Get all recorded timestamps for this processing session.
        
        Returns:
            Dict[str, int]: Dictionary of timestamp names to epoch milliseconds values
        """
        return self.timestamps.copy()
    
    def get_processing_duration_ms(self) -> Optional[int]:
        """
        Calculate processing duration in milliseconds.
        
        Returns:
            Optional[int]: Duration in milliseconds, or None if start/end not recorded
        """
        start = self.timestamps.get('processing_start')
        end = self.timestamps.get('processing_end')
        
        if start is not None and end is not None:
            return end - start
        return None
    
    def validate_temporal_ordering(self) -> bool:
        """
        Validate that timestamps follow expected temporal ordering.
        
        Returns:
            bool: True if timestamps are in correct order, False otherwise
        """
        try:
            # Expected order: ingestion <= submission <= processing_start <= processing_end <= processed_at
            timestamps = self.timestamps
            
            # Check ingestion <= submission
            if 'ingestion' in timestamps and 'submission' in timestamps:
                if timestamps['ingestion'] > timestamps['submission']:
                    logger.warning(f"Note {self.note_id}: Ingestion timestamp after submission")
                    return False
            
            # Check submission <= processing_start
            if 'submission' in timestamps and 'processing_start' in timestamps:
                if timestamps['submission'] > timestamps['processing_start']:
                    logger.warning(f"Note {self.note_id}: Submission timestamp after processing start")
                    return False
            
            # Check processing_start <= processing_end
            if 'processing_start' in timestamps and 'processing_end' in timestamps:
                if timestamps['processing_start'] > timestamps['processing_end']:
                    logger.warning(f"Note {self.note_id}: Processing start after processing end")
                    return False
            
            # Check processing_end <= processed_at
            if 'processing_end' in timestamps and 'processed_at' in timestamps:
                if timestamps['processing_end'] > timestamps['processed_at']:
                    logger.warning(f"Note {self.note_id}: Processing end after processed at")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to validate temporal ordering for note {self.note_id}: {str(e)}")
            return False


# Global processing tracker instance for current processing job
_current_tracker: Optional[ProcessingTracker] = None


def init_processing_tracker(note_id: str) -> ProcessingTracker:
    """
    Initialize a new processing tracker for a note processing job.
    
    Args:
        note_id: Unique identifier for the note being processed
        
    Returns:
        ProcessingTracker: Initialized tracker instance
    """
    global _current_tracker
    _current_tracker = ProcessingTracker(note_id=note_id)
    return _current_tracker


def get_current_processing_tracker() -> Optional[ProcessingTracker]:
    """
    Get the current processing tracker instance.
    
    Returns:
        Optional[ProcessingTracker]: Current tracker or None if not initialized
    """
    global _current_tracker
    return _current_tracker


def clear_processing_tracker() -> Optional[ProcessingTracker]:
    """
    Get the current tracker and clear the global reference.
    
    Returns:
        Optional[ProcessingTracker]: Previous tracker instance or None
    """
    global _current_tracker
    tracker = _current_tracker
    _current_tracker = None
    return tracker