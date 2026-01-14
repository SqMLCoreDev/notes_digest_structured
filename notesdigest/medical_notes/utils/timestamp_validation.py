"""
Comprehensive Error Handling and Validation for Timestamp Tracking
Provides fallback mechanisms, validation, and error recovery for timestamp operations
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class TimestampValidationError(Exception):
    """Custom exception for timestamp validation errors"""
    pass


class TimestampErrorHandler:
    """
    Handles errors and provides fallback mechanisms for timestamp operations.
    Ensures processing continues even if timestamp operations fail.
    """
    
    @staticmethod
    def safe_timestamp_generation(operation_name: str = "unknown") -> int:
        """
        Safely generate a current timestamp with fallback mechanisms.
        
        Args:
            operation_name: Name of the operation for logging
            
        Returns:
            int: Current timestamp in epoch milliseconds
        """
        try:
            from medical_notes.utils.timestamp_utils import TimestampManager
            return TimestampManager.current_epoch_ms()
        except Exception as e:
            logger.warning(f"Primary timestamp generation failed for {operation_name}: {str(e)}")
            
            # Fallback 1: Basic datetime conversion
            try:
                from datetime import timezone
                return int(datetime.now(timezone.utc).timestamp() * 1000)
            except Exception as e2:
                logger.error(f"Fallback timestamp generation failed for {operation_name}: {str(e2)}")
                
                # Fallback 2: Hardcoded reasonable timestamp (should never happen)
                # This represents a timestamp from 2024 as absolute fallback
                return 1704067200000  # 2024-01-01 00:00:00 UTC
    
    @staticmethod
    def validate_and_correct_timestamp(timestamp: Any, field_name: str = "unknown") -> int:
        """
        Validate a timestamp value and correct it if invalid.
        
        Args:
            timestamp: Timestamp value to validate
            field_name: Name of the field for logging
            
        Returns:
            int: Valid timestamp in epoch milliseconds
        """
        try:
            from medical_notes.utils.timestamp_utils import TimestampManager
            
            # Handle None values
            if timestamp is None:
                logger.warning(f"Null timestamp for {field_name}, using current time")
                return TimestampErrorHandler.safe_timestamp_generation(f"null_{field_name}")
            
            # Convert to int if possible
            try:
                timestamp_int = int(timestamp)
            except (ValueError, TypeError):
                logger.warning(f"Non-numeric timestamp for {field_name}: {timestamp}, using current time")
                return TimestampErrorHandler.safe_timestamp_generation(f"non_numeric_{field_name}")
            
            # Validate format
            if TimestampManager.validate_epoch_timestamp(timestamp_int):
                return timestamp_int
            else:
                logger.warning(f"Invalid timestamp format for {field_name}: {timestamp_int}, using current time")
                return TimestampErrorHandler.safe_timestamp_generation(f"invalid_format_{field_name}")
                
        except Exception as e:
            logger.error(f"Timestamp validation failed for {field_name}: {str(e)}")
            return TimestampErrorHandler.safe_timestamp_generation(f"validation_error_{field_name}")
    
    @staticmethod
    def validate_temporal_ordering(timestamps: Dict[str, int], note_id: str = "unknown") -> List[str]:
        """
        Validate temporal ordering of timestamps and return list of issues.
        
        Args:
            timestamps: Dictionary of timestamp names to values
            note_id: Note ID for logging
            
        Returns:
            List[str]: List of temporal ordering issues found
        """
        issues = []
        
        try:
            # Expected order: ingestion <= submission <= processing_start <= processing_end <= processed_at
            ordering_checks = [
                ('ingestion', 'submission', 'Ingestion should occur before or at submission'),
                ('submission', 'processing_start', 'Submission should occur before or at processing start'),
                ('processing_start', 'processing_end', 'Processing start should occur before processing end'),
                ('processing_end', 'processed_at', 'Processing end should occur before or at processed_at')
            ]
            
            for earlier_key, later_key, message in ordering_checks:
                earlier_ts = timestamps.get(earlier_key)
                later_ts = timestamps.get(later_key)
                
                if earlier_ts is not None and later_ts is not None:
                    if earlier_ts > later_ts:
                        issue = f"{message} (note {note_id}): {earlier_key}={earlier_ts} > {later_key}={later_ts}"
                        issues.append(issue)
                        logger.warning(issue)
            
            return issues
            
        except Exception as e:
            error_msg = f"Temporal ordering validation failed for note {note_id}: {str(e)}"
            logger.error(error_msg)
            issues.append(error_msg)
            return issues
    
    @staticmethod
    def safe_processing_tracker_operation(tracker, operation: str, note_id: str = "unknown") -> Optional[int]:
        """
        Safely execute a processing tracker operation with error handling.
        
        Args:
            tracker: ProcessingTracker instance
            operation: Operation name ('mark_ingestion', 'mark_submission', etc.)
            note_id: Note ID for logging
            
        Returns:
            Optional[int]: Timestamp if successful, None if failed
        """
        try:
            if tracker is None:
                logger.warning(f"ProcessingTracker is None for {operation} on note {note_id}")
                return None
            
            method = getattr(tracker, operation, None)
            if method is None:
                logger.error(f"ProcessingTracker method {operation} not found for note {note_id}")
                return None
            
            return method()
            
        except Exception as e:
            logger.error(f"ProcessingTracker {operation} failed for note {note_id}: {str(e)}")
            return None


class TimestampFieldValidator:
    """
    Validates timestamp fields in records and data structures.
    Provides comprehensive validation for all timestamp-related fields.
    """
    
    # Define expected timestamp fields for each index
    PROCESSED_NOTES_TIMESTAMP_FIELDS = [
        'ingestionDateTimeAsEpoch',
        'submitDateEpoch', 
        'processedDateTimeEpoch'
    ]
    
    TOKEN_USAGE_TIMESTAMP_FIELDS = [
        'processedAtEpoch',
        'processingTimeStartEpoch',
        'processingTimeEndEpoch'
    ]
    
    @classmethod
    def validate_processed_notes_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate timestamp fields in a processed notes record.
        
        Args:
            record: Record dictionary to validate
            
        Returns:
            Dict[str, Any]: Validated record with corrected timestamps
        """
        validated_record = record.copy()
        issues = []
        
        try:
            note_id = record.get('noteId', 'unknown')
            
            # Validate each timestamp field
            for field in cls.PROCESSED_NOTES_TIMESTAMP_FIELDS:
                if field in validated_record:
                    original_value = validated_record[field]
                    corrected_value = TimestampErrorHandler.validate_and_correct_timestamp(
                        original_value, field
                    )
                    
                    if original_value != corrected_value:
                        issues.append(f"Corrected {field}: {original_value} -> {corrected_value}")
                    
                    validated_record[field] = corrected_value
            
            # Validate temporal ordering
            timestamps = {
                'ingestion': validated_record.get('ingestionDateTimeAsEpoch'),
                'submission': validated_record.get('submitDateEpoch'),
                'processed_at': validated_record.get('processedDateTimeEpoch')
            }
            
            ordering_issues = TimestampErrorHandler.validate_temporal_ordering(timestamps, str(note_id))
            issues.extend(ordering_issues)
            
            # Add validation issues to processing issues if they exist
            if issues:
                existing_issues = validated_record.get('processingIssues', '')
                validation_issues_str = '; '.join([f"Timestamp validation: {issue}" for issue in issues])
                
                if existing_issues:
                    validated_record['processingIssues'] = f"{existing_issues}; {validation_issues_str}"
                else:
                    validated_record['processingIssues'] = validation_issues_str
            
            return validated_record
            
        except Exception as e:
            logger.error(f"Record validation failed: {str(e)}")
            # Return original record if validation fails completely
            return record
    
    @classmethod
    def validate_token_usage_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate timestamp fields in a token usage record.
        
        Args:
            record: Record dictionary to validate
            
        Returns:
            Dict[str, Any]: Validated record with corrected timestamps
        """
        validated_record = record.copy()
        
        try:
            document_id = record.get('documentId', 'unknown')
            
            # Validate each timestamp field
            for field in cls.TOKEN_USAGE_TIMESTAMP_FIELDS:
                if field in validated_record:
                    original_value = validated_record[field]
                    corrected_value = TimestampErrorHandler.validate_and_correct_timestamp(
                        original_value, field
                    )
                    validated_record[field] = corrected_value
            
            # Validate temporal ordering
            timestamps = {
                'processing_start': validated_record.get('processingTimeStartEpoch'),
                'processing_end': validated_record.get('processingTimeEndEpoch'),
                'processed_at': validated_record.get('processedAtEpoch')
            }
            
            TimestampErrorHandler.validate_temporal_ordering(timestamps, str(document_id))
            
            return validated_record
            
        except Exception as e:
            logger.error(f"Token usage record validation failed: {str(e)}")
            # Return original record if validation fails completely
            return record
    
    @classmethod
    def validate_field_name_uniqueness(cls, record: Dict[str, Any], index_type: str = "processed_notes") -> List[str]:
        """
        Validate that timestamp field names are unique within the record.
        
        Args:
            record: Record dictionary to check
            index_type: Type of index ("processed_notes" or "token_usage")
            
        Returns:
            List[str]: List of duplicate field issues found
        """
        issues = []
        
        try:
            if index_type == "processed_notes":
                expected_fields = cls.PROCESSED_NOTES_TIMESTAMP_FIELDS
            elif index_type == "token_usage":
                expected_fields = cls.TOKEN_USAGE_TIMESTAMP_FIELDS
            else:
                return [f"Unknown index type: {index_type}"]
            
            # Check for duplicate field names (should not happen in practice)
            field_counts = {}
            for field in record.keys():
                if field.endswith('Epoch'):
                    field_counts[field] = field_counts.get(field, 0) + 1
            
            duplicates = [field for field, count in field_counts.items() if count > 1]
            if duplicates:
                issues.append(f"Duplicate timestamp fields found: {duplicates}")
            
            # Check for missing expected fields
            missing_fields = [field for field in expected_fields if field not in record]
            if missing_fields:
                issues.append(f"Missing expected timestamp fields: {missing_fields}")
            
            return issues
            
        except Exception as e:
            logger.error(f"Field uniqueness validation failed: {str(e)}")
            return [f"Field uniqueness validation error: {str(e)}"]


def ensure_processing_continues(func):
    """
    Decorator to ensure processing continues even if timestamp operations fail.
    Logs errors but does not raise exceptions.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Timestamp operation failed in {func.__name__}: {str(e)}")
            # Return a safe default value based on function name
            if 'timestamp' in func.__name__.lower() or 'epoch' in func.__name__.lower():
                return TimestampErrorHandler.safe_timestamp_generation(func.__name__)
            return None
    return wrapper


