"""
Medical Notes Processing API - Concurrent Processing Implementation
Tracks: processedDateTime, processingIssues, submitDateTime, submittingIssues
Features: Extracts patientMRN, fetches N previous visits by dateOfService (not noteId sequence)
Only uses dateOfServiceEpoch (no serviceDay, serviceMonth, serviceYear)

Processing Mode: CONCURRENT (multiple notes processed in parallel by default)

Indices used:
- tiamd_prod_clinical_notes (source data)
- tiamd_prod_processed_notes (processed output)
- tiamd_prod_notes_digest (digest summaries)

Processing Logic:
- On SUCCESS: status='processed' in both indices, processingIssues=''
- On FAILURE: status='' in clinical_notes, push to processed_notes with processingIssues filled
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import uuid
import asyncio
import time
from contextlib import asynccontextmanager
import pandas as pd
from datetime import datetime as dt
import os

# Import processing function
from medical_notes.service.medical_notes_processor import process_single_note, normalize_note_type

# Import centralized configuration
from medical_notes.config.config import (
    ES_INDEX_CLINICAL_NOTES,
    ES_INDEX_PROCESSED_NOTES,
    ES_INDEX_NOTES_DIGEST,
    ES_INDEX_TOKEN_USAGE,
    N_PREVIOUS_VISITS,
    ENABLE_DATA_FLATTENING,
    MAX_CONCURRENT_NOTES,
    MAX_QUEUE_SIZE
)

# Import data flattening functionality
from medical_notes.utils.data_flattening import flatten_all_nested_objects

# Import token tracking
from medical_notes.service.token_tracker import init_tracker, get_and_clear_tracker, TokenTracker

# Import concurrent processing
from medical_notes.service.concurrent_job_manager import get_job_manager, shutdown_job_manager
from medical_notes.service.rate_limiter import get_bedrock_rate_limiter

# In-memory storage for job logs and status (legacy support)
jobs_db = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Medical Notes API starting... (Concurrent processing: {MAX_CONCURRENT_NOTES} workers, Historical context: {N_PREVIOUS_VISITS} previous visits)")
    
    # Initialize job manager and rate limiter
    job_manager = get_job_manager()
    rate_limiter = get_bedrock_rate_limiter()
    
    print(f"📊 Concurrency settings: Max workers: {MAX_CONCURRENT_NOTES}, Max queue: {MAX_QUEUE_SIZE}")
    
    yield
    
    print("👋 Medical Notes API shutting down...")
    shutdown_job_manager()

app = FastAPI(
    title="Medical Notes API - Concurrent Processing",
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/notes-processor"
)

# Include routers
from medical_notes.routes.process_routes import router as process_router
from medical_notes.routes.status_routes import router as status_router
from medical_notes.routes.debug_routes import router as debug_router

app.include_router(process_router)
app.include_router(status_router)
app.include_router(debug_router)


# Pydantic models moved to routes/process_routes.py


def parse_service_date_to_epoch(date_of_service: str) -> Optional[int]:
    """
    Parse dateOfService and create dateOfServiceEpoch field.
    UPDATED: Now handles timestamps in dateOfService (e.g., "6/28/2025 9:27 AM" or "MM/DD/YYYY HH:MM AM/PM")
    
    Args:
        date_of_service: Date string in format YYYY-MM-DD, MM/DD/YYYY, or MM/DD/YYYY HH:MM AM/PM
    
    Returns:
        int or None: Epoch milliseconds or None if parsing fails
    """
    if not date_of_service:
        return None
        
    try:
        # First, try using dateutil parser (handles timestamps automatically)
        try:
            from dateutil import parser as date_parser
            date_obj = date_parser.parse(date_of_service)
            # Convert to epoch (milliseconds since 1970-01-01)
            epoch_ms = int(date_obj.timestamp() * 1000)
            print(f"    ✓ Parsed date with timestamp: '{date_of_service}' -> epoch {epoch_ms}")
            return epoch_ms
        except:
            pass  # Fall back to manual parsing
        
        # Fallback: Try parsing common date formats (without timestamp)
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%m-%d-%Y', '%m/%d/%Y']:
            try:
                # Extract just the date part if timestamp is present
                date_part = date_of_service.split()[0] if ' ' in date_of_service else date_of_service
                date_obj = dt.strptime(date_part, fmt)
                # Convert to epoch (milliseconds since 1970-01-01)
                epoch_ms = int(date_obj.timestamp() * 1000)
                print(f"    ✓ Parsed date (extracted date part): '{date_part}' -> epoch {epoch_ms}")
                return epoch_ms
            except ValueError:
                continue
        
        # If no format matched, return None
        print(f"    ⚠️ Could not parse date '{date_of_service}' - no format matched")
        return None
        
    except Exception as e:
        print(f"    ⚠️ Error parsing date '{date_of_service}': {str(e)}")
        return None


def add_log(job_id: str, stage: str, status: str, message: str):
    """Add a log entry to the job"""
    if job_id in jobs_db:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "status": status,
            "message": message
        }
        jobs_db[job_id]['logs'].append(log_entry)
        jobs_db[job_id]['current_stage'] = stage
        print(f"[{job_id}] [{stage}] {status}: {message}")



def push_failed_record_to_processed_notes(job_id: str, note_id: str, note_data: dict, 
                                          note_type: Optional[str], patient_mrn: Optional[str],
                                          llm_processing_issues: List[str]):
    """
    Push a record to tiamd_prod_processed_notes when processing fails
    This captures the failure with processingIssues populated (LLM-related errors only)
    
    Args:
        job_id: Job ID for logging
        note_id: The noteId
        note_data: Original note data from tiamd_prod_clinical_notes
        note_type: Note type (if extracted, else None)
        patient_mrn: Patient MRN (if extracted, else None)
        llm_processing_issues: List of LLM-related issues encountered
    """
    try:
        from medical_notes.service.medical_notes_processor import prepare_es_record
        from medical_notes.repository.elastic_search import df_to_es_load
        
        add_log(job_id, "push_failed_record", "in_progress", 
                "Pushing failed record to tiamd_prod_processed_notes with LLM processingIssues")
        
        # Prepare record with empty/null processed fields
        es_record = prepare_es_record(
            note_data=note_data,
            note_type=note_type,
            processed_text='',  # Empty - processing failed
            processed_json=None,   # No longer using processed_json
            soap_text='',        # Empty - processing failed
            soap_json=None,        # No longer using soap_json
            processing_issues=llm_processing_issues  # Only LLM-related issues
        )
        
        es_record['noteId'] = note_id
        es_record['notesProcessedStatus'] = ''  # Empty status - processing failed
        
        es_df = pd.DataFrame([es_record])
        df_to_es_load(es_df, ES_INDEX_PROCESSED_NOTES)
        
        composite_key = es_record.get('_id', 'N/A')
        processed_datetime = es_record.get('processedDateTime', 'N/A')
        processing_issues_str = es_record.get('processingIssues', '')
        
        add_log(job_id, "push_failed_record", "completed", 
                f"Failed record pushed with noteId '{note_id}', composite_key '{composite_key}', processingIssues: {processing_issues_str}")
        
        return True
        
    except Exception as e:
        add_log(job_id, "push_failed_record", "failed", f"Error pushing failed record: {str(e)}")
        return False


def update_submit_tracking(note_id: str, composite_key: str, submit_datetime: str, submitting_issues: str):
    """
    Update submitDateTime and submittingIssues in tiamd_prod_processed_notes after API push
    Uses BOTH noteId and composite_key to ensure only ONE document is updated
    
    Args:
        note_id: The noteId
        composite_key: The composite key for exact document identification
        submit_datetime: Timestamp when submitted to API
        submitting_issues: Any issues during API submission (empty string if none)
    """
    from medical_notes.repository.elastic_search import update_submit_tracking_precise
    
    try:
        time.sleep(10)  # Small delay to ensure ES indexing consistency
        # Update using BOTH noteId and composite_key for precise targeting
        result = update_submit_tracking_precise(
            note_id=note_id,
            composite_key=composite_key,
            submit_datetime=submit_datetime,
            submitting_issues=submitting_issues
        )
        
        if result:
            print(f"    ✓ Updated submitDateTime and submittingIssues for noteId '{note_id}' with composite_key '{composite_key}'")
            return True
        else:
            print(f"    ⚠️ Failed to update submit tracking for noteId '{note_id}' with composite_key '{composite_key}'")
            return False
            
    except Exception as e:
        print(f"    ✗ Error updating submit tracking: {str(e)}")
        return False


def update_patient_mrn_in_clinical_notes(job_id: str, note_id: str, patient_mrn: str, date_of_service: str):
    """
    Update patientMRN and dateOfServiceEpoch in tiamd_prod_clinical_notes index
    
    Args:
        job_id: Job ID for logging
        note_id: The noteId
        patient_mrn: Extracted patient MRN
        date_of_service: Date of service to parse
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from medical_notes.repository.elastic_search import update_from_dataframe
        
        add_log(job_id, "update_mrn", "in_progress", 
                f"Updating patientMRN='{patient_mrn}' and dateOfServiceEpoch in tiamd_prod_clinical_notes for noteId '{note_id}'")
        
        # Parse to epoch only
        epoch_ms = parse_service_date_to_epoch(date_of_service)
        
        update_df = pd.DataFrame([{
            'noteId': note_id,
            'patientMRN': patient_mrn,
            'dateOfServiceEpoch': epoch_ms
        }])
        
        update_result = update_from_dataframe(
            ES_INDEX_CLINICAL_NOTES,
            update_df,
            fields_to_update=['patientMRN', 'dateOfServiceEpoch']
        )
        
        add_log(job_id, "update_mrn", "completed", 
                f"patientMRN '{patient_mrn}' and dateOfServiceEpoch updated in tiamd_prod_clinical_notes for noteId '{note_id}'")
        
        return True
        
    except Exception as e:
        add_log(job_id, "update_mrn", "failed", f"Error updating patientMRN and dateOfServiceEpoch: {str(e)}")
        return False



