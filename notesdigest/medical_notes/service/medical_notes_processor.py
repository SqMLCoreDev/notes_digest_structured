"""
Medical Notes Processing Pipeline - Updated Version
Added: processedDateTime, processingIssues, submitDateTime, submittingIssues tracking
"""

import re
import json
import pandas as pd
from datetime import datetime
from dateutil import parser
from typing import Dict, Any, Optional, Tuple

# Import local modules using relative imports
from medical_notes.repository.elastic_search import get_notes_by_noteid
from medical_notes.repository.elastic_search import update_from_dataframe
from medical_notes.repository.elastic_search import df_to_es_load
from medical_notes.service.note_type_extractor import extract_note_type
from medical_notes.utils.clean_output import clean_asterisks
from medical_notes.config.config import ES_INDEX_CLINICAL_NOTES, ES_INDEX_PROCESSED_NOTES, ES_INDEX_NOTES_DIGEST

def is_llm_processing_error(error_message: str) -> bool:
    """
    Determine if an error message represents an LLM processing error.
    
    Args:
        error_message: The error message to classify
        
    Returns:
        bool: True if this is an LLM processing error, False otherwise
    """
    if not error_message:
        return False
    
    error_lower = error_message.lower()
    
    # LLM-related error patterns
    llm_error_patterns = [
        # AWS Bedrock/Claude specific errors
        'bedrock', 'claude', 'anthropic', 'invoke_model',
        # LLM API errors
        'token limit', 'context window', 'max_tokens', 'input too long',
        # Authentication/credentials for LLM services
        'aws_access_key', 'aws_secret_access', 'credentials',
        # LLM response issues
        'empty response', 'no content in', 'llm returned null', 'llm returned empty',
        # Template processing (LLM-based)
        'template processing', 'structured data extraction', 'processing error:',
        # LLM generation failures
        'soap generation', 'notes digest generation', 'all template processing failed',
        # Model-specific errors
        'model not found', 'model unavailable', 'rate limit', 'throttling'
    ]
    
    # Check if error message contains any LLM-related patterns
    for pattern in llm_error_patterns:
        if pattern in error_lower:
            return True
    
    # System/infrastructure errors (NOT LLM processing errors)
    system_error_patterns = [
        'elasticsearch', 'index', 'connection', 'network', 'timeout',
        'database', 'sql', 'file system', 'disk space',
        'not found in', 'already processed', 'rawdata is empty',
        'demographics extraction', 'regex extraction', 'date parsing'
    ]
    
    # If it's clearly a system error, return False
    for pattern in system_error_patterns:
        if pattern in error_lower:
            return False
    
    # If uncertain, err on the side of NOT including it in processing issues
    return False

def normalize_note_type(note_type: str) -> str:
    """
    Normalize incoming noteType values (from ES or extractor) to canonical keys.

    Canonical values:
      - history_physical
      - progress_note
      - discharge_summary
      - consultation_note
      - procedure_note
      - ed_note
      - generic_note
    
    Defaults to progress_note for unrecognized types.
    """
    if not note_type:
        return "progress_note"

    # Basic normalization: trim, lowercase, replace spaces with underscores
    normalized = str(note_type).strip().lower().replace(" ", "_")

    # Handle common plural / alias variants
    alias_map = {
        # Progress note variants
        "progress_note": "progress_note",
        "progress_notes": "progress_note",
        
        # History & Physical variants
        "history_physical": "history_physical",
        "history_physicals": "history_physical",  # Added plural
        "history_and_physical": "history_physical",
        "history_physical_note": "history_physical",
        "h&p": "history_physical",
        
        # Consultation variants
        "consultation_note": "consultation_note",
        "consultation_notes": "consultation_note",  # Added plural
        "consult_note": "consultation_note",
        "consultation": "consultation_note",
        "consultations": "consultation_note",
        
        # Procedure note variants
        "procedure_note": "procedure_note",
        "procedure_notes": "procedure_note",
        
        # ED/ER note variants
        "ed_note": "ed_note",
        "ed_notes": "ed_note",
        
        # Discharge variants
        "discharge_summary": "discharge_summary",
        "discharge_summarys": "discharge_summary",  # Added plural (even though grammatically incorrect)
        "discharge_summaries": "discharge_summary",  # Added correct plural
        "discharge_planning": "discharge_summary",
        
        # Generic variants
        "generic_note": "generic_note",
        "generic_notes": "generic_note",  # Added plural
        "generic": "generic_note",
        "general": "generic_note",
        
        # OP Follow-up Visit variants
        "op_follow_up_visit": "op_follow_up_visit",
        "op_follow-up_visit": "op_follow_up_visit",
        "op_followup_visit": "op_follow_up_visit",
        "op_followup": "op_follow_up_visit",
        "op_follow_up": "op_follow_up_visit",
        "op_visit": "op_follow_up_visit",
        "outpatient_follow_up": "op_follow_up_visit",
        "outpatient_follow-up": "op_follow_up_visit",
        "outpatient_followup": "op_follow_up_visit",
        "outpatient_follow_up_visit": "op_follow_up_visit",
        "outpatient_visit": "op_follow_up_visit",
        "follow_up_visit": "op_follow_up_visit",
        "followup_visit": "op_follow_up_visit",
        "follow-up_visit": "op_follow_up_visit",
    }

    if normalized in alias_map:
        normalized = alias_map[normalized]

    valid_types = {
        "history_physical",
        "progress_note",
        "discharge_summary",
        "consultation_note",
        "procedure_note",
        "ed_note",
        "generic_note",
        "op_follow_up_visit",
    }

    if normalized not in valid_types:
        print(f"  ⚠️ Unrecognized noteType '{note_type}', normalizing to 'progress_note'")
        return "progress_note"

    return normalized


def generate_composite_key(note_id):
    """
    Generate composite key using only the noteId.
    """
    return str(note_id)