# Convenience functions for common validation operations
def validate_and_log_timestamps(record: Dict[str, Any], index_type: str = "processed_notes") -> Dict[str, Any]:
    """
    Validate timestamps in a record and log any issues found.
    
    Args:
        record: Record to validate
        index_type: Type of index for validation rules
        
    Returns:
        Dict[str, Any]: Validated record
    """
    if index_type == "processed_notes":
        return TimestampFieldValidator.validate_processed_notes_record(record)
    elif index_type == "token_usage":
        return TimestampFieldValidator.validate_token_usage_record(record)
    else:
        logger.warning(f"Unknown index type for validation: {index_type}")
        return record


def log_timestamp_summary(timestamps: Dict[str, int], note_id: str = "unknown"):
    """
    Log a summary of timestamps for debugging and monitoring.
    
    Args:
        timestamps: Dictionary of timestamp names to values
        note_id: Note ID for logging context
    """
    try:
        logger.info(f"Timestamp summary for note {note_id}:")
        for name, timestamp in timestamps.items():
            if timestamp is not None:
                # Convert to human-readable format for logging
                try:
                    dt = datetime.fromtimestamp(timestamp / 1000)
                    logger.info(f"  {name}: {timestamp} ({dt.isoformat()})")
                except:
                    logger.info(f"  {name}: {timestamp} (invalid format)")
            else:
                logger.info(f"  {name}: None")
                
        # Calculate durations if possible
        if 'processing_start' in timestamps and 'processing_end' in timestamps:
            start = timestamps['processing_start']
            end = timestamps['processing_end']
            if start and end:
                duration_ms = end - start
                logger.info(f"  Processing duration: {duration_ms}ms ({duration_ms/1000:.2f}s)")
                
    except Exception as e:
        logger.error(f"Failed to log timestamp summary for note {note_id}: {str(e)}")