def fetch_previous_visits(job_id: str, patient_mrn: str, current_service_date: str, 
                         current_note_id: str, n: int):
    """
    Fetch N previous visits for a patient from tiamd_prod_processed_notes
    SORTED BY dateOfService (not noteId sequence)
    FILTERED BY: 
        1. patientMRN = current patient MRN (PRIMARY)
        2. dateOfService < current service date
        3. noteId < current noteId (to handle reprocessing scenarios)
    
    Example: For patient MRN 49398 with noteIds [1,2,3,4]
    - When processing noteId 3: Returns noteIds 1,2 only (excludes 4)
    - When reprocessing noteId 3: Still returns noteIds 1,2 only
    
    Args:
        job_id: Job ID for logging
        patient_mrn: Patient MRN (e.g., "49398")
        current_service_date: Current visit's service date (e.g., "2025-10-22")
        current_note_id: Current noteId (e.g., "3")
        n: Number of previous visits to fetch
    
    Returns:
        list: List of previous visit dictionaries with dateOfService and notesProcessedText
    """
    try:
        from medical_notes.repository.elastic_search import get_previous_visits_by_mrn_and_noteid
        
        add_log(job_id, "fetch_previous_visits", "in_progress", 
                f"Fetching last {n} previous visit(s) for MRN '{patient_mrn}' WHERE dateOfService < '{current_service_date}' AND noteId < '{current_note_id}'")
        
        # Call ES fetcher with both date and noteId filtering
        previous_visits = get_previous_visits_by_mrn_and_noteid(
            index_name=ES_INDEX_PROCESSED_NOTES,
            mrn=patient_mrn,
            current_service_date=current_service_date,
            current_note_id=current_note_id,  # NEW: Pass current noteId for filtering
            n=n,
            fields=["dateOfService", "notesProcessedText", "patientmrn", "noteId"]
        )

        if previous_visits:
            add_log(job_id, "fetch_previous_visits", "completed", 
                    f"Found {len(previous_visits)} previous visit(s) for MRN '{patient_mrn}'")
            
            # Log details of found visits
            for i, visit in enumerate(previous_visits, 1):
                visit_date = visit.get('dateOfService', 'Unknown')
                visit_note_id = visit.get('noteId', 'Unknown')
                text_length = len(visit.get('notesProcessedText', ''))
                add_log(job_id, "fetch_previous_visits", "info", 
                       f"  Visit {i}: noteId={visit_note_id}, date={visit_date}, text={text_length} chars")
        else:
            add_log(job_id, "fetch_previous_visits", "completed", 
                    f"No previous visits found for MRN '{patient_mrn}' with dateOfService < '{current_service_date}' AND noteId < '{current_note_id}'")
        
        return previous_visits
        
    except Exception as e:
        add_log(job_id, "fetch_previous_visits", "failed", 
                f"Error fetching previous visits: {str(e)}")
        return []