def extract_structured_data(rawdata, note_type, patient_id=None):
    """
    Extract structured data using unified template system
    Returns: processed_text, soap_text, notes_digest, error_message (LLM-related errors only)
    
    Args:
        rawdata: The raw medical note text
        note_type: Type of medical note
        patient_id: Optional patient ID from clinical notes index to pass to LLM for context
    """
    if not rawdata or not note_type:
        return None, None, None, "Missing rawdata or note_type - LLM processing cannot proceed"
    
    try:
        # Use the existing MedicalNotesGenerator for consistency
        from medical_notes.service.all_medical_notes import MedicalNotesGenerator
        
        # Initialize generator
        notes_generator = MedicalNotesGenerator()
        
        # Convert rawdata to DataFrame format expected by the generator
        df = pd.DataFrame([{'rawdata': rawdata}])
        
        # Process using the existing generator, passing patient_id for LLM context
        result, error = notes_generator.process_medical_records(df, note_type=note_type, patient_id=patient_id)
        
        if error:
            print(f"  ✗ LLM Processing error: {error}")
            return None, None, None, f"LLM Processing error: {error}"
        
        if result:
            # Extract the outputs
            processed_text = result.get('processed_data', '')
            soap_text = result.get('soap_data', '')
            notes_digest = result.get('notes_digest', '{}')

            # Clean the outputs (remove ** formatting)
            if processed_text:
                processed_text = clean_asterisks(processed_text)
            if soap_text:
                soap_text = clean_asterisks(soap_text)
            
            print(f"  ✓ All LLM template processing completed successfully")
            return processed_text, soap_text, notes_digest, None
        
        return None, None, None, "LLM processing returned no result"
        
    except Exception as e:
        error_msg = f"LLM template processing exception: {str(e)}"
        print(f"  ✗ {error_msg}")
        return None, None, None, error_msg

