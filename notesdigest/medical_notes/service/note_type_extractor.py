"""
Simplified Note Type and MRN Extractor using LLM
With token usage tracking
"""

import os
import json
import re
import boto3
from dotenv import load_dotenv
from medical_notes.service.token_tracker import add_token_usage, extract_token_usage_from_response

load_dotenv()


def extract_note_type_and_mrn(raw_text, sample_fraction=0.25):
    """
    Extract note type AND patient MRN from raw medical text using LLM.
    
    Args:
        raw_text: The full raw medical note text
        sample_fraction: Fraction of text to use for extraction (0.25 = 25%)
    
    Returns:
        tuple: (note_type, patient_mrn)
               note_type: str - Note type key (history_physical, discharge_summary, etc.)
               patient_mrn: str or None - Patient MRN if found, None otherwise
    """
    # TODO: Enable timing features later
    # from datetime import datetime
    
    if not raw_text or not raw_text.strip():
        return "generic_note", None
    
    # TODO: Enable timing features later
    # Record start time
    # start_time = datetime.now()
    
    try:
        # Sample from beginning (where MRN typically appears)
        sample_size = int(len(raw_text) * sample_fraction)
        text_sample = raw_text[:sample_size]
        
        # Initialize Bedrock
        bedrock = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        ).client("bedrock-runtime")
        
        # Improved prompt with clearer MRN extraction rules
        prompt = f"""Extract note type and patient MRN from this medical note.

NOTE TYPES (return exactly one):
- history_physical: Initial evaluation with comprehensive history/exam
- discharge_summary: Hospital discharge documentation
- consultation_note: Specialist consultation
- progress_note: Daily hospital update
- procedure_note: Procedure documentation
- ed_note: Emergency department visit
- generic_note: Other/mixed content

MRN EXTRACTION RULES:(return full mrn value)
- Find the label "MRN:" or "MRN :" or "mrn:" in the text
- Extract ONLY the value immediately after "MRN:" up to (but not including) the next space
- The MRN can contain letters, numbers, and special characters - extract them all until you hit a space
- DO NOT include any text that comes after the first space following the MRN value
- Examples:
  * "MRN: MRN007Rachel Niya Mariya" → extract "MRN007Rachel" (stop at space before "Niya")
  * "mrn : 12345678 niya maria" → extract "12345678"
  * "MRN: 987XY23 john doe" → extract "987XY23"
  * "mrn : joy12345db michael" → extract "joy12345db"
  * "mrn : xxxxxjoy fatima" → extract "xxxxxjoy"
- Return ONLY the MRN value, nothing else , there should not be any explination or extra text

MEDICAL NOTE:
{text_sample}

Return ONLY in this exact format (no extra text):
NOTE_TYPE: <type>
PATIENT_MRN: <complete_mrn_value>"""

        # Call Bedrock with Claude Haiku 3.5
        response = bedrock.invoke_model(
            modelId=os.getenv("CLAUDE_HAIKU_4_5","us.anthropic.claude-haiku-4-5-20251001-v1:0"),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 100,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        # Parse response
        response_body = json.loads(response['body'].read())
        response_text = response_body['content'][0]['text'].strip()
        
        # TODO: Enable timing features later
        # Record end time
        # end_time = datetime.now()
        # duration = (end_time - start_time).total_seconds()
        
        # Track token usage (without timing for now)
        input_tokens, output_tokens = extract_token_usage_from_response(response_body)
        add_token_usage("note_type_mrn_extraction", input_tokens, output_tokens)
        print(f"  📊 Token usage (note_type_mrn): {input_tokens:,} in / {output_tokens:,} out")
        # TODO: Enable timing features later
        # add_token_usage("note_type_mrn_extraction", input_tokens, output_tokens, start_time, end_time)
        # print(f"  📊 Token usage (note_type_mrn): {input_tokens:,} in / {output_tokens:,} out ({duration:.2f}s)")
        
        note_type = "generic_note"
        patient_mrn = None
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('NOTE_TYPE:'):
                note_type = line.split(':', 1)[1].strip().lower()
                valid_types = ['history_physical', 'discharge_summary', 'consultation_note',
                             'progress_note', 'procedure_note', 'ed_note', 'generic_note']
                if note_type not in valid_types:
                    note_type = 'generic_note'
                
            elif line.startswith('PATIENT_MRN:'):
                mrn = line.split(':', 1)[1].strip()
                # Remove any trailing punctuation or whitespace
                mrn = mrn.rstrip('.,;:!? \t\n\r')
                if mrn and mrn.upper() != 'NOT_FOUND':
                    patient_mrn = mrn
        
        # Log results
        print(f"  ✓ Note type: {note_type}")
        print(f"  {'✓' if patient_mrn else '⚠️'} MRN (LLM): {patient_mrn or 'not found'}")
        
        # If MRN extraction failed with LLM, try regex fallback
        if not patient_mrn:
            print(f"  🔄 Trying regex fallback for MRN extraction...")
            regex_mrn = extract_mrn_with_regex_fallback(raw_text)
            if regex_mrn:
                patient_mrn = regex_mrn
        
        return note_type, patient_mrn
    
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return "generic_note", None


# Convenience functions for backward compatibility
def extract_note_type(raw_text, sample_fraction=0.25):
    """
    Legacy function - Extract only note type (for backward compatibility)
    
    Args:
        raw_text: The full raw medical note text
        sample_fraction: Fraction of text to use
    
    Returns:
        str: Note type key
    """
    note_type, _ = extract_note_type_and_mrn(raw_text, sample_fraction)
    return note_type


def extract_patient_name(raw_text, sample_fraction=0.25, known_patient_id=None):
    """
    Extract patient name from raw medical text using LLM with regex fallback.
    
    Args:
        raw_text: The full raw medical note text
        sample_fraction: Fraction of text to use for extraction (0.25 = 25%)
        known_patient_id: Optional known patient ID from clinical notes index for validation
    
    Returns:
        str or None: Patient name if found, None otherwise
    """
    if not raw_text or not raw_text.strip():
        return None
    
    try:
        # First try LLM-based extraction
        # Sample from beginning (where patient name typically appears)
        sample_size = int(len(raw_text) * sample_fraction)
        text_sample = raw_text[:sample_size]
        
        # Initialize Bedrock
        bedrock = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        ).client("bedrock-runtime")
        
        # Build prompt with optional known patient ID context
        known_patient_context = ""
        if known_patient_id:
            known_patient_context = f"""
KNOWN PATIENT INFORMATION:
- The patient ID from the clinical notes index is: "{known_patient_id}"
- This is the known/confirmed patient. Use this to help verify the patient name you extract.
- If the extracted name matches or corresponds to this patient ID, confirm it.
"""
            print(f"  📋 Including known patientID in LLM prompt for validation: '{known_patient_id}'")
        
        # Optimized prompt for patient name extraction
        prompt = f"""Extract the patient name from this medical note.
{known_patient_context}
PATIENT NAME EXTRACTION RULES:
- Find the patient's full name in the medical record
- Look for patterns like "Patient Name:", "Name:", "Patient:", or patient identification sections
- Extract the complete name (first and last name, middle name if present)
- Do NOT include titles (Mr., Mrs., Dr.), credentials, or other text
- Examples:
  * "Patient Name: John Michael Smith" → extract "John Michael Smith"
  * "Name: Sarah Johnson" → extract "Sarah Johnson"
  * "Patient: Maria Elena Rodriguez" → extract "Maria Elena Rodriguez"
  * "Mr. Robert Davis" → extract "Robert Davis" (remove title)
- Return ONLY the patient name, nothing else, there should not be any explanation or extra text
- If no clear patient name is found, return "NOT_FOUND"

MEDICAL NOTE:
{text_sample}

Return ONLY in this exact format (no extra text):
PATIENT_NAME: <complete_patient_name>"""

        # Call Bedrock with Claude Haiku
        response = bedrock.invoke_model(
            modelId=os.getenv("CLAUDE_HAIKU_4_5","us.anthropic.claude-haiku-4-5-20251001-v1:0"),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,  # Reduced since we only need patient name
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        response_text = response_body['content'][0]['text'].strip()
        
        # Track token usage
        input_tokens, output_tokens = extract_token_usage_from_response(response_body)
        add_token_usage("patient_name_extraction", input_tokens, output_tokens)
        print(f"  📊 Token usage (patient_name): {input_tokens:,} in / {output_tokens:,} out")
        
        patient_name = None
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('PATIENT_NAME:'):
                name = line.split(':', 1)[1].strip()
                # Remove any trailing punctuation or whitespace
                name = name.rstrip('.,;:!? \t\n\r')
                # Remove common titles
                name = re.sub(r'^(Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Miss)\s+', '', name, flags=re.IGNORECASE)
                if name and name.upper() != 'NOT_FOUND' and len(name) > 2:
                    patient_name = name
                break  # Found name, no need to continue
        
        # Log result
        print(f"  {'✓' if patient_name else '⚠️'} Patient Name (LLM): {patient_name or 'not found'}")
        
        # If LLM extraction succeeded, return the result
        if patient_name:
            return patient_name
        
        # If LLM extraction failed, try regex fallback
        print(f"  🔄 Trying regex fallback for patient name extraction...")
        regex_name = extract_patient_name_with_regex_fallback(raw_text)
        if regex_name:
            return regex_name
        
        return None
        
    except Exception as e:
        print(f"  ✗ Error extracting patient name with LLM: {str(e)}")
        print(f"  🔄 Trying regex fallback for patient name extraction...")
        
        # If LLM fails completely, try regex fallback
        try:
            return extract_patient_name_with_regex_fallback(raw_text)
        except Exception as regex_e:
            print(f"  ✗ Error extracting patient name with regex: {str(regex_e)}")
            return None


def extract_patient_name_with_regex_fallback(raw_text):
    """
    Extract patient name using regex patterns as fallback when LLM extraction fails.
    
    Args:
        raw_text: The full raw medical note text
    
    Returns:
        str or None: Patient name if found, None otherwise
    """
    if not raw_text or not raw_text.strip():
        return None
    
    # Define regex patterns for patient name extraction
    name_patterns = [
        # Standard patient name patterns with colon requirement
        r'Patient\s*Name\s*:\s*([A-Za-z\s\-\'\.]+?)(?:\n|\r|MRN|DOB|$)',
        r'Name\s*:\s*([A-Za-z\s\-\'\.]+?)(?:\n|\r|MRN|DOB|$)',
        r'Patient\s*:\s*([A-Za-z\s\-\'\.]+?)(?:\n|\r|MRN|DOB|$)',
        r'Full\s*Name\s*:\s*([A-Za-z\s\-\'\.]+?)(?:\n|\r|MRN|DOB|$)',
        # Patterns with dash
        r'Patient\s*Name\s*-\s*([A-Za-z\s\-\'\.]+?)(?:\n|\r|MRN|DOB|$)',
        r'Name\s*-\s*([A-Za-z\s\-\'\.]+?)(?:\n|\r|MRN|DOB|$)',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up the name - remove common suffixes and extra whitespace
            name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
            name = name.rstrip('.,;:')  # Remove trailing punctuation
            # Remove common titles
            name = re.sub(r'^(Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Miss)\s+', '', name, flags=re.IGNORECASE)
            
            # Skip if it looks like it's not actually a name (too short, contains numbers, etc.)
            if len(name) > 2 and not re.search(r'\d', name):
                print(f"  ✓ Patient name extracted via regex: {name}")
                return name
    
    print(f"  ⚠️ Patient name not found via regex patterns")
    return None


def extract_mrn_with_regex_fallback(raw_text):
    """
    Extract MRN using regex patterns as fallback when LLM extraction fails.
    
    Args:
        raw_text: The full raw medical note text
    
    Returns:
        str or None: Patient MRN if found, None otherwise
    """
    if not raw_text or not raw_text.strip():
        return None
    
    # Define regex patterns for MRN extraction - require colon or specific context
    mrn_patterns = [
        # Standard MRN patterns with colon requirement
        r'MRN\s*:\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # MRN: followed by alphanumeric
        r'mrn\s*:\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # mrn: followed by alphanumeric
        r'Medical\s*Record\s*Number\s*:\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # Full form with colon
        r'Patient\s*MRN\s*:\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # Patient MRN: with colon
        r'Record\s*ID\s*:\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # Record ID: with colon
        r'Patient\s*ID\s*:\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # Patient ID: with colon
        # Patterns with dash
        r'MRN\s*-\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # MRN - followed by alphanumeric
        r'mrn\s*-\s*([A-Za-z0-9]+)(?=\s|$|[^\w])',  # mrn - followed by alphanumeric
    ]
    
    for pattern in mrn_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            mrn = match.group(1).strip()
            # Remove any trailing punctuation
            mrn = mrn.rstrip('.,;:!?')
            if mrn:  # Ensure we have a non-empty MRN
                print(f"  ✓ MRN extracted via regex: {mrn}")
                return mrn
    
    print(f"  ⚠️ MRN not found via regex patterns")
    return None


def extract_mrn(raw_text, sample_fraction=0.25):
    """
    Extract only patient MRN from raw medical text with regex fallback.
    
    Args:
        raw_text: The full raw medical note text
        sample_fraction: Fraction of text to use for extraction (0.25 = 25%)
    
    Returns:
        str or None: Patient MRN if found, None otherwise
    """
    # TODO: Enable timing features later
    # from datetime import datetime
    
    if not raw_text or not raw_text.strip():
        return None
    
    # TODO: Enable timing features later
    # Record start time
    # start_time = datetime.now()
    
    try:
        # First try LLM-based extraction
        # Sample from beginning (where MRN typically appears)
        sample_size = int(len(raw_text) * sample_fraction)
        text_sample = raw_text[:sample_size]
        
        # Initialize Bedrock
        bedrock = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        ).client("bedrock-runtime")
        
        # Optimized prompt - only extracts MRN, no note type
        prompt = f"""Extract the patient MRN from this medical note.

MRN EXTRACTION RULES (return full mrn value):
- Find the label "MRN:" or "MRN :" or "mrn:" in the text
- Extract ONLY the value immediately after "MRN:" up to (but not including) the next space
- The MRN can contain letters, numbers, and special characters - extract them all until you hit a space
- DO NOT include any text that comes after the first space following the MRN value
- Examples:
  * "MRN: MRN007Rachel Niya Mariya" → extract "MRN007Rachel" (stop at space before "Niya")
  * "mrn : 12345678 niya maria" → extract "12345678"
  * "MRN: 987XY23 john doe" → extract "987XY23"
  * "mrn : joy12345db michael" → extract "joy12345db"
  * "mrn : xxxxxjoy fatima" → extract "xxxxxjoy"
- Return ONLY the MRN value, nothing else, there should not be any explanation or extra text

MEDICAL NOTE:
{text_sample}

Return ONLY in this exact format (no extra text):
PATIENT_MRN: <complete_mrn_value>"""

        # Call Bedrock with Claude Haiku
        response = bedrock.invoke_model(
            modelId=os.getenv("CLAUDE_HAIKU_4_5","us.anthropic.claude-haiku-4-5-20251001-v1:0"),
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,  # Reduced since we only need MRN
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        response_text = response_body['content'][0]['text'].strip()
        
        # TODO: Enable timing features later
        # Record end time
        # end_time = datetime.now()
        # duration = (end_time - start_time).total_seconds()
        
        # Track token usage (without timing for now)
        input_tokens, output_tokens = extract_token_usage_from_response(response_body)
        add_token_usage("mrn_extraction", input_tokens, output_tokens)
        print(f"  📊 Token usage (mrn_only): {input_tokens:,} in / {output_tokens:,} out")
        # TODO: Enable timing features later
        # add_token_usage("mrn_extraction", input_tokens, output_tokens, start_time, end_time)
        # print(f"  📊 Token usage (mrn_only): {input_tokens:,} in / {output_tokens:,} out ({duration:.2f}s)")
        
        patient_mrn = None
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith('PATIENT_MRN:'):
                mrn = line.split(':', 1)[1].strip()
                # Remove any trailing punctuation or whitespace
                mrn = mrn.rstrip('.,;:!? \t\n\r')
                if mrn and mrn.upper() != 'NOT_FOUND':
                    patient_mrn = mrn
                break  # Found MRN, no need to continue
        
        # Log result
        print(f"  {'✓' if patient_mrn else '⚠️'} MRN (LLM): {patient_mrn or 'not found'}")
        
        # If LLM extraction succeeded, return the result
        if patient_mrn:
            return patient_mrn
        
        # If LLM extraction failed, try regex fallback
        print(f"  🔄 Trying regex fallback for MRN extraction...")
        regex_mrn = extract_mrn_with_regex_fallback(raw_text)
        if regex_mrn:
            return regex_mrn
        
        return None
        
    except Exception as e:
        print(f"  ✗ Error extracting MRN with LLM: {str(e)}")
        print(f"  🔄 Trying regex fallback for MRN extraction...")
        
        # If LLM fails completely, try regex fallback
        try:
            return extract_mrn_with_regex_fallback(raw_text)
        except Exception as regex_e:
            print(f"  ✗ Error extracting MRN with regex: {str(regex_e)}")
            return None