def combine_with_historical_context(current_rawdata: str, previous_visits: list, current_date_time: str = None) -> str:
    """
    Combine current rawdata with historical context from previous visits
    
    Args:
        current_rawdata: Current visit's raw text
        previous_visits: List of previous visit dictionaries (sorted by date DESC)
        current_date_time: Current date and time to prepend (format: MM/DD/YYYY HH:MM AM/PM)
    
    Returns:
        str: Combined text with historical context
    """
    # Get current date and time if not provided
    if not current_date_time:
        now = datetime.now()
        month = str(now.month)
        day = str(now.day)
        year = str(now.year)
        hour_12 = now.strftime("%I").lstrip("0") or "12"
        minute = now.strftime("%M")
        am_pm = now.strftime("%p")
        current_date_time = f"{month}/{day}/{year} {hour_12}:{minute} {am_pm}"
    
    # Build historical context (oldest first for chronological order)
    historical_context = ""
    if previous_visits:
        for visit in reversed(previous_visits):  # Reverse to get oldest first
            date_of_service = visit.get('dateOfService', 'Unknown Date')
            note_id = visit.get('noteId', 'Unknown')
            processed_text = visit.get('notesProcessedText', '')
            
            if processed_text:
                historical_context += f"\n{'='*80}\n"
                historical_context += f"PREVIOUS VISIT [Date: {date_of_service}, NoteID: {note_id}]\n"
                historical_context += f"{'='*80}\n"
                historical_context += f"{processed_text}\n"
    
    # Combine with current visit - prepend current date/time as Date of Service
    combined_text = f"{historical_context}\n{'='*80}\n"
    combined_text += f"CURRENT VISIT\n"
    combined_text += f"Date of Service: {current_date_time}\n"
    combined_text += f"{'='*80}\n"
    combined_text += f"{current_rawdata}"
    
    return combined_text


async def process_note_async(job_id: str, note_id: str):
    """Process the medical note asynchronously"""
    try:
        result = await process_note_with_tracking(job_id, note_id)
        
        if not result['success']:
            # Send error notification on failure with already-extracted data
            await send_error_notification(
                job_id, 
                note_id, 
                result.get('error'), 
                result.get('status_code'),
                note_data=result.get('note_data'),
                note_type=result.get('note_type'),
                patient_mrn=result.get('patient_mrn')
            )
            
            jobs_db[job_id]['status'] = 'failed'
            jobs_db[job_id]['error'] = result.get('error')
            jobs_db[job_id]['status_code'] = result.get('status_code')
    
    except Exception as e:
        error_msg = str(e)
        add_log(job_id, "error", "failed", f"Unexpected error: {error_msg}")
        
        jobs_db[job_id]['status'] = 'failed'
        jobs_db[job_id]['error'] = error_msg
        jobs_db[job_id]['status_code'] = 500
        
        # Send error notification (no note_data available for unexpected exceptions)
        await send_error_notification(job_id, note_id, error_msg, 500)