def extract_demographics_from_text(processed_text):
    """
    Fallback method: Extract demographics from processed text using regex patterns.
    """
    demographics = {
        'patient_first_name': '',
        'patient_last_name': '',
        'patient_name': '',
        'patient_mrn': '',
        'location': '',
        'admission_date': '',
        'date_of_service': '',
        'discharge_date': '',
    }
    
    if not processed_text:
        return demographics, ["No processed text available for regex extraction"]
    
    issues = []
    
    try:
        # Extract patient name (re-enabled as it's mandatory)
        name_patterns = [
            r'Patient\s*Name\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|MRN|DOB|$)',
            r'Name\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|MRN|DOB|$)',
            r'Patient\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|MRN|DOB|$)',
            r'Full\s*Name\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|MRN|DOB|$)',
        ]
        
        name_found = False
        for pattern in name_patterns:
            match = re.search(pattern, processed_text, re.IGNORECASE)
            if match:
                patient_name = match.group(1).strip()
                # Clean up the name - remove common suffixes and extra whitespace
                patient_name = re.sub(r'\s+', ' ', patient_name)  # Normalize whitespace
                patient_name = patient_name.rstrip('.,;:')  # Remove trailing punctuation
                
                # Skip if it looks like it's not actually a name (too short, contains numbers, etc.)
                if len(patient_name) > 2 and not re.search(r'\d', patient_name):
                    demographics['patient_name'] = patient_name
                    name_found = True
                    break
        
        if not name_found:
            issues.append("Patient name not found in text")
        
        # Pattern for MRN
        mrn_patterns = [
            r'MRN\s*:?\s*([^\s]+)',  # Captures everything until first space after MRN:
            r'Medical\s*Record\s*Number\s*:?\s*([^\s]+)',
            r'Record\s*#?\s*:?\s*([^\s]+)',
            r'Patient\s*ID\s*:?\s*([^\s]+)',
            ]
        
        mrn_found = False
        for pattern in mrn_patterns:
            match = re.search(pattern, processed_text, re.IGNORECASE)
            if match:
                demographics['patient_mrn'] = match.group(1).strip()
                mrn_found = True
                break
        
        if not mrn_found:
            issues.append("Patient MRN not found in text")
        
        # Pattern for Location
        location_patterns = [
            r'Location\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|<br>|$)',
            r'Facility\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|<br>|$)',
            r'Hospital\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|<br>|$)',
            r'Department\s*[:\-]?\s*([^\n\r]+?)(?:\n|\r|<br>|$)',
        ]
        
        location_found = False
        for pattern in location_patterns:
            match = re.search(pattern, processed_text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Clean up location - remove HTML tags and limit length
                location = re.sub(r'<br\s*/?>', ' ', location)
                location = re.sub(r'<[^>]+>', '', location)
                
                # Stop at "Contact information" or "Additional Providers"
                if 'Contact information:' in location or 'Contact Information:' in location:
                    location = re.split(r'[Cc]ontact [Ii]nformation:', location)[0].strip().rstrip(',').strip()
                if 'Additional Providers:' in location or '- Additional Providers:' in location:
                    location = re.split(r'-?\s*[Aa]dditional [Pp]roviders:', location)[0].strip().rstrip(',').strip()
                
                # Take only first part before comma if too long
                if ',' in location and len(location) > 100:
                    location = location.split(',')[0].strip()
                
                # Limit to reasonable length
                if len(location) > 200:
                    location = location[:200].strip()
                
                demographics['location'] = location
                location_found = True
                break
        
        if not location_found:
            issues.append("Location not found in text")
        
        # Date patterns for admission, service, discharge
        admission_patterns = [
            r'Admission\s*Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Admitted\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Admission\s*[:\-]?\s*([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
            r'Admit\s*Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        ]
        
        admission_found = False
        for pattern in admission_patterns:
            match = re.search(pattern, processed_text, re.IGNORECASE)
            if match:
                demographics['admission_date'] = match.group(1).strip()
                admission_found = True
                break
        
        if not admission_found:
            issues.append("Admission date not found in text")
        
        dos_patterns = [
            r'Date\s*of\s*Service\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Service\s*Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'DOS\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        ]
        
        dos_found = False
        for pattern in dos_patterns:
            match = re.search(pattern, processed_text, re.IGNORECASE)
            if match:
                demographics['date_of_service'] = match.group(1).strip()
                dos_found = True
                break
        
        if not dos_found:
            issues.append("Date of service not found in text")
        
        discharge_patterns = [
            r'Discharge\s*Date\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'Discharged\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
        ]
        
        for pattern in discharge_patterns:
            match = re.search(pattern, processed_text, re.IGNORECASE)
            if match:
                demographics['discharge_date'] = match.group(1).strip()
                break
    
    except Exception as e:
        issues.append(f"Regex extraction exception: {str(e)}")
    
    return demographics, issues


def extract_demographics_from_notes_digest(notes_digest):
    """
    Extract demographics from the notes_digest field.
    Handles both JSON format and plain text format.
    """
    demographics = {
        'patient_name': '',
        'patient_mrn': '',
        'location': '',
        'admission_date': '',
        'date_of_service': '',
        'discharge_date': '',
    }

    issues = []

    # Ensure notes_digest is a string
    if notes_digest is None:
        issues.append("No notes_digest data provided (None)")
        return demographics, issues
    
    # Convert to string if it's not already
    if not isinstance(notes_digest, str):
        try:
            notes_digest = str(notes_digest)
        except Exception as e:
            issues.append(f"Could not convert notes_digest to string: {str(e)}")
            return demographics, issues

    if not notes_digest.strip():
        issues.append("No notes_digest data provided (empty)")
        return demographics, issues

    try:
        # First, try to parse as JSON (structured format)
        import json
        try:
            digest_json = json.loads(notes_digest)
            
            # Ensure digest_json is a dictionary
            if not isinstance(digest_json, dict):
                raise TypeError(f"Expected dictionary, got {type(digest_json)}")
            
            # Extract from demographics section
            demo_section = digest_json.get('demographics', {})
            if demo_section and isinstance(demo_section, dict):
                demographics['patient_name'] = demo_section.get('Patientname', '') or demo_section.get('patientname', '')
                demographics['patient_mrn'] = demo_section.get('mrn', '')
                demographics['admission_date'] = demo_section.get('dateofadmission', '')
                demographics['discharge_date'] = demo_section.get('dateofdischarge', '')
                demographics['date_of_service'] = demo_section.get('dateofservice', '')
            
            # Extract location from service_details section
            service_section = digest_json.get('service_details', {})
            if service_section and isinstance(service_section, dict):
                demographics['location'] = service_section.get('location', '')
            
            # Log successful JSON extraction
            print(f"    ✓ Successfully extracted demographics from JSON format")
            
        except (json.JSONDecodeError, TypeError) as json_error:
            # Fallback to regex patterns for plain text format
            print(f"    ⚠️ Notes digest not in JSON format ({str(json_error)}), using regex extraction")
            
            # Extract patient name
            name_patterns = [
                r'Patient\s*Name\s*:\s*([^\n\r]+)',
                r'Name\s*:\s*([^\n\r]+)',
                r'Patientname\s*:\s*([^\n\r]+)'
            ]
            for pattern in name_patterns:
                match = re.search(pattern, notes_digest, re.IGNORECASE)
                if match:
                    demographics['patient_name'] = match.group(1).strip()
                    break
            
            # Extract MRN
            mrn_patterns = [
                r'MRN\s*:\s*(\S+)',
                r'Medical\s*Record\s*Number\s*:\s*(\S+)',
                r'"mrn"\s*:\s*"([^"]+)"'
            ]
            for pattern in mrn_patterns:
                match = re.search(pattern, notes_digest, re.IGNORECASE)
                if match:
                    demographics['patient_mrn'] = match.group(1).strip()
                    break

            # Extract location
            location_patterns = [
                r'Location\s*:\s*([^\n\r]+)',
                r'"location"\s*:\s*"([^"]+)"',
                r'Facility\s*:\s*([^\n\r]+)'
            ]
            for pattern in location_patterns:
                match = re.search(pattern, notes_digest, re.IGNORECASE)
                if match:
                    demographics['location'] = match.group(1).strip()
                    break

            # Extract admission date
            admission_patterns = [
                r'Admission\s*Date\s*:\s*([^\n\r]+)',
                r'Date\s*of\s*Admission\s*:\s*([^\n\r]+)',
                r'"dateofadmission"\s*:\s*"([^"]+)"'
            ]
            for pattern in admission_patterns:
                match = re.search(pattern, notes_digest, re.IGNORECASE)
                if match:
                    demographics['admission_date'] = match.group(1).strip()
                    break

            # Extract discharge date
            discharge_patterns = [
                r'Discharge\s*Date\s*:\s*([^\n\r]+)',
                r'Date\s*of\s*Discharge\s*:\s*([^\n\r]+)',
                r'"dateofdischarge"\s*:\s*"([^"]+)"'
            ]
            for pattern in discharge_patterns:
                match = re.search(pattern, notes_digest, re.IGNORECASE)
                if match:
                    demographics['discharge_date'] = match.group(1).strip()
                    break

        # Check for missing fields and add issues
        if not demographics['patient_name']:
            issues.append("Patient name not found in notes_digest")
        if not demographics['patient_mrn']:
            issues.append("Patient MRN not found in notes_digest")
        if not demographics['location']:
            issues.append("Location not found in notes_digest")
        if not demographics['admission_date']:
            issues.append("Admission date not found in notes_digest")
        if not demographics['discharge_date']:
            issues.append("Discharge date not found in notes_digest")

    except Exception as e:
        issues.append(f"Demographics extraction exception: {str(e)}")

    return demographics, issues


def prepare_es_record(note_data, note_type, processed_text=None, processed_json=None, 
                     soap_text=None, soap_json=None, processing_issues=None):
    """
    Prepare record with all required ES fields for tiamd_processed_notes.
    Enhanced with comprehensive timestamp tracking including:
    - ingestionDateTimeAsEpoch: When note was received by system
    - submitDateEpoch: When note was submitted for processing  
    - processedDateTimeEpoch: When note processing completed
    """
    
    # Import timestamp utilities
    from medical_notes.utils.timestamp_utils import TimestampManager, get_current_processing_tracker
    
    # Extract demographics with issue tracking
    demographics, demo_issues = extract_demographics_from_notes_digest(note_data.get('notes_digest', ''))
    
    # Check if we successfully extracted from notes_digest
    notes_digest_success = any([demographics.get('patient_name'), demographics.get('patient_mrn'), 
                               demographics.get('admission_date'), demographics.get('discharge_date')])
    
    if notes_digest_success:
        print(f"    ✓ Demographics successfully extracted from notes_digest")
    
    # Fallback 1: If demographics not found in notes_digest, try extracting from processed_text
    if not notes_digest_success:
        print(f"    ⚠️ Demographics not found in notes_digest, trying processed_text fallback")
        if processed_text:
            fallback_demographics, fallback_issues = extract_demographics_from_text(processed_text)
            # Merge non-empty values from fallback
            for key, value in fallback_demographics.items():
                if value and not demographics.get(key):
                    demographics[key] = value
                    print(f"    ✓ Extracted {key} from processed_text: '{value}'")
            # Update issues - remove resolved ones
            demo_issues = [issue for issue in demo_issues 
                          if not any(field in issue.lower() for field in demographics.keys() if demographics[field])]
    
    # PRIORITY 1: Use patientID from clinical notes index as primary source
    clinical_patient_id = note_data.get('patientID', '')
    if clinical_patient_id and not demographics.get('patient_name'):
        demographics['patient_name'] = clinical_patient_id
        print(f"    ✓ Using patientID from clinical notes index (PRIMARY SOURCE): '{clinical_patient_id}'")
        # Remove the patient name issue since we found it in clinical notes
        demo_issues = [issue for issue in demo_issues if 'Patient name not found' not in issue]
    
    # Fallback 1.5: If patient name specifically not found, try extracting from processed_text
    if not demographics.get('patient_name') and processed_text:
        print(f"    ⚠️ Patient name not found in clinical notes or notes_digest, trying processed_text fallback")
        fallback_demographics, fallback_issues = extract_demographics_from_text(processed_text)
        if fallback_demographics.get('patient_name'):
            demographics['patient_name'] = fallback_demographics['patient_name']
            print(f"    ✓ Extracted patient_name from processed_text: '{fallback_demographics['patient_name']}'")
            # Remove the patient name issue since we found it
            demo_issues = [issue for issue in demo_issues if 'Patient name not found' not in issue]
    
    # Fallback 2: Use location from clinical notes if not found in notes_digest or processed_text
    if not demographics.get('location'):
        clinical_location = note_data.get('locationname', '') or note_data.get('locationName', '')
        if clinical_location:
            demographics['location'] = clinical_location
            print(f"    ✓ Using location from clinical notes as fallback: '{clinical_location}'")
            # Remove the location issue since we found it in clinical notes
            demo_issues = [issue for issue in demo_issues if 'Location not found' not in issue]
        else:
            print(f"    ⚠️ Location not available in notes_digest, processed_text, or clinical notes")
    
    # Fallback 3: Use LLM to extract patient name from raw data if still not found
    # Pass the known patientID to LLM for validation/confirmation if available
    if not demographics.get('patient_name'):
        rawdata = note_data.get('rawdata', '')
        if rawdata:
            print(f"    ⚠️ Patient name not found in clinical notes, notes_digest, or processed_text, trying LLM extraction from rawdata")
            from medical_notes.service.note_type_extractor import extract_patient_name
            # Pass known patientID to LLM for validation (if we had one but need full name)
            llm_patient_name = extract_patient_name(rawdata, known_patient_id=clinical_patient_id if clinical_patient_id else None)
            if llm_patient_name:
                demographics['patient_name'] = llm_patient_name
                print(f"    ✓ Using LLM-extracted patient name: '{llm_patient_name}'")
                # Remove the patient name issue since we found it via LLM
                demo_issues = [issue for issue in demo_issues if 'Patient name not found' not in issue]
            else:
                print(f"    ⚠️ LLM could not extract patient name from rawdata")
    
    # IMPORTANT: Only include LLM-related processing issues, not demographics extraction issues
    # Demographics extraction is regex-based, not LLM-based
    llm_processing_issues = processing_issues or []
    
    # Log demographics issues separately (not as processing issues)
    if demo_issues:
        print(f"\n  [Demographics Extraction Issues] ({len(demo_issues)} total):")
        for idx, issue in enumerate(demo_issues, 1):
            print(f"    {idx}. ⚠️  {issue}")
    else:
        print(f"\n  [Demographics Extraction Issues] ✓ None - Clean extraction")
    
    # Get current timestamp for both processedDateTime and dateOfService
    current_datetime = datetime.now()
    processed_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    
    # UPDATED: ALWAYS use current timestamp as dateOfService (processing date/time)
    # Format: MM/DD/YYYY HH:MM AM/PM
    month = str(current_datetime.month)
    day = str(current_datetime.day)
    year = str(current_datetime.year)
    hour_12 = current_datetime.strftime("%I").lstrip("0") or "12"
    minute = current_datetime.strftime("%M")
    am_pm = current_datetime.strftime("%p")
    demographics['date_of_service'] = f"{month}/{day}/{year} {hour_12}:{minute} {am_pm}"
    print(f"    ✓ Date of Service set to current processing timestamp: {demographics['date_of_service']}")
    
    print(f"\n  [Demographics Extraction] Final Results:")
    print(f"    • Patient Full Name: {demographics.get('patient_name', 'MISSING')}")
    print(f"    • Patient MRN: {demographics.get('patient_mrn', 'MISSING')}")
    print(f"    • Location: {demographics.get('location', 'MISSING')}")
    print(f"    • Date of Service (Processing Timestamp): {demographics.get('date_of_service', 'MISSING')}")
    print(f"    • Admission Date: {demographics.get('admission_date', 'MISSING')}")
    print(f"    • Discharge Date: {demographics.get('discharge_date', 'N/A')}")
    
    # Detailed location logging
    if demographics.get('location'):
        print(f"\n  [Location Validation] ✓ PASSED")
        print(f"    • Location value: '{demographics.get('location')}'")
        print(f"    • Location length: {len(demographics.get('location', ''))} characters")
    else:
        print(f"\n  [Location Validation] ✗ FAILED - MANDATORY FIELD MISSING")
        print(f"    • This is a CRITICAL issue that must be resolved")
    
    if llm_processing_issues:
        print(f"\n  [LLM Processing Issues Detected] ({len(llm_processing_issues)} total):")
        for idx, issue in enumerate(llm_processing_issues, 1):
            print(f"    {idx}. ⚠️  {issue}")
    else:
        print(f"\n  [LLM Processing Issues Detected] ✓ None - Clean LLM processing")
    
    # Generate composite key
    note_id = note_data.get('noteId', '')
    composite_key = generate_composite_key(note_id)
    
    # Enhanced timestamp tracking using ProcessingTracker
    tracker = get_current_processing_tracker()
    
    # Get timestamps from tracker or generate fallback timestamps
    if tracker:
        timestamps = tracker.get_timestamps()
        ingestion_epoch = timestamps.get('ingestion', TimestampManager.current_epoch_ms())
        submission_epoch = timestamps.get('submission', TimestampManager.current_epoch_ms())
        processed_epoch = timestamps.get('processed_at', TimestampManager.current_epoch_ms())
        print(f"    ✓ Using ProcessingTracker timestamps for note {note_id}")
    else:
        # Fallback: generate current timestamps
        current_epoch = TimestampManager.current_epoch_ms()
        ingestion_epoch = current_epoch
        submission_epoch = current_epoch
        processed_epoch = current_epoch
        print(f"    ⚠️ ProcessingTracker not found, using fallback timestamps for note {note_id}")
    
    # Enhanced validation using TimestampErrorHandler
    from medical_notes.utils.timestamp_validation import TimestampErrorHandler
    
    ingestion_epoch = TimestampErrorHandler.validate_and_correct_timestamp(
        ingestion_epoch, 'ingestionDateTimeAsEpoch'
    )
    submission_epoch = TimestampErrorHandler.validate_and_correct_timestamp(
        submission_epoch, 'submitDateEpoch'
    )
    processed_epoch = TimestampErrorHandler.validate_and_correct_timestamp(
        processed_epoch, 'processedDateTimeEpoch'
    )
    
    # Validate timestamp format (legacy validation for backward compatibility)
    if not TimestampManager.validate_epoch_timestamp(ingestion_epoch):
        print(f"    ⚠️ Invalid ingestion timestamp after correction, using current time")
        ingestion_epoch = TimestampManager.current_epoch_ms()
    
    if not TimestampManager.validate_epoch_timestamp(submission_epoch):
        print(f"    ⚠️ Invalid submission timestamp after correction, using current time")
        submission_epoch = TimestampManager.current_epoch_ms()
        
    if not TimestampManager.validate_epoch_timestamp(processed_epoch):
        print(f"    ⚠️ Invalid processed timestamp after correction, using current time")
        processed_epoch = TimestampManager.current_epoch_ms()
    
    # Legacy timestamp handling for backward compatibility
    ingestion_datetime = datetime.now().isoformat()
    legacy_ingestion_epoch = None
    try:
        from dateutil import parser as date_parser
        ingestion_dt = date_parser.parse(ingestion_datetime)
        legacy_ingestion_epoch = int(ingestion_dt.timestamp() * 1000)
    except:
        legacy_ingestion_epoch = ingestion_epoch
    
    print(f"\n  [Timestamp Tracking] Enhanced timestamp fields:")
    print(f"    • ingestionDateTimeAsEpoch: {ingestion_epoch}")
    print(f"    • submitDateEpoch: {submission_epoch}")
    print(f"    • processedDateTimeEpoch: {processed_epoch}")
    
    # Prepare the record with enhanced tracking columns
    record = {
        '_id': composite_key,
        'composite_key': composite_key,
        'noteId': int(note_data['noteId']) if str(note_data['noteId']).isdigit() else note_data['noteId'],
        'patientName': demographics.get('patient_name', ''),
        'patientmrn': demographics.get('patient_mrn', ''),
        'location': demographics.get('location', ''),
        'admissionDate': demographics.get('admission_date', ''),
        'dateOfService': demographics.get('date_of_service', ''),
        'dischargeDate': demographics.get('discharge_date', ''),
        'ingestionDateTime': ingestion_datetime,
        'ingestionDate': datetime.now().strftime('%Y-%m-%d'),  # Date-only format yyyy-MM-dd
        'ingestionDateTimeasEpoch': legacy_ingestion_epoch,  # Legacy field for backward compatibility
        'ingestionDateTimeAsEpoch': ingestion_epoch,  # New enhanced timestamp field
        'noteType': note_type,
        'notesProcessedPlainText': processed_text,  # Plain text version from processed_data
        'soapnotesPlainText': soap_text,  # Plain text version of SOAP notes from soap_data
        'notesProcessedStatus': 'processed',
        'processedDateTime': processed_datetime,
        'processedDateTimeEpoch': processed_epoch,  # New enhanced timestamp field
        'processingIssues': '; '.join(llm_processing_issues) if llm_processing_issues else '',
        'submitDateTime': '',  # Will be updated after API push
        'submitDateEpoch': submission_epoch,  # New enhanced timestamp field
        'submittingIssues': ''  # Will be updated if API push fails
    }
    
    # Final validation of the complete record
    from medical_notes.utils.timestamp_validation import validate_and_log_timestamps
    validated_record = validate_and_log_timestamps(record, "processed_notes")
    
    return validated_record


def package_note_data(note_data: Dict[str, Any], note_type: str) -> Dict[str, Any]:
    """
    Package validated note data for main processing pipeline.
    
    Creates a comprehensive data package containing all required information
    for the parallel processing workflows.
    
    Args:
        note_data: Dictionary containing note data from Elasticsearch
        note_type: Normalized note type
        
    Returns:
        Dictionary containing packaged data with all required fields
        
    Requirements: 3.1, 3.2
    """
    # Extract MRN from note data or raw data
    mrn = note_data.get('patientmrn')
    if not mrn:
        # Fallback: extract MRN from raw data using existing function
        from medical_notes.service.note_type_extractor import extract_mrn
        mrn = extract_mrn(note_data.get('rawdata', ''))
    
    # Package all required data
    packaged_data = {
        'note_id': note_data['noteId'],
        'raw_data': note_data['rawdata'],
        'note_type': note_type,
        'mrn': mrn,
        'original_note_data': note_data.copy()
    }
    
    return packaged_data


def execute_parallel_processing(packaged_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute all three processing workflows using the existing MedicalNotesGenerator.
    
    This function now delegates to the existing MedicalNotesGenerator which already
    handles all three template types (note_type, soap, notes_digest) in a single call.
    
    Args:
        packaged_data: Dictionary containing packaged note data
        
    Returns:
        Dictionary containing all processing results and any errors
        
    Requirements: 3.3, 6.5
    """
    processing_results = {
        'template_result': None,
        'soap_result': None,
        'digest_result': None,
        'errors': [],
        'original_data': packaged_data
    }
    
    raw_data = packaged_data['raw_data']
    note_type = packaged_data['note_type']
    # Get patient_id from original note data to pass to LLM for context
    patient_id = packaged_data.get('original_note_data', {}).get('patientID', '')
    
    try:
        # Use extract_structured_data which now uses MedicalNotesGenerator
        # Pass patient_id to LLM for patient context
        processed_text, soap_text, notes_digest, error = extract_structured_data(raw_data, note_type, patient_id=patient_id)
        
        if error:
            processing_results['errors'].append(error)
        
        # Assign results
        processing_results['template_result'] = processed_text
        processing_results['soap_result'] = soap_text
        processing_results['digest_result'] = notes_digest
        
        # Log success for each completed workflow
        if processed_text:
            print(f"✓ Template processing completed for note type: {note_type}")
        if soap_text:
            print(f"✓ SOAP generation completed using unified template system")
        if notes_digest:
            print(f"✓ Digest creation completed using unified template system")
            
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        processing_results['errors'].append(error_msg)
        print(f"✗ {error_msg}")
    
    return processing_results


def route_to_main_pipeline(packaged_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route packaged data to the main processing pipeline coordinator.
    
    This function serves as the entry point for the main processing pipeline,
    coordinating the execution of all processing workflows.
    
    Args:
        packaged_data: Dictionary containing packaged note data
        
    Returns:
        Dictionary containing all processing results
        
    Requirements: 3.2, 3.3
    """
    print(f"\n[Main Pipeline] Starting processing for note ID: {packaged_data['note_id']}")
    print(f"[Main Pipeline] Note type: {packaged_data['note_type']}")
    print(f"[Main Pipeline] MRN: {packaged_data['mrn']}")
    
    # Execute parallel processing workflows
    processing_results = execute_parallel_processing(packaged_data)
    
    # Log processing summary
    successful_workflows = sum(1 for key in ['template_result', 'soap_result', 'digest_result'] 
                              if processing_results[key] is not None)
    total_workflows = 3
    
    print(f"\n[Main Pipeline] Processing completed: {successful_workflows}/{total_workflows} workflows successful")
    
    if processing_results['errors']:
        print(f"[Main Pipeline] Errors encountered: {len(processing_results['errors'])}")
        for error in processing_results['errors']:
            print(f"  - {error}")
    
    return processing_results


def index_to_elasticsearch(es_record: Dict[str, Any], notes_digest: str, note_type: str) -> Dict[str, Any]:
    """
    Index processed notes and digest to Elasticsearch with independent error handling.
    
    This function implements the Elasticsearch indexing system that:
    1. Creates DataFrame conversion logic for all record types
    2. Implements processed notes indexing to ES_INDEX_PROCESSED_NOTES
    3. Implements digest indexing to ES_INDEX_NOTES_DIGEST
    4. Adds independent error handling for each index
    
    Args:
        es_record: Complete Elasticsearch record for processed notes
        notes_digest: Notes digest text for digest index
        note_type: Normalized note type
        
    Returns:
        Dictionary containing indexing results and any errors
        
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 9.3
    """
    indexing_results = {
        "processed_notes_success": False,
        "digest_success": False,
        "errors": [],
        "processed_notes_error": None,
        "digest_error": None
    }
    
    print(f"\n[Elasticsearch Indexing] Starting indexing operations...")
    
    # Index processed notes (independent error handling)
    try:
        print(f"  Converting processed note to DataFrame and indexing to {ES_INDEX_PROCESSED_NOTES}...")
        es_df = pd.DataFrame([es_record])
        df_to_es_load(es_df, ES_INDEX_PROCESSED_NOTES)
        indexing_results["processed_notes_success"] = True
        print(f"  ✓ Processed note indexed successfully")
        print(f"     - Note ID: {es_record['noteId']}")
        print(f"     - Composite Key: {es_record['_id']}")
        print(f"     - Index: {ES_INDEX_PROCESSED_NOTES}")
    except Exception as e:
        error_msg = f"Failed to index processed note to {ES_INDEX_PROCESSED_NOTES}: {str(e)}"
        indexing_results["errors"].append(error_msg)
        indexing_results["processed_notes_error"] = str(e)
        print(f"  ✗ {error_msg}")

    # Index notes digest (independent error handling)
    try:
        print(f"  Converting notes digest to DataFrame and indexing to {ES_INDEX_NOTES_DIGEST}...")
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
        if notes_digest:
            try:
                from medical_notes.config.config import ENABLE_DATA_FLATTENING
                if ENABLE_DATA_FLATTENING:
                    import json
                    from medical_notes.utils.data_flattening import flatten_all_nested_objects
                    from datetime import datetime
                    
                    # Parse the notes_digest JSON string
                    digest_json = json.loads(notes_digest) if isinstance(notes_digest, str) else notes_digest
                    
                    # Apply flattening to the parsed digest
                    flattened_digest, flattening_issues = flatten_all_nested_objects(digest_json)
                    
                    # Add all flattened fields to digest_record
                    digest_record.update(flattened_digest)
                    
                    # Add epoch timestamp fields
                    current_time = datetime.now()
                    epoch_ms = int(current_time.timestamp() * 1000)
                    
                    digest_record['ingestionDateTime_epoch'] = epoch_ms
                    digest_record['processedDateTime_epoch'] = epoch_ms
                    
                    # Add epoch fields for date fields if they exist and are parseable
                    from medical_notes.service.app import parse_service_date_to_epoch
                    date_fields = ['dateofbirth', 'dateofadmission', 'dateofdischarge', 'dateofservice']
                    for date_field in date_fields:
                        if date_field in digest_record and digest_record[date_field]:
                            try:
                                epoch_field = f"{date_field}_epoch"
                                epoch_value = parse_service_date_to_epoch(digest_record[date_field])
                                digest_record[epoch_field] = epoch_value if epoch_value else 0
                            except:
                                digest_record[f"{date_field}_epoch"] = 0
                    
                    print(f"     - Applied data flattening: {len(flattened_digest)} fields added")
                    if flattening_issues:
                        print(f"     - Flattening issues: {len(flattening_issues)}")
                        
            except Exception as e:
                print(f"     - Flattening failed: {str(e)} (continuing with basic record)")
                pass
        
        digest_df = pd.DataFrame([digest_record])
        df_to_es_load(digest_df, ES_INDEX_NOTES_DIGEST)
        indexing_results["digest_success"] = True
        print(f"  ✓ Notes digest indexed successfully")
        print(f"     - Note ID: {digest_record['noteId']}")
        print(f"     - Composite Key: {digest_record['composite_key']}")
        print(f"     - Index: {ES_INDEX_NOTES_DIGEST}")
    except Exception as e:
        error_msg = f"Failed to index notes digest to {ES_INDEX_NOTES_DIGEST}: {str(e)}"
        indexing_results["errors"].append(error_msg)
        indexing_results["digest_error"] = str(e)
        print(f"  ✗ {error_msg}")

    # Report indexing results
    if indexing_results["processed_notes_success"] and indexing_results["digest_success"]:
        print(f"\n✓ All Elasticsearch indexing operations completed successfully")
    elif indexing_results["processed_notes_success"] or indexing_results["digest_success"]:
        print(f"\n⚠️ Partial Elasticsearch indexing success:")
        print(f"   - Processed notes: {'✓' if indexing_results['processed_notes_success'] else '✗'}")
        print(f"   - Notes digest: {'✓' if indexing_results['digest_success'] else '✗'}")
    else:
        print(f"\n✗ All Elasticsearch indexing operations failed")
        
    if indexing_results["errors"]:
        print(f"   Indexing errors: {len(indexing_results['errors'])}")
        for error in indexing_results["errors"]:
            print(f"     - {error}")
    
    return indexing_results


def process_single_note(note_id):
    """
    Process a single medical note by noteId with issue tracking
    """
    print("=" * 80)
    print(f"PROCESSING MEDICAL NOTE")
    print(f"Note ID: {note_id}")
    print("=" * 80)
    
    processing_issues = []
    
    results = {
        "success": False,
        "note_id": note_id,
        "note_type": None,
        "processed": False,
        "soap_generated": False,
        "demographics_extracted": False,
        "processed_notes_indexed": False,
        "digest_indexed": False,
        "message": "",
        "errors": [],
        "processing_issues": [],
        "indexing_errors": []
    }
    
    try:
        # Step 1: Check if noteId exists
        print(f"\n[Step 1] Checking if noteId exists in {ES_INDEX_CLINICAL_NOTES}...")
        notes = get_notes_by_noteid(ES_INDEX_CLINICAL_NOTES, note_id)
        
        if not notes or len(notes) == 0:
            error_msg = f"noteId '{note_id}' not found in {ES_INDEX_CLINICAL_NOTES} index"
            results["message"] = error_msg
            results["errors"].append(error_msg)
            # NOTE: This is a data validation error, not an LLM processing error
            print(f"✗ {error_msg}")
            return results
        
        note_data = notes[0]
        current_status = note_data.get('status', '')
        
        if current_status == 'processed':
            error_msg = f"noteId '{note_id}' has already been processed"
            results["message"] = error_msg
            results["errors"].append(error_msg)
            # NOTE: This is a business logic error, not an LLM processing error
            print(f"✗ {error_msg}")
            return results
        
        print(f"✓ noteId '{note_id}' found in index")
        
        # Step 2: Fetch rawdata
        print(f"\n[Step 2] Fetching rawdata from {ES_INDEX_CLINICAL_NOTES}...")
        rawdata = note_data.get('rawdata', '')
        
        if not rawdata:
            error_msg = "Note found but rawdata is empty"
            results["message"] = error_msg
            results["errors"].append(error_msg)
            # NOTE: This is a data validation error, not an LLM processing error
            print(f"✗ {error_msg}")
            return results
        
        print(f"✓ rawdata fetched successfully (length: {len(rawdata)} characters)")
        
        # Step 3: Get note type from Elasticsearch document
        print("\n[Step 3] Getting note type from document...")
        raw_note_type = note_data.get('noteType')

        if not raw_note_type:
            # Fallback: if noteType is not in the document, extract from rawdata
            print("  ⚠️ noteType not found in document, extracting from rawdata as fallback...")
            raw_note_type = extract_note_type(rawdata)

        note_type = normalize_note_type(raw_note_type)
        print(f"  ✓ Normalized note type: {note_type} (raw: {raw_note_type})")

        if not note_type:
            error_msg = "Could not identify note type from document or raw text"
            results["message"] = error_msg
            results["errors"].append(error_msg)
            # NOTE: Note type extraction failure could be LLM-related if using LLM fallback
            # But if it's from document, it's a data issue. Let's be conservative and not add it.
            print(f"✗ {error_msg}")
            return results
        
        results["note_type"] = note_type
        print(f"✓ Note type retrieved from document: {note_type}")
        
        # Step 4: Package data for main processing pipeline
        print("\n[Step 4] Packaging data for main processing pipeline...")
        packaged_data = package_note_data(note_data, note_type)
        print(f"✓ Data packaged successfully")
        print(f"  - Note ID: {packaged_data['note_id']}")
        print(f"  - Note Type: {packaged_data['note_type']}")
        print(f"  - MRN: {packaged_data['mrn']}")
        print(f"  - Raw Data Length: {len(packaged_data['raw_data'])} characters")
        
        # Step 5: Route to main processing pipeline
        print("\n[Step 5] Routing to main processing pipeline...")
        processing_results = route_to_main_pipeline(packaged_data)
        
        # Extract results from parallel processing
        processed_text = processing_results.get('template_result')
        soap_text = processing_results.get('soap_result')
        notes_digest = processing_results.get('digest_result')
        
        # Collect any LLM processing errors (not system/indexing errors)
        if processing_results.get('errors'):
            # Filter to only include LLM-related errors
            for error in processing_results['errors']:
                if is_llm_processing_error(error):
                    processing_issues.append(error)
        
        # Verify at least some processing succeeded
        if not processed_text and not soap_text and not notes_digest:
            error_msg = "All processing workflows failed"
            results["message"] = error_msg
            results["errors"].append(error_msg)
            # This could be an LLM processing failure - add to processing_issues
            processing_issues.append(error_msg)
            print(f"✗ {error_msg}")
            return results
        
        # Update results based on successful processing
        if processed_text:
            results["processed"] = True
            print(f"✓ Template-based processing completed")
        
        if soap_text:
            results["soap_generated"] = True
            print(f"✓ SOAP generation completed")
        
        print(f"✓ Main processing pipeline completed successfully")
        
        # Step 6: Push to processed notes index
        print(f"\n[Step 6] Pushing processed data to {ES_INDEX_PROCESSED_NOTES}...")

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

        if es_record['patientmrn']:
            results["demographics_extracted"] = True

        # Step 6: Index to Elasticsearch using dedicated indexing system
        print(f"\n[Step 6] Indexing to Elasticsearch indices with independent error handling...")
        indexing_results = index_to_elasticsearch(es_record, notes_digest, note_type)
        
        # NOTE: Elasticsearch indexing errors are not LLM processing errors
        # Update results with indexing status but don't add to processing_issues
        results["indexing_errors"] = indexing_results["errors"]
        results["processed_notes_indexed"] = indexing_results["processed_notes_success"]
        results["digest_indexed"] = indexing_results["digest_success"]
        
        # Step 7: Update status in original index
        print(f"\n[Step 7] Updating status in {ES_INDEX_CLINICAL_NOTES}...")
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
        
        print(f"✓ Status updated to 'processed' for noteId '{note_id}'")
        
        results["success"] = True
        results["message"] = "Note processed successfully"
        results["processing_issues"] = processing_issues
        
        # Log final success status
        if results["processed_notes_indexed"] and results["digest_indexed"]:
            print(f"\n✓ Complete processing success: Note processed and indexed to both indices")
        elif results["processed_notes_indexed"] or results["digest_indexed"]:
            print(f"\n⚠️ Partial processing success: Note processed but only indexed to {'processed notes' if results['processed_notes_indexed'] else 'digest'} index")
        else:
            print(f"\n⚠️ Processing completed but indexing failed for both indices")
        
        print("\n" + "=" * 80)
        print("PROCESSING COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        error_msg = f"Processing failed with error: {str(e)}"
        results["message"] = error_msg
        results["errors"].append(str(e))
        # NOTE: General exceptions are typically system errors, not LLM processing errors
        # Only add to processing_issues if it's specifically an LLM-related error
        if is_llm_processing_error(str(e)):
            processing_issues.append(error_msg)
        results["processing_issues"] = processing_issues
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return results

def process_and_store_notes(data):
    """
    Process notes and store them in appropriate indices.
    """
    notesProcessedPlainText = data.get('processed_data', '')
    soapnotesPlainText = data.get('soap_data', '')
    notes_digest = data.get('notes_digest', '')

    # Push notes_digest to another index
    if notes_digest:
        print("Pushing notes_digest to another index...")
        # Logic to push notes_digest to the appropriate index
        # Example: update_to_another_index(notes_digest)

    return notesProcessedPlainText, soapnotesPlainText