async def process_note_with_tracking(job_id: str, note_id: str):
    """
    Process note with detailed error tracking and status codes
    Enhanced with comprehensive timestamp tracking throughout processing lifecycle
    Returns: dict with 'success', 'error', 'status_code'
    """
    composite_key = None
    current_stage = "initialization"
    
    # Initialize token tracker for this note
    token_tracker = init_tracker(note_id=note_id, model="claude-haiku-3-5")
    
    # Initialize processing tracker for timestamp tracking
    from medical_notes.utils.timestamp_utils import init_processing_tracker
    processing_tracker = init_processing_tracker(note_id=note_id)
    
    # Mark ingestion timestamp (note received by system)
    ingestion_timestamp = processing_tracker.mark_ingestion()
    add_log(job_id, "timestamp_tracking", "info", 
            f"Ingestion timestamp recorded: {ingestion_timestamp}")
    
    try:
        n_previous_visits = N_PREVIOUS_VISITS
        job_start_time = datetime.now()
        
        jobs_db[job_id]['actual_started_at'] = job_start_time.isoformat()
        add_log(job_id, "job_start", "started", 
                f"Job processing started at {job_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        jobs_db[job_id]['status'] = 'processing'
        
        # Mark submission timestamp (note submitted for processing)
        submission_timestamp = processing_tracker.mark_submission()
        add_log(job_id, "timestamp_tracking", "info", 
                f"Submission timestamp recorded: {submission_timestamp}")
        
        # Stage 1: Validation
        current_stage = "validation"
        add_log(job_id, "validation", "in_progress", 
                f"Checking if noteId '{note_id}' exists in tiamd_prod_clinical_notes index")
        
        from medical_notes.repository.elastic_search import get_notes_by_noteid
        time.sleep(10)
        notes = get_notes_by_noteid(ES_INDEX_CLINICAL_NOTES, note_id)
        
        if not notes or len(notes) == 0:
            # Mark processing end even for failures
            processing_tracker.mark_processing_end()
            return {
                'success': False,
                'error': f"noteId '{note_id}' not found in tiamd_prod_clinical_notes index",
                'status_code': 404,
                'stage': current_stage,
                'note_data': None,
                'note_type': None,
                'patient_mrn': None
            }
        
        note_data = notes[0]
        current_status = note_data.get('status', '')
        
        if current_status == 'processed':
            # Mark processing end even for conflicts
            processing_tracker.mark_processing_end()
            return {
                'success': False,
                'error': f"noteId '{note_id}' already processed",
                'status_code': 409,  # Conflict
                'stage': current_stage,
                'note_data': note_data,
                'note_type': note_data.get('noteType'),
                'patient_mrn': None
            }
        
        add_log(job_id, "validation", "completed", 
                f"noteId '{note_id}' found and ready for processing")
        
        # Stage 2: Fetch note data
        current_stage = "fetch"
        add_log(job_id, "fetch", "in_progress", "Fetching noteId, rawdata, serviceDate, and locationname from tiamd_prod_clinical_notes")
        
        rawdata = note_data.get('rawdata', '')
        date_of_service = note_data.get('serviceDate', '')
        location_name = note_data.get('locationname', '') or note_data.get('locationName', '')
        
        if not rawdata:
            return {
                'success': False,
                'error': "rawdata field is empty",
                'status_code': 422,  # Unprocessable Entity
                'stage': current_stage,
                'note_data': note_data,
                'note_type': note_data.get('noteType'),
                'patient_mrn': None
            }
        
        add_log(job_id, "fetch", "completed", 
                f"Successfully fetched rawdata (length: {len(rawdata)} characters), "
                f"serviceDate: {date_of_service}, locationname: '{location_name if location_name else 'Not available'}'")
        
        if location_name:
            add_log(job_id, "fetch", "info", 
                    f"Location available in clinical_notes for fallback: '{location_name}'")
        
        # Stage 3: Get note type from Elasticsearch document and extract patient MRN from rawdata
        current_stage = "extraction"
        
        # Get raw noteType from the same Elasticsearch document (note_data)
        raw_note_type = note_data.get('noteType')
        patient_mrn = None  # Initialize MRN variable
        
        if not raw_note_type:
            # Fallback: if noteType is not in the document, extract both note type AND MRN from rawdata
            add_log(job_id, "extraction", "info", 
                    "noteType not found in document, extracting note type and MRN from rawdata as fallback")
            from medical_notes.service.note_type_extractor import extract_note_type_and_mrn
            raw_note_type, patient_mrn = extract_note_type_and_mrn(rawdata)
        else:
            # Note type exists in document, only extract MRN from rawdata
            add_log(job_id, "extraction", "in_progress", 
                    "Extracting patient MRN from rawdata using LLM")
            from medical_notes.service.note_type_extractor import extract_mrn
            patient_mrn = extract_mrn(rawdata)
        
        note_type = normalize_note_type(raw_note_type)
        
        if not note_type:
            error_msg = "Could not identify note type from document or raw text"
            processing_issues = ["Note type extraction failed"]
            
            # Mark processing end timestamp for failure
            processing_tracker.mark_processing_end()
            
            # Only include LLM-related processing issues
            llm_issues = ["Note type extraction failed"]  # This could be LLM-related if using LLM fallback
            
            push_failed_record_to_processed_notes(
                job_id, note_id, note_data, None, None, llm_issues
            )
            
            return {
                'success': False,
                'error': error_msg,
                'status_code': 422,  # Unprocessable Entity - cannot extract required data
                'stage': current_stage,
                'note_data': note_data,
                'note_type': None,
                'patient_mrn': None
            }
        
        add_log(job_id, "extraction", "info", 
                f"Note type retrieved from document: {note_type} (raw: {raw_note_type})")
        
        processing_issues = []  # Only for LLM-related errors
        
        if not patient_mrn:
            add_log(job_id, "extraction", "warning", 
                    "Could not extract patient MRN - will continue without historical context")
            # NOTE: MRN extraction failure is not an LLM processing error - it's handled gracefully
        else:
            add_log(job_id, "extraction", "completed", 
                    f"Note type: {note_type}, Patient MRN: {patient_mrn}")
            
            # Update patientMRN with error handling
            current_stage = "update_mrn"
            try:
                mrn_updated = update_patient_mrn_in_clinical_notes(
                    job_id, note_id, patient_mrn, date_of_service
                )
                
                if not mrn_updated:
                    return {
                        'success': False,
                        'error': f"Failed to update patientMRN '{patient_mrn}' in tiamd_prod_clinical_notes",
                        'status_code': 500,  # Internal Server Error - ES update failed
                        'stage': current_stage,
                        'details': 'Elasticsearch update operation failed',
                        'note_data': note_data,
                        'note_type': note_type,
                        'patient_mrn': patient_mrn
                    }
            except Exception as mrn_error:
                return {
                    'success': False,
                    'error': f"Exception while updating patientMRN: {str(mrn_error)}",
                    'status_code': 500,
                    'stage': current_stage,
                    'details': str(mrn_error),
                    'note_data': note_data,
                    'note_type': note_type,
                    'patient_mrn': patient_mrn
                }
        
        # Stage 4-6: Historical context
        # Get current date and time for Date of Service
        current_datetime = datetime.now()
        month = str(current_datetime.month)
        day = str(current_datetime.day)
        year = str(current_datetime.year)
        hour_12 = current_datetime.strftime("%I").lstrip("0") or "12"
        minute = current_datetime.strftime("%M")
        am_pm = current_datetime.strftime("%p")
        current_date_time_str = f"{month}/{day}/{year} {hour_12}:{minute} {am_pm}"
        
        combined_rawdata = rawdata
        previous_visits = []
        
        if patient_mrn and n_previous_visits > 0:
            current_stage = "historical_context"
            add_log(job_id, "historical_context", "in_progress", 
                    f"Fetching {n_previous_visits} previous visit(s)")
            
            previous_visits = fetch_previous_visits(
                job_id, 
                patient_mrn, 
                date_of_service, 
                note_id,
                n_previous_visits
            )
            
            if previous_visits:
                current_stage = "combine_context"
                combined_rawdata = combine_with_historical_context(rawdata, previous_visits, current_date_time_str)
                
                add_log(job_id, "combine_context", "completed", 
                        f"Combined with {len(previous_visits)} previous visit(s) with current date/time: {current_date_time_str}")
            else:
                # No previous visits, but still prepend current date/time
                combined_rawdata = combine_with_historical_context(rawdata, [], current_date_time_str)
                add_log(job_id, "combine_context", "completed", 
                        f"No previous visits found, added current date/time: {current_date_time_str}")
        else:
            # No historical context needed, but still prepend current date/time
            combined_rawdata = combine_with_historical_context(rawdata, [], current_date_time_str)
            add_log(job_id, "combine_context", "completed", 
                    f"Added current date/time to context: {current_date_time_str}")
        
        # Stage 7: Extract structured data from raw data (batch extraction)
        current_stage = "data_extraction"
        
        # Mark processing start timestamp (actual processing begins)
        processing_start_timestamp = processing_tracker.mark_processing_start()
        add_log(job_id, "timestamp_tracking", "info", 
                f"Processing start timestamp recorded: {processing_start_timestamp}")
        
        add_log(job_id, "data_extraction", "in_progress",
                "Extracting structured data using batch processing from raw data")
        
        # Use raw data directly for batch extraction
        data_for_extraction = combined_rawdata
        
        from medical_notes.service.medical_notes_processor import extract_structured_data
        time.sleep(10)
        
        try:
            processed_text, soap_text, notes_digest, extraction_error = extract_structured_data(
                data_for_extraction, note_type
            )
            
            if extraction_error:
                # Only add LLM-related extraction errors to processing_issues
                processing_issues.append(extraction_error)
            
            if not processed_text and not soap_text and not notes_digest:
                error_msg = "All template processing failed - no outputs generated"
                # This is an LLM processing failure - add to processing_issues
                processing_issues.append(error_msg)
                
                # Mark processing end timestamp for failure
                processing_tracker.mark_processing_end()
                
                push_failed_record_to_processed_notes(
                    job_id, note_id, note_data, note_type, patient_mrn, processing_issues
                )
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': 500,  # Internal Server Error - LLM processing failed
                    'stage': current_stage,
                    'details': extraction_error or 'All template processing returned empty results',
                    'note_data': note_data,
                    'note_type': note_type,
                    'patient_mrn': patient_mrn
                }
        except Exception as extract_error:
            return {
                'success': False,
                'error': f"Exception during data extraction: {str(extract_error)}",
                'status_code': 500,
                'stage': current_stage,
                'details': str(extract_error),
                'note_data': note_data,
                'note_type': note_type,
                'patient_mrn': patient_mrn
            }
        
        add_log(job_id, "data_extraction", "completed", 
                "Structured data extracted successfully using unified template system")
        
        # Skip separate SOAP generation stage since it's now included in data extraction
        # Stage 8 is now combined with Stage 7
        
        # Stage 9: Push to tiamd_prod_processed_notes
        current_stage = "push_to_index"
        add_log(job_id, "push_to_index", "in_progress",
                "Pushing processed data to tiamd_prod_processed_notes")

        from medical_notes.service.medical_notes_processor import prepare_es_record
        from medical_notes.repository.elastic_search import df_to_es_load

        try:
            # Add notes_digest to note_data so it's available for demographics extraction
            note_data['notes_digest'] = notes_digest
            
            es_record = prepare_es_record(
                note_data=note_data,
                note_type=note_type,
                processed_text=processed_text,
                processed_json=None,  # No longer using processed_json
                soap_text=soap_text,
                soap_json=None,  # No longer using soap_json
                processing_issues=processing_issues
            )

            es_record['noteId'] = note_id
            es_record['notesProcessedStatus'] = 'processed'
            es_record['dateOfServiceEpoch'] = parse_service_date_to_epoch(
                es_record.get('dateOfService', '')
            )

            # Enhanced logging for Stage 9
            add_log(job_id, "push_to_index", "info",
                    f"Record prepared with fields: noteId={note_id}, location='{es_record.get('location', 'N/A')}', "
                    f"dateOfService='{es_record.get('dateOfService', 'N/A')}', "
                    f"notesProcessedText={len(es_record.get('notesProcessedText', ''))} chars, "
                    f"notesProcessedPlainText={len(es_record.get('notesProcessedPlainText', ''))} chars")

            es_df = pd.DataFrame([es_record])
            df_to_es_load(es_df, ES_INDEX_PROCESSED_NOTES)

            composite_key = es_record.get('_id')

            if not composite_key:
                return {
                    'success': False,
                    'error': "Failed to generate composite key (_id) for processed note",
                    'status_code': 500,
                    'stage': current_stage,
                    'details': 'Composite key generation returned null',
                    'note_data': note_data,
                    'note_type': note_type,
                    'patient_mrn': patient_mrn
                }

            add_log(job_id, "push_to_index", "completed",
                    f"Data pushed successfully to tiamd_prod_processed_notes - composite_key: '{composite_key}', "
                    f"notesProcessedPlainText included: {len(es_record.get('notesProcessedPlainText', ''))} chars")

        except Exception as push_error:
            return {
                'success': False,
                'error': f"Failed to push data to tiamd_prod_processed_notes: {str(push_error)}",
                'status_code': 500,
                'stage': current_stage,
                'details': str(push_error),
                'note_data': note_data,
                'note_type': note_type,
                'patient_mrn': patient_mrn
            }

        # Stage 9a: Push notes_digest to tiamd_prod_notes_digest
        try:
            add_log(job_id, "push_digest_to_index", "in_progress",
                    "Pushing notes digest to tiamd_prod_notes_digest")
            
            digest_record = {
                '_id': es_record['_id'],
                'noteId': es_record['noteId'],
                'composite_key': es_record['composite_key'],
                'noteType': note_type,
                'patientName': es_record['patientName'],
                'patientmrn': es_record['patientmrn'],
                'ingestionDateTime': es_record['ingestionDateTime'],
                'processedDateTime': es_record['processedDateTime'],
            }
            
            # Apply data structure flattening if enabled and notes_digest contains JSON
            if ENABLE_DATA_FLATTENING and notes_digest:
                try:
                    import json
                    
                    # Parse the notes_digest JSON string
                    digest_json = json.loads(notes_digest) if isinstance(notes_digest, str) else notes_digest
                    
                    # Apply flattening to the parsed digest
                    flattened_digest, flattening_issues = flatten_all_nested_objects(digest_json)
                    
                    # Log flattening results
                    if flattening_issues:
                        add_log(job_id, "push_digest_to_index", "info",
                                f"Data flattening applied with {len(flattening_issues)} issues: {flattening_issues}")
                    else:
                        add_log(job_id, "push_digest_to_index", "info",
                                "Data flattening applied successfully with no issues")
                    
                    # Add all flattened fields to digest_record
                    digest_record.update(flattened_digest)
                    
                    # Add epoch timestamp fields for better date handling
                    current_time = datetime.now()
                    epoch_ms = int(current_time.timestamp() * 1000)
                    
                    # Add epoch fields for ingestion and processing timestamps
                    digest_record['ingestionDateTime_epoch'] = epoch_ms
                    digest_record['processedDateTime_epoch'] = epoch_ms
                    
                    # Add epoch fields for date fields if they exist and are parseable
                    date_fields = ['dateofbirth', 'dateofadmission', 'dateofdischarge', 'dateofservice']
                    for date_field in date_fields:
                        if date_field in digest_record and digest_record[date_field]:
                            try:
                                epoch_field = f"{date_field}_epoch"
                                epoch_value = parse_service_date_to_epoch(digest_record[date_field])
                                digest_record[epoch_field] = epoch_value if epoch_value else 0
                            except:
                                digest_record[f"{date_field}_epoch"] = 0
                    
                    add_log(job_id, "push_digest_to_index", "info",
                            f"Flattened {len(flattened_digest)} fields added to digest record with epoch timestamps")
                    
                except (json.JSONDecodeError, TypeError) as e:
                    add_log(job_id, "push_digest_to_index", "warning",
                            f"Could not apply data flattening - notes_digest is not valid JSON: {str(e)}")
                except Exception as e:
                    add_log(job_id, "push_digest_to_index", "warning",
                            f"Data flattening failed: {str(e)} (continuing with original digest)")
            
            digest_df = pd.DataFrame([digest_record])
            df_to_es_load(digest_df, ES_INDEX_NOTES_DIGEST)
            
            flattening_status = " (with data flattening)" if ENABLE_DATA_FLATTENING else ""
            add_log(job_id, "push_digest_to_index", "completed",
                    f"Notes digest pushed successfully to tiamd_prod_notes_digest{flattening_status} - composite_key: '{composite_key}'")
        
        except Exception as digest_error:
            add_log(job_id, "push_digest_to_index", "warning",
                    f"Failed to push notes digest: {str(digest_error)} (continuing anyway)")
            # NOTE: Elasticsearch indexing failure is not an LLM processing error

        # Stage 10: Push to External API (BEFORE updating status in clinical_notes)
        current_stage = "api_push"
        add_log(job_id, "api_push", "in_progress", 
                f"Pushing data to external API for noteId '{note_id}'")
        
        from medical_notes.repository.elastic_search import push_note_to_api
        
        submit_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            time.sleep(10)
            api_success, submitting_issues = push_note_to_api(note_id, composite_key)
            
            if not api_success:
                # API failed - capture the specific error details in submittingIssues
                update_submit_tracking(note_id, composite_key, submit_datetime, submitting_issues)
                
                return {
                    'success': False,
                    'error': f"Failed to push data to external API: {submitting_issues}",
                    'status_code': 403,
                    'stage': current_stage,
                    'details': 'External API returned non-success status or validation error',
                    'note_data': note_data,
                    'note_type': note_type,
                    'patient_mrn': patient_mrn
                }
            
            add_log(job_id, "api_push", "completed", 
                    "Data successfully pushed to external API (200 OK)")
        
        except Exception as api_error:
            submitting_issues = f"API exception: {str(api_error)}"
            update_submit_tracking(note_id, composite_key, submit_datetime, submitting_issues)
            
            return {
                'success': False,
                'error': f"Exception during API push: {str(api_error)}",
                'status_code': 500,
                'stage': current_stage,
                'details': str(api_error),
                'note_data': note_data,
                'note_type': note_type,
                'patient_mrn': patient_mrn
            }
        
        # Stage 11: Update status in clinical_notes (ONLY AFTER successful API push)
        current_stage = "status_update"
        add_log(job_id, "status_update", "in_progress", 
                "Updating status to 'processed' in tiamd_prod_clinical_notes after successful API push")
        
        from medical_notes.repository.elastic_search import update_from_dataframe
        time.sleep(10)
        
        try:
            update_df = pd.DataFrame([{
                'noteId': note_id,
                'status': 'processed',
                'noteType': note_type
            }])
            
            update_result = update_from_dataframe(
                ES_INDEX_CLINICAL_NOTES,
                update_df,
                fields_to_update=['status', 'noteType']
            )
            
            add_log(job_id, "status_update", "completed", 
                    f"Status updated to 'processed' for noteId '{note_id}' after API confirmation")
        
        except Exception as update_error:
            # API push was successful but status update failed
            # Log warning but don't fail the entire process
            add_log(job_id, "status_update", "warning", 
                    f"Failed to update status in tiamd_prod_clinical_notes: {str(update_error)}")
            # Continue processing - don't return error here
        
        # Stage 12: Update submit tracking
        current_stage = "submit_tracking"
        submitting_issues_str = ''
        tracking_updated = update_submit_tracking(
            note_id, composite_key, submit_datetime, submitting_issues_str
        )
        
        if tracking_updated:
            add_log(job_id, "submit_tracking", "completed", 
                    f"Submit tracking updated (submitDateTime: {submit_datetime})")
        
        # Stage 13: Update final status
        current_stage = "final_status_update"
        try:
            from medical_notes.repository.elastic_search import update_status_precise
            time.sleep(10)
            status_updated = update_status_precise(
                note_id=note_id,
                composite_key=composite_key,
                new_status="note submitted"
            )
            
            if status_updated:
                add_log(job_id, "final_status_update", "completed", 
                        "Status updated to 'note submitted'")
        except Exception as update_error:
            add_log(job_id, "final_status_update", "warning", 
                    f"Exception updating final status: {str(update_error)}")
        
        # Mark processing end timestamp (processing completed successfully)
        processing_end_timestamp = processing_tracker.mark_processing_end()
        add_log(job_id, "timestamp_tracking", "info", 
                f"Processing end timestamp recorded: {processing_end_timestamp}")
        
        # Mark processed_at timestamp (note indexed/stored)
        processed_at_timestamp = processing_tracker.mark_processed_at()
        add_log(job_id, "timestamp_tracking", "info", 
                f"Processed at timestamp recorded: {processed_at_timestamp}")
        
        # Validate temporal ordering
        if processing_tracker.validate_temporal_ordering():
            add_log(job_id, "timestamp_tracking", "info", 
                    "Timestamp temporal ordering validation passed")
        else:
            add_log(job_id, "timestamp_tracking", "warning", 
                    "Timestamp temporal ordering validation failed")
        
        # SUCCESS - Calculate duration
        job_end_time = datetime.now()
        jobs_db[job_id]['completed_at'] = job_end_time.isoformat()
        duration = (job_end_time - job_start_time).total_seconds()
        jobs_db[job_id]['duration_seconds'] = duration
        jobs_db[job_id]['status'] = 'completed'
        
        # Get token usage summary
        final_tracker = get_and_clear_tracker()
        token_usage_summary = final_tracker.get_summary() if final_tracker else None
        
        # Log token usage summary and push to Elasticsearch
        if final_tracker:
            add_log(job_id, "token_usage", "info", 
                    f"Total tokens: {final_tracker.get_total_tokens():,} "
                    f"(in: {final_tracker.get_total_input_tokens():,}, out: {final_tracker.get_total_output_tokens():,}) | "
                    f"Cost: ${final_tracker.get_total_cost():.6f} USD")
            
            # Log per-section breakdown
            for section in final_tracker.sections:
                add_log(job_id, "token_usage", "info", 
                        f"  • {section.section_name}: {section.input_tokens + section.output_tokens:,} tokens (${section.cost_usd:.6f})")
            
            # Print summary to console
            print(final_tracker.print_summary())
            
            # Push to Elasticsearch
            es_pushed = final_tracker.push_to_elasticsearch()
            if es_pushed:
                add_log(job_id, "token_usage", "info", f"Token usage pushed to Elasticsearch ({ES_INDEX_TOKEN_USAGE})")
            else:
                add_log(job_id, "token_usage", "warning", "Failed to push token usage to Elasticsearch")
        
        jobs_db[job_id]['result'] = {
            'noteId': note_id,
            'noteType': note_type,
            'patientMRN': patient_mrn or 'Not extracted',
            'composite_key': composite_key,
            'processed': True,
            'status': 'note submitted',
            'submitDateTime': submit_datetime,
            'duration_seconds': round(duration, 2),
            'token_usage': token_usage_summary
        }
        
        add_log(job_id, "completion", "success", 
                f"Processing completed successfully for noteId '{note_id}'")
        
        return {
            'success': True,
            'status_code': 200
        }
    
    except Exception as e:
        error_msg = str(e)
        add_log(job_id, "error", "failed", f"Unexpected error: {error_msg}")
        
        # Mark processing end timestamp even for failures
        try:
            processing_end_timestamp = processing_tracker.mark_processing_end()
            add_log(job_id, "timestamp_tracking", "info", 
                    f"Processing end timestamp recorded (failure): {processing_end_timestamp}")
        except Exception as timestamp_error:
            add_log(job_id, "timestamp_tracking", "warning", 
                    f"Failed to record processing end timestamp: {str(timestamp_error)}")
        
        import traceback
        traceback.print_exc()
        
        # Get token usage even on failure
        final_tracker = get_and_clear_tracker()
        token_usage_summary = final_tracker.get_summary() if final_tracker else None
        
        if final_tracker:
            add_log(job_id, "token_usage", "info", 
                    f"Tokens used before failure: {final_tracker.get_total_tokens():,} | Cost: ${final_tracker.get_total_cost():.6f} USD")
            print(final_tracker.print_summary())
            
            # Push to Elasticsearch even on failure
            es_pushed = final_tracker.push_to_elasticsearch()
            if es_pushed:
                add_log(job_id, "token_usage", "info", f"Token usage pushed to Elasticsearch ({ES_INDEX_TOKEN_USAGE})")
        
        return {
            'success': False,
            'error': error_msg,
            'status_code': 500,  # Internal Server Error
            'stage': current_stage,
            'details': traceback.format_exc(),
            'token_usage': token_usage_summary,
            'note_data': locals().get('note_data'),
            'note_type': locals().get('note_type'),
            'patient_mrn': locals().get('patient_mrn')
        }


async def send_error_notification(job_id: str, note_id: str, error: str, status_code: int,
                                   note_data: dict = None, note_type: str = None, patient_mrn: str = None):
    """
    Send error notification when processing fails
    Uses already-extracted data from processing flow

    Args:
        job_id: Job ID
        note_id: The noteId
        error: Error message
        status_code: HTTP status code representing the error type
        note_data: Note data from ES (already fetched during processing)
        note_type: Note type (already extracted during processing)
        patient_mrn: Patient MRN (already extracted during processing)
    """
    from medical_notes.repository.elastic_search import send_processing_error
    from medical_notes.repository.elastic_search import get_notes_by_noteid

    add_log(job_id, "error_notification", "in_progress",
            f"Sending error notification to external API (status: {status_code})")

    # Use passed note_data, or fetch from ES if not provided (fallback for early failures)
    if note_data is None:
        note_data = {}
        try:
            notes = get_notes_by_noteid(ES_INDEX_CLINICAL_NOTES, note_id)
            if notes and len(notes) > 0:
                note_data = notes[0]
                add_log(job_id, "error_notification", "info",
                        f"Fetched note data from ES for error notification (fallback)")
        except Exception as fetch_error:
            add_log(job_id, "error_notification", "warning",
                    f"Could not fetch note data from ES: {str(fetch_error)}")

    # Use passed values or get from note_data
    final_note_type = note_type or note_data.get('noteType', '')
    final_patient_mrn = patient_mrn or ""

    # Prepare error payload with all required fields
    error_payload = {
        "noteId": note_id,
        "patientName": note_data.get('patientID', ''),
        "patientmrn": final_patient_mrn,
        "dateOfService": datetime.now().strftime("%Y-%m-%d"),
        "noteType": final_note_type,
        "locationname": note_data.get('locationname', '') or note_data.get('locationName', ''),
        "statusCode": status_code,
        "errorMessage": error
    }

    try:
        result = send_processing_error(error_payload)

        if result:
            add_log(job_id, "error_notification", "completed",
                    f"Error notification sent successfully (statusCode: {status_code})")
        else:
            add_log(job_id, "error_notification", "failed",
                    "Failed to send error notification to external API")

    except Exception as e:
        add_log(job_id, "error_notification", "failed", 
                f"Exception sending error notification: {str(e)}")


# Status code definitions for reference
"""
Status Codes Used:
- 200: Success
- 404: Note not found in index
- 409: Note already processed (conflict)
- 422: Unprocessable Entity (cannot extract required data, empty rawdata)
- 403: Forbidden (API rejected the request)
- 500: Internal Server Error (ES failures, LLM failures, unexpected errors)
"""

import asyncio

def concurrent_process_note_wrapper(job_id: str, note_id: str) -> dict:
    """
    Wrapper function for concurrent processing that integrates with the job manager.
    This function bridges the async FastAPI world with the synchronous job manager.
    
    Args:
        job_id: Job ID for tracking
        note_id: Note ID to process
        
    Returns:
        dict: Processing result
    """
    # Create job tracking in legacy jobs_db for compatibility
    jobs_db[job_id] = {
        'job_id': job_id,
        'noteId': note_id,
        'status': 'processing',
        'current_stage': 'processing',
        'logs': [],
        'started_at': datetime.now().isoformat(),
        'actual_started_at': datetime.now().isoformat(),
    }
    
    print(f"🔄 [Concurrent] Starting full processing pipeline for job {job_id}, note {note_id}")
    
    try:
        # Run the full async processing pipeline in a new event loop
        # This includes all steps: validation, processing, API push, status updates
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            print(f"🔄 [Concurrent] Executing async processing pipeline for note {note_id}")
            result = loop.run_until_complete(process_note_with_tracking(job_id, note_id))
            print(f"📊 [Concurrent] Processing pipeline completed for note {note_id}: success={result.get('success')}")
        finally:
            loop.close()
        
        # Update job status based on result
        if result.get('success'):
            jobs_db[job_id]['status'] = 'completed'
            jobs_db[job_id]['completed_at'] = datetime.now().isoformat()
            jobs_db[job_id]['result'] = result
            
            print(f"✅ [Concurrent] Job {job_id} completed successfully for note {note_id}")
            return {
                'success': True,
                'message': f'Note {note_id} processed successfully with API push',
                'note_id': note_id,
                'job_id': job_id
            }
        else:
            jobs_db[job_id]['status'] = 'failed'
            jobs_db[job_id]['completed_at'] = datetime.now().isoformat()
            jobs_db[job_id]['error'] = result.get('error', 'Unknown error')
            
            print(f"❌ [Concurrent] Job {job_id} failed for note {note_id}: {result.get('error')}")
            return {
                'success': False,
                'message': result.get('error', 'Processing failed'),
                'note_id': note_id,
                'job_id': job_id,
                'status_code': result.get('status_code', 500)
            }
        
    except Exception as e:
        error_msg = str(e)
        jobs_db[job_id]['status'] = 'failed'
        jobs_db[job_id]['error'] = error_msg
        jobs_db[job_id]['completed_at'] = datetime.now().isoformat()
        
        print(f"💥 [Concurrent] Exception in job {job_id} for note {note_id}: {error_msg}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'message': error_msg,
            'note_id': note_id,
            'job_id': job_id,
            'status_code': 500
        }


# Route definitions moved to separate route files
# All API endpoints are now organized in medical_notes/routes/

# uvicorn app.app:app --reload