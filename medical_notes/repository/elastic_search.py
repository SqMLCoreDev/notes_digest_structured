# elastic search loader
"""
Elasticsearch Data Loader Script - Updated for Tracking Fields and Data Flattening
Handles: processedDateTime, processingIssues, submitDateTime, submittingIssues
Includes: Comprehensive data structure flattening for all nested objects
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import dateutil.parser
from collections import deque

from elasticsearch import helpers, Elasticsearch
from elasticsearch.helpers import parallel_bulk
from elasticsearch.helpers.errors import BulkIndexError

# Import the comprehensive flattening function
from medical_notes.utils.data_flattening import flatten_all_nested_objects

import warnings
warnings.filterwarnings("ignore")


class NpEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types and pandas NA values"""
    def default(self, obj):
        try:
            if isinstance(obj, np.generic):
                return obj.item()
            elif isinstance(obj, (np.ndarray, list)):
                return [self.default(x) for x in obj]
            elif pd.isna(obj):
                return None
            return super().default(obj)
        except Exception:
            return str(obj)


def format_date_for_es(value):
    """
    Convert date to ISO 8601 format (yyyy-MM-dd) that Elasticsearch accepts
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    
    try:
        if isinstance(value, str):
            if value.strip() in ["", "nan", "none", "N/A"]:
                return None
            parsed_date = dateutil.parser.parse(value)
        elif isinstance(value, (pd.Timestamp, datetime)):
            parsed_date = value
        elif isinstance(value, (int, float)):
            if value > 10000000000:
                parsed_date = datetime.fromtimestamp(value / 1000)
            else:
                parsed_date = datetime.fromtimestamp(value)
        else:
            return None
        
        return parsed_date.strftime("%Y-%m-%d")
    except Exception as e:
        return None


def format_datetime_for_es(value):
    """
    Convert datetime to ISO 8601 format (yyyy-MM-dd HH:mm:ss) for datetime fields
    Used for: ingestionDateTime, processedDateTime, submitDateTime
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    
    try:
        if isinstance(value, str):
            if value.strip() in ["", "nan", "none", "N/A"]:
                return None
            parsed_dt = dateutil.parser.parse(value)
        elif isinstance(value, (pd.Timestamp, datetime)):
            parsed_dt = value
        elif isinstance(value, (int, float)):
            if value > 10000000000:
                parsed_dt = datetime.fromtimestamp(value / 1000)
            else:
                parsed_dt = datetime.fromtimestamp(value)
        else:
            return None
        
        return parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        return None


def df_to_es_load(newdf, dataset_id):
    """
    Load DataFrame to Elasticsearch with automatic mapping generation
    Supports composite key (_id) field and tracking fields
    """
    from medical_notes.config.config import ES_URL, ES_USER, ES_PASSWORD
   
    if not ES_URL:
        raise ValueError("ES_URL is not defined. Please set the Elasticsearch URL.")

    dataset_id = dataset_id.lower()
    ingestionTS = int(datetime.now().timestamp() * 1000)
    print("ingestionTS", ingestionTS)
    newdf["ingestionTS"] = ingestionTS

    # Elasticsearch client setup
    print("Connecting to:", ES_URL)
    Parallel_ES_client = Elasticsearch(
        [ES_URL],
        http_auth=(ES_USER, ES_PASSWORD),
        request_timeout=10000,
        verify_certs=True
    )

    print("10- {}".format(datetime.now()))

    # Get existing index mapping
    index_mapping = {}
    if Parallel_ES_client.indices.exists(index=dataset_id):
        try:
            mapping_response = Parallel_ES_client.indices.get_mapping(index=dataset_id)
            index_mapping = mapping_response.get(dataset_id, {}).get('mappings', {}).get('properties', {})
            print(f"Using existing index mapping for '{dataset_id}'")
        except Exception as e:
            print(f"Warning: Could not retrieve index mapping: {e}")

    print("Index mapping retrieved")

    def _rec_to_actions(dfs):
        """Convert DataFrame records to Elasticsearch bulk actions with comprehensive flattening"""
        # Date fields that should be formatted as yyyy-MM-dd
        date_fields = ['admissionDate', 'dateOfService', 'dischargeDate', 'serviceDate', 'created_at', 'updated_at']

        # Datetime fields that should be formatted as yyyy-MM-dd HH:mm:ss
        datetime_fields = ['ingestionDateTime', 'processedDateTime', 'submitDateTime', 'created_at', 'updated_at']

        # Text fields that should remain as-is (issues tracking)
        text_fields = ['processingIssues', 'submittingIssues']

        # JSON object fields that should be preserved as-is
        json_object_fields = ['processed_json']

        for record in dfs.to_dict(orient="records"):
            record.update({'sqmlcomments': ''})
            record.update({'sqml_annotations': ''})

            # Add timestamp tracking for document operations
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # For upsert operations, we'll add last_modified_at and preserve created_at if it exists
            record['last_modified_at'] = current_time
            
            # Only set created_at if it doesn't exist (will be preserved in upsert)
            if 'created_at' not in record or not record.get('created_at'):
                record['created_at'] = current_time

            # Apply comprehensive flattening for notes digest indices
            if dataset_id.endswith('_notes_digest'):
                try:
                    flattened_record, flattening_issues = flatten_all_nested_objects(record)
                    record = flattened_record
                    
                    # Add flattening issues to processing issues if any
                    if flattening_issues:
                        existing_issues = record.get('processingIssues', '')
                        if existing_issues:
                            record['processingIssues'] = existing_issues + '; ' + '; '.join(flattening_issues)
                        else:
                            record['processingIssues'] = '; '.join(flattening_issues)
                        print(f"   Applied flattening with {len(flattening_issues)} issues")
                    else:
                        print("   Applied flattening successfully")
                        
                except Exception as e:
                    error_msg = f"Flattening failed: {str(e)}"
                    print(f"   Warning: {error_msg}")
                    existing_issues = record.get('processingIssues', '')
                    if existing_issues:
                        record['processingIssues'] = existing_issues + '; ' + error_msg
                    else:
                        record['processingIssues'] = error_msg

            # Extract custom _id if present (for composite key support)
            custom_id = None
            composite_key_value = None
            
            if '_id' in record:
                custom_id = record.pop('_id')
                print(f"   Using custom _id for upsert: {custom_id}")
            
            if 'composite_key' in record:
                composite_key_value = record['composite_key']
                print(f"   composite_key field for upsert: {composite_key_value}")

            for key, value in record.items():
                # Keep JSON object fields as-is (processed_json)
                if key in json_object_fields:
                    # Ensure it's a dict, empty dict if None
                    if value is None or (isinstance(value, float) and np.isnan(value)):
                        record[key] = {}
                    elif isinstance(value, dict):
                        record[key] = value  # Keep as dict
                    else:
                        record[key] = {}

                # Format date fields to yyyy-MM-dd
                elif key in date_fields:
                    formatted_date = format_date_for_es(value)
                    record[key] = formatted_date

                # Format datetime fields to yyyy-MM-dd HH:mm:ss
                elif key in datetime_fields:
                    formatted_datetime = format_datetime_for_es(value)
                    record[key] = formatted_datetime

                # Keep text fields as-is (processingIssues, submittingIssues)
                elif key in text_fields:
                    # Ensure it's a string, empty string if None
                    if value is None or (isinstance(value, float) and np.isnan(value)):
                        record[key] = ''
                    else:
                        record[key] = str(value)

                # Handle NaN values for other fields
                elif isinstance(value, float) and np.isnan(value):
                    record[key] = None
                else:
                    try:
                        if isinstance(value, str) and (value.lower() in ["nan", "none", ""]):
                            record[key] = None
                    except:
                        pass

            # Build the bulk action document using upsert to preserve existing data
            if custom_id:
                yield {
                    "_id": custom_id, 
                    "_op_type": "update", 
                    "_index": dataset_id, 
                    "doc": json.loads(json.dumps(record, cls=NpEncoder)),
                    "doc_as_upsert": True,
                    "retry_on_conflict": 3
                }
            elif composite_key_value:
                yield {
                    "_id": composite_key_value, 
                    "_op_type": "update", 
                    "_index": dataset_id, 
                    "doc": json.loads(json.dumps(record, cls=NpEncoder)),
                    "doc_as_upsert": True,
                    "retry_on_conflict": 3
                }
            else:
                # For documents without explicit ID, still use index operation
                yield {"_op_type": "index", "_index": dataset_id, "_source": json.dumps(record, cls=NpEncoder)}

    def send_to_elasticsearch_parallel(dfs):
        """Send data to Elasticsearch using parallel bulk loading"""
        try:
            deque(parallel_bulk(Parallel_ES_client, _rec_to_actions(dfs), chunk_size=500), maxlen=0)
        except BulkIndexError as e:
            print(f"{len(e.errors)} document(s) failed to index.")
            print(e.errors)
            
    print("11- {}".format(datetime.now()))
    send_to_elasticsearch_parallel(newdf)
    print("12- {}".format(datetime.now()))



# es_fetcher
import requests
import urllib3
from datetime import datetime
from medical_notes.config.config import ES_URL, ES_HEADERS

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



def get_previous_visits_by_mrn(index_name, mrn, current_service_date, n, fields=None, current_note_id=None):
    """
    Fetch N previous visits for a patient by MRN, sorted by dateOfService descending.
    Includes same-day visits but excludes the current noteId.
    
    UPDATED: Now filters by noteId < current_note_id to handle reprocessing scenarios.
    
    Args:
        index_name (str): Elasticsearch index name (typically "tiamd_processed_notes")
        mrn (str): Patient MRN (will be cleaned and searched in multiple field variations)
        current_service_date (str): Current visit's service date to include same-day (format: YYYY-MM-DD or MM/DD/YYYY or MM-DD-YYYY)
        n (int): Number of previous visits to fetch
        fields (list, optional): List of fields to retrieve (default: dateOfService, notesProcessedText, patientmrn)
        current_note_id (str, optional): Current noteId to exclude from results AND filter noteId < current
    
    Returns:
        list: List of previous visit dictionaries, sorted by dateOfService (most recent first), then noteId DESC
        
    Example:
        Patient MRN 49398 has noteIds [1, 2, 3, 4]
        When processing noteId=3:
        - Returns: noteIds 1, 2 only
        - Excludes: noteId 4 (because 4 > 3)
        - Excludes: noteId 3 (current note)
    """
    if not fields:
        fields = ["dateOfService", "notesProcessedText", "patientmrn", "noteId"]
    
    # Clean the MRN - remove whitespace, convert to string
    mrn_cleaned = str(mrn).strip()
    
    print(f"\n[DEBUG] Searching for previous visits:")
    print(f"  - MRN (cleaned): '{mrn_cleaned}'")
    print(f"  - Current Service Date: '{current_service_date}'")
    print(f"  - Current NoteId: '{current_note_id}'")
    print(f"  - Requesting: {n} previous visits")
    
    # Build MRN matching query - try multiple field variations and matching strategies
    mrn_should_clauses = [
        # Exact term matches
        {"term": {"patientmrn.keyword": mrn_cleaned}},
        {"term": {"patientmrn": mrn_cleaned}},
        {"term": {"patientMRN.keyword": mrn_cleaned}},
        {"term": {"patientMRN": mrn_cleaned}},
        {"term": {"patient_mrn.keyword": mrn_cleaned}},
        {"term": {"patient_mrn": mrn_cleaned}},
        
        # Match queries (more flexible)
        {"match": {"patientmrn": mrn_cleaned}},
        {"match": {"patientMRN": mrn_cleaned}},
        {"match": {"patient_mrn": mrn_cleaned}},
        
        # Match phrase for exact matching with flexibility
        {"match_phrase": {"patientmrn": mrn_cleaned}},
        {"match_phrase": {"patientMRN": mrn_cleaned}},
    ]
    
    must_clauses = [
        {
            "bool": {
                "should": mrn_should_clauses,
                "minimum_should_match": 1
            }
        }
    ]
    
    # UPDATED: Add must_not clause for current noteId
    must_not_clauses = []
    if current_note_id:
        must_not_clauses.append({"term": {"noteId": str(current_note_id)}})
        print(f"  - Excluding current noteId: {current_note_id}")
    
    # Date filter with same-day inclusion
    # UPDATED: Now handles timestamps in dateOfService (e.g., "6/28/2025 9:27 AM")
    safe_service_date = (current_service_date or "").strip()
    if safe_service_date:
        # Try to normalize the date format - extract date part even if timestamp is present
        normalized_date = None
        
        # First, try to parse with dateutil parser (handles timestamps automatically)
        try:
            from dateutil import parser as date_parser
            parsed = date_parser.parse(safe_service_date)
            # Extract just the date part (YYYY-MM-DD) for comparison
            normalized_date = parsed.strftime("%Y-%m-%d")
            print(f"  - Parsed date with timestamp support: {safe_service_date} -> {normalized_date}")
        except:
            # Fallback to manual parsing if dateutil fails
            # Try parsing common date formats (without timestamp)
            date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%d/%m/%Y", "%d-%m-%Y"]
            for fmt in date_formats:
                try:
                    # Extract just the date part if timestamp is present
                    date_part = safe_service_date.split()[0] if ' ' in safe_service_date else safe_service_date
                    parsed = datetime.strptime(date_part, fmt)
                    normalized_date = parsed.strftime("%Y-%m-%d")
                    print(f"  - Extracted date part: {date_part} -> {normalized_date}")
                    break
                except:
                    continue
        
        if normalized_date:
            print(f"  - Normalized date filter: <= {normalized_date}")
            # Use dateOfServiceEpoch if available for better sorting, otherwise use dateOfService
            # For now, use dateOfService with normalized date
            must_clauses.append({"range": {"dateOfService": {"lte": normalized_date}}})
        else:
            print(f"  - Warning: Could not parse date '{safe_service_date}', using original for filter")
            # Extract date part manually if possible
            date_part = safe_service_date.split()[0] if ' ' in safe_service_date else safe_service_date
            must_clauses.append({"range": {"dateOfService": {"lte": date_part}}})
    else:
        print("  - No date filter applied (current_service_date is empty)")
    
    # NEW: Add noteId < current_note_id filter
    if current_note_id:
        try:
            current_note_id_int = int(current_note_id)
            must_clauses.append({"range": {"noteId": {"lt": current_note_id_int}}})
            print(f"  - NoteId filter: < {current_note_id_int} (handles reprocessing)")
        except (ValueError, TypeError):
            print(f"  - Warning: Could not parse current_note_id '{current_note_id}' as integer, skipping noteId filter")
    
    # Build the full query with must_not and improved sorting
    query = {
        "size": max(int(n), 1),
        "_source": fields,
        "query": {
            "bool": {
                "must": must_clauses,
                "must_not": must_not_clauses,
                # Also ensure notesProcessedText exists and is not empty
                "filter": [
                    {"exists": {"field": "notesProcessedText"}},
                    {"bool": {"must_not": {"term": {"notesProcessedText.keyword": ""}}}}
                ]
            }
        },
        "sort": [
            # UPDATED: Use dateOfServiceEpoch for proper timestamp-aware sorting if available
            # Fallback to dateOfService if epoch not available
            {"dateOfServiceEpoch": {"order": "desc", "missing": "_last"}},
            {"dateOfService": {"order": "desc"}},
            {"noteId": {"order": "desc"}}
        ]
    }
    
    print(f"\n[DEBUG] Elasticsearch Query:")
    print(f"{query}")
    
    try:
        response = requests.post(
            f"{ES_URL}/{index_name}/_search",
            headers=ES_HEADERS,
            json=query,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        
        response_data = response.json()
        hits = response_data.get("hits", {}).get("hits", [])
        total_hits = response_data.get("hits", {}).get("total", {})
        
        print(f"\n[DEBUG] ES Response:")
        print(f"  - Total matches: {total_hits}")
        print(f"  - Returned hits: {len(hits)}")
        
        previous_visits = []
        for hit in hits:
            source = hit["_source"]
            # Ensure we have the required fields
            if source.get('dateOfService') and source.get('notesProcessedText'):
                previous_visits.append(source)
        
        print(f"\n[RESULT] Found {len(previous_visits)} valid previous visit(s) for MRN '{mrn_cleaned}'")
        for i, visit in enumerate(previous_visits, 1):
            visit_date = visit.get('dateOfService', 'Unknown')
            visit_note_id = visit.get('noteId', 'Unknown')
            visit_mrn = visit.get('patientmrn', 'N/A')
            text_length = len(visit.get('notesProcessedText', ''))
            print(f"  {i}. NoteId: {visit_note_id} | Date: {visit_date} | MRN: {visit_mrn} | Text: {text_length} chars")
        
        return previous_visits
        
    except requests.HTTPError as e:
        err_text = getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
        print(f"\n[ERROR] HTTP Error fetching previous visits:")
        print(f"  - MRN: {mrn_cleaned}")
        print(f"  - Status: {e}")
        print(f"  - Response: {err_text[:500]}")
        return []
    except Exception as e:
        print(f"\n[ERROR] Exception fetching previous visits:")
        print(f"  - MRN: {mrn_cleaned}")
        print(f"  - Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_notes_by_status(index_name, status, fields=None):
    """Fetch notes from Elasticsearch by status."""
    query = {
        "query": {
            "term": {
                "status": status
            }
        }
    }
    
    if fields:
        query["_source"] = fields
    
    try:
        response = requests.post(
            f"{ES_URL}/{index_name}/_search",
            headers=ES_HEADERS,
            json=query,
            verify=False
        )
        response.raise_for_status()
        
        hits = response.json().get("hits", {}).get("hits", [])
        return [hit["_source"] for hit in hits]
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []


def get_notes_by_mrn(index_name, mrn, fields=None):
    """Fetch notes from Elasticsearch by MRN."""
    query = {
        "query": {
            "term": {
                "patientmrn": mrn
            }
        }
    }
    
    if fields:
        query["_source"] = fields
    
    try:
        response = requests.post(
            f"{ES_URL}/{index_name}/_search",
            headers=ES_HEADERS,
            json=query,
            verify=False
        )
        response.raise_for_status()
        
        hits = response.json().get("hits", {}).get("hits", [])
        return [hit["_source"] for hit in hits]
        
    except requests.HTTPError as e:
        err_text = getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
        print(f"Error fetching data (status): {e} | Response: {err_text[:500]}")
        return []
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []


def get_notes_by_noteid(index_name, noteid, fields=None):
    """Fetch notes from Elasticsearch by Note ID (numeric only)."""
    # Validate that noteId is numeric
    if not str(noteid).isdigit():
        print(f"Error: noteId must be numeric, got: {noteid}")
        return []
    
    query = {
        "query": {
            "term": {
                "noteId": noteid
            }
        }
    }
    
    if fields:
        query["_source"] = fields
    
    try:
        response = requests.post(
            f"{ES_URL}/{index_name}/_search",
            headers=ES_HEADERS,
            json=query,
            verify=False
        )
        response.raise_for_status()
        
        hits = response.json().get("hits", {}).get("hits", [])
        return [hit["_source"] for hit in hits]
        
    except requests.HTTPError as e:
        err_text = getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
        print(f"Error fetching data for noteId {noteid}: {e} | Response: {err_text[:500]}")
        return []
    except Exception as e:
        print(f"Error fetching data for noteId {noteid}: {e}")
        return []


def check_noteid_exists(index_name, noteid):
    """Check if a noteId exists in the index."""
    if not str(noteid).isdigit():
        print(f"Error: noteId must be numeric, got: {noteid}")
        return False, None
    
    notes = get_notes_by_noteid(index_name, noteid, fields=["noteId", "status"])
    
    if notes and len(notes) > 0:
        return True, notes[0].get('status', None)
    
    return False, None


# Alias for backward compatibility and clearer naming
def get_previous_visits_by_mrn_and_noteid(index_name, mrn, current_service_date, n, fields=None, current_note_id=None):
    """
    Alias for get_previous_visits_by_mrn with noteId filtering.
    Fetches N previous visits for a patient by MRN, sorted by dateOfService descending.
    Now handles timestamps in dateOfService (e.g., "6/28/2025 9:27 AM").
    
    Args:
        index_name (str): Elasticsearch index name
        mrn (str): Patient MRN
        current_service_date (str): Current visit's service date (can include timestamp like "6/28/2025 9:27 AM")
        n (int): Number of previous visits to fetch
        fields (list, optional): List of fields to retrieve
        current_note_id (str, optional): Current noteId to exclude and filter by
    
    Returns:
        list: List of previous visit dictionaries, sorted by dateOfService (most recent first)
    """
    return get_previous_visits_by_mrn(
        index_name=index_name,
        mrn=mrn,
        current_service_date=current_service_date,
        n=n,
        fields=fields,
        current_note_id=current_note_id
    )



# es_to_api
"""
Enhanced ES to API Module with Failure Notification Support
Fetches from Elasticsearch and sends to external API
Includes success and failure notification endpoints
"""

import requests
import json
from datetime import datetime
from typing import Optional, Dict
from medical_notes.config.config import ES_INDEX_PROCESSED_NOTES, ES_URL, ES_HEADERS, API_BASE_URL, API_ENDPOINT, API_HEADERS


def push_note_to_api(note_id, composite_key, es_credentials=None):
    """
    Fetch note data from Elasticsearch using both noteId and composite_key and push to API endpoint
    
    Args:
        note_id: The noteId of the note to process
        composite_key: The composite key of the note to process
        es_credentials: Optional credentials for ES
    
    Returns:
        tuple: (success: bool, submitting_issues: str)
               success: True if successful, False otherwise
               submitting_issues: Empty string if success, error details if failed
    """
    try:
        # Query Elasticsearch using both noteId and composite_key for accuracy
        cc_obj = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"_id": composite_key}},
                        {"term": {"noteId": note_id}}
                    ]
                }
            }
        }
        
        cc_request_entity = json.dumps(cc_obj)
        
        print(f"Fetching note from Elasticsearch...")
        print(f"  - noteId: {note_id}")
        print(f"  - composite_key: {composite_key}")
        
        cc_response = requests.post(
            f"{ES_URL}/{ES_INDEX_PROCESSED_NOTES}/_search?size=1",
            data=cc_request_entity,
            headers=ES_HEADERS,
            verify=True
        )
        
        if cc_response.status_code != 200:
            error_msg = f"Elasticsearch fetch failed with status {cc_response.status_code}: {cc_response.text}"
            print(f"Error fetching from ES: {cc_response.status_code}")
            print(f"Response: {cc_response.text}")
            return False, error_msg
        
        # Parse response
        cc_response_array = cc_response.json().get("hits", {}).get("hits", [])
        
        if not cc_response_array:
            error_msg = f"No note found with noteId: {note_id} and composite_key: {composite_key}"
            print(error_msg)
            return False, error_msg
        
        response_data_dc = cc_response_array[0]
        
        print(f"✓ Note found in Elasticsearch")
        
        payload = {}
        date_formatter = "%Y-%m-%d"
        date_time_formatter = "%Y-%m-%d %H:%M:%S"
        
        # Extract source data
        source = response_data_dc.get("_source", {})
        
        # REQUIRED FIELDS - Add them first
        payload["patientName"] = source.get("patientName")
        payload["patientmrn"] = source.get("patientmrn")
        payload["noteId"] = source.get("noteId")
        payload["noteType"] = source.get("noteType")
        
        print(f"\nRequired fields:")
        print(f"  - patientName: {payload['patientName']}")
        print(f"  - patientmrn: {payload['patientmrn']}")
        print(f"  - noteId: {payload['noteId']}")
        print(f"  - noteType: {payload['noteType']}")
        
        # Parse and add required date fields (dateOfService is always required)
        date_of_service = source.get("dateOfService")
        if date_of_service:
            try:
                dos_date = datetime.strptime(date_of_service, date_formatter).date()
                payload["dateOfService"] = dos_date.isoformat()
                print(f"  - dateOfService: {dos_date.isoformat()} ✓")
            except (ValueError, TypeError) as e:
                error_msg = f"Error parsing dateOfService: {e}"
                print(error_msg)
                return False, error_msg
        else:
            error_msg = "Error: dateOfService is required but missing"
            print(error_msg)
            return False, error_msg
        
        print(f"\nConditional date fields:")
        
        # CONDITIONAL: Only add admissionDate if it's not null/empty
        admission_date = source.get("admissionDate")
        if admission_date:
            try:
                adm_date = datetime.strptime(admission_date, date_formatter).date()
                payload["admissionDate"] = adm_date.isoformat()
                print(f"  - admissionDate: {adm_date.isoformat()} ✓")
            except (ValueError, TypeError) as e:
                print(f"  - admissionDate: Could not parse, skipping ⚠️")
        else:
            print(f"  - admissionDate: null/empty, skipping")
        
        # CONDITIONAL: Only add dischargeDate if it's not null/empty
        discharge_date = source.get("dischargeDate")
        if discharge_date:
            try:
                dis_date = datetime.strptime(discharge_date, date_formatter).date()
                payload["dischargeDate"] = dis_date.isoformat()
                print(f"  - dischargeDate: {dis_date.isoformat()} ✓")
            except (ValueError, TypeError) as e:
                print(f"  - dischargeDate: Could not parse, skipping ⚠️")
        else:
            print(f"  - dischargeDate: null/empty, skipping")
        
        # CONDITIONAL: Only add ingestionDateTime if it's not null/empty
        ingestion_date_str = source.get("ingestionDateTime")
        if ingestion_date_str:
            try:
                ingestion_datetime = datetime.strptime(ingestion_date_str, date_time_formatter)
                payload["ingestionDateTime"] = ingestion_datetime.strftime(date_time_formatter)
                print(f"  - ingestionDateTime: {payload['ingestionDateTime']} ✓")
            except (ValueError, TypeError) as e:
                print(f"  - ingestionDateTime: Could not parse, skipping ⚠️")
        else:
            print(f"  - ingestionDateTime: null/empty, skipping")
        
        print(f"\nText and JSON fields:")

        # Send actual processed data for plain text fields, but always "null" for structured text fields
        payload["notesProcessedText"] = "null"
        payload["soapnotesText"] = "null"
        payload["notesProcessedJson"] = source.get("notesProcessedJson") or "null"
        payload["soapnotesJson"] = source.get("soapnotesJson") or "null"
        payload["notesProcessedPlainText"] = source.get("notesProcessedPlainText") or "null"
        payload["soapnotesPlainText"] = source.get("soapnotesPlainText") or "null"
        
        print(f"  - notesProcessedText: {len(str(payload['notesProcessedText']))} chars")
        print(f"  - soapnotesText: {len(str(payload['soapnotesText']))} chars")
        print(f"  - notesProcessedJson: {len(str(payload['notesProcessedJson']))} chars")
        print(f"  - soapnotesJson: {len(str(payload['soapnotesJson']))} chars")
        print(f"  - notesProcessedPlainText: {len(str(payload['notesProcessedPlainText']))} chars")
        print(f"  - soapnotesPlainText: {len(str(payload['soapnotesPlainText']))} chars")
        
        # Log if any fields are empty
        empty_fields = []
        for field_name, field_value in [
            ("notesProcessedText", payload["notesProcessedText"]),
            ("soapnotesText", payload["soapnotesText"]),
            ("notesProcessedJson", payload["notesProcessedJson"]),
            ("soapnotesJson", payload["soapnotesJson"]),
            ("notesProcessedPlainText", payload["notesProcessedPlainText"]),
            ("soapnotesPlainText", payload["soapnotesPlainText"])
        ]:
            if not field_value or field_value == "":
                empty_fields.append(field_name)
        
        if empty_fields:
            print(f"  ⚠️ Empty fields: {', '.join(empty_fields)}")
        
        print(f"  - Sending actual processed data to API")
        
        print(f"\n{'='*60}")
        print(f"Payload Summary:")
        print(f"  - Total fields: {len(payload)}")
        print(f"  - Payload size: {len(json.dumps(payload))} bytes")
        print(f"  - Fields: {', '.join(payload.keys())}")
        print(f"{'='*60}\n")
        
        print(f"Pushing data to API endpoint: {API_ENDPOINT}")

        response = requests.post(API_ENDPOINT, json=payload, headers=API_HEADERS)
        
        print(f"API Response Status: {response.status_code}")
        
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Success! API response: {response.text}")
            print(f"Note (noteId: {note_id}, composite_key: {composite_key}) processed successfully!")
            return True, ""  # Success, no submitting issues
        else:
            # Capture API validation errors and response details for submittingIssues
            error_msg = f"API returned status {response.status_code}: {response.text}"
            print(f"❌ Error: {error_msg}")
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg
    except KeyError as e:
        error_msg = f"Missing required field in source data: {e}"
        print(f"❌ {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error processing note: {e}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return False, error_msg


def push_failure_to_api(failure_data: Dict) -> bool:
    """
    Push processing failure notification to external API
    Uses the SAME endpoint as success but includes noteStatus + noteStatusDetails
    Includes patient data fetched from ES clinical_notes

    Args:
        failure_data: Dictionary containing:
            - noteId: The noteId (REQUIRED)
            - patientName: Patient name from ES (patientID field)
            - patientmrn: Patient MRN extracted from rawdata
            - dateOfService: Current processing date
            - noteType: Note type from ES
            - errorMessage: Description of the error
            - failedStage: Stage where processing failed
            - statusCode: HTTP status code (default 500)

    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        note_type = failure_data.get("noteType", "")
        error_message = failure_data.get("errorMessage", "")

        payload = {
            "noteId": failure_data.get("noteId"),
            "patientName": failure_data.get("patientName", ""),
            "patientmrn": failure_data.get("patientmrn", ""),
            "dateOfService": failure_data.get("dateOfService", ""),
            "noteType": note_type,
            "noteStatus": failure_data.get("statusCode", 500),
            "noteStatusDetails": error_message,
            # Send null for structured text fields
            "notesProcessedText": "null",
            "soapnotesText": "null",
            "notesProcessedJson": "null",
            "soapnotesJson": "null",
            # Send error messages in plain text fields
            "notesProcessedPlainText": f"Error: {error_message}",
            "soapnotesPlainText": f"Error: {error_message}",
            "failedStage": failure_data.get("failedStage")
        }

        print(f"\nPushing failure notification to API...")
        print(f"  - noteId: {payload['noteId']}")
        print(f"  - patientName: {payload['patientName']}")
        print(f"  - patientmrn: {payload['patientmrn']}")
        print(f"  - dateOfService: {payload['dateOfService']}")
        print(f"  - noteType: {payload['noteType']}")
        print(f"  - failedStage: {payload['failedStage']}")
        print(f"  - noteStatus: {payload['noteStatus']}")
        print(f"  - noteStatusDetails: {payload['noteStatusDetails']}")
        print(f"  - notesProcessedText: {payload['notesProcessedText']}")
        print(f"  - soapnotesText: {payload['soapnotesText']}")
        print(f"  - notesProcessedJson: {payload['notesProcessedJson']}")
        print(f"  - soapnotesJson: {payload['soapnotesJson']}")
        print(f"  - notesProcessedPlainText: {payload['notesProcessedPlainText']}")
        print(f"  - soapnotesPlainText: {payload['soapnotesPlainText']}")
        print(f"\nError Payload:\n{json.dumps(payload, indent=2)}")

        # Make API request to the SAME endpoint (savePatientDigestNote)
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=API_HEADERS,
            timeout=30
        )

        # Check response
        if response.status_code in [200, 201]:
            print(f"✓ Successfully pushed failure notification to API")
            return True
        else:
            print(f"✗ API returned status {response.status_code}: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"✗ API failure notification timed out for noteId '{failure_data.get('noteId')}'")
        return False

    except requests.exceptions.RequestException as e:
        print(f"✗ API failure notification request failed: {str(e)}")
        return False

    except Exception as e:
        print(f"✗ Unexpected error pushing failure notification: {str(e)}")
        return False


def send_processing_error(error_payload: Dict) -> bool:
    """
    Send processing error notification after all retries exhausted
    Uses the SAME endpoint as success but includes noteStatus + noteStatusDetails
    Includes patient data fetched from ES clinical_notes

    Args:
        error_payload: Dictionary containing:
            - noteId: The noteId (REQUIRED)
            - patientName: Patient name from ES (patientID field)
            - patientmrn: Patient MRN extracted from rawdata
            - dateOfService: Current processing date
            - noteType: Note type from ES
            - locationname: Location name from ES
            - statusCode: HTTP status code (404, 409, 422, 403, 500)
            - errorMessage: Description of the error

    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    try:
        error_type = classify_error_by_status_code(error_payload.get("statusCode", 500))
        note_type = error_payload.get("noteType", "")
        error_message = error_payload.get("errorMessage", "")

        payload = {
            "noteId": error_payload.get("noteId"),
            "patientName": error_payload.get("patientName", ""),
            "patientmrn": error_payload.get("patientmrn", ""),
            "dateOfService": error_payload.get("dateOfService", ""),
            "noteType": note_type,
            "noteStatus": error_payload.get("statusCode", 500),
            "noteStatusDetails": error_message,
            # Send null for structured text fields
            "notesProcessedText": "null",
            "soapnotesText": "null",
            "notesProcessedJson": "null",
            "soapnotesJson": "null",
            # Send error messages in plain text fields
            "notesProcessedPlainText": f"Error: {error_message}",
            "soapnotesPlainText": f"Error: {error_message}"
        }

        print(f"\nSending error notification to API...")
        print(f"  - noteId: {payload['noteId']}")
        print(f"  - patientName: {payload['patientName']}")
        print(f"  - patientmrn: {payload['patientmrn']}")
        print(f"  - dateOfService: {payload['dateOfService']}")
        print(f"  - noteType: {payload['noteType']}")
        print(f"  - noteStatus: {payload['noteStatus']}")
        print(f"  - noteStatusDetails: {payload['noteStatusDetails']}")
        print(f"  - notesProcessedText: {payload['notesProcessedText']}")
        print(f"  - soapnotesText: {payload['soapnotesText']}")
        print(f"  - notesProcessedJson: {payload['notesProcessedJson']}")
        print(f"  - soapnotesJson: {payload['soapnotesJson']}")
        print(f"  - notesProcessedPlainText: {payload['notesProcessedPlainText']}")
        print(f"  - soapnotesPlainText: {payload['soapnotesPlainText']}")
        print(f"  - errorType: {error_type}")
        print(f"\nError Payload:\n{json.dumps(payload, indent=2)}")

        # Make API request to the SAME endpoint (savePatientDigestNote)
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=API_HEADERS,
            timeout=30
        )

        # Check response
        if response.status_code in [200, 201]:
            print(f"✓ Successfully sent error notification to API")
            return True
        else:
            print(f"✗ API returned status {response.status_code}: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"✗ API error notification timed out for noteId '{error_payload.get('noteId')}'")
        return False

    except requests.exceptions.RequestException as e:
        print(f"✗ API error notification request failed: {str(e)}")
        return False

    except Exception as e:
        print(f"✗ Unexpected error sending error notification: {str(e)}")
        return False


def determine_if_retryable(failed_stage: str) -> bool:
    """
    Determine if a failure is retryable based on the stage where it failed
    
    Args:
        failed_stage: The stage where processing failed
    
    Returns:
        bool: True if the failure is retryable, False otherwise
    """
    # Non-retryable stages (data issues)
    non_retryable_stages = [
        "validation",      # Note doesn't exist or already processed
        "fetch",          # Missing rawdata
        "extraction"      # Cannot extract note type
    ]
    
    # Retryable stages (temporary issues, API problems, etc.)
    retryable_stages = [
        "data_extraction",    # LLM might succeed on retry
        "soap_generation",    # LLM might succeed on retry
        "push_to_index",      # ES might be temporarily down
        "status_update",      # ES update might succeed on retry
        "api_push",          # External API might be temporarily down
        "update_mrn",        # ES update might succeed on retry
        "historical_context", # ES query might succeed on retry
        "combine_context",   # Processing might succeed on retry
        "submit_tracking",   # ES update might succeed on retry
        "final_status_update" # ES update might succeed on retry
    ]
    
    if failed_stage in non_retryable_stages:
        return False
    elif failed_stage in retryable_stages:
        return True
    else:
        # Unknown stage - default to retryable
        return True


def classify_error_by_status_code(status_code: int) -> str:
    """
    Classify error type based on status code
    
    Args:
        status_code: HTTP status code
    
    Returns:
        str: Error classification
    """
    error_types = {
        404: "NOT_FOUND",           # Note doesn't exist in index
        409: "ALREADY_PROCESSED",   # Note already processed
        422: "DATA_INVALID",        # Cannot extract required data
        403: "API_REJECTED",        # External API rejected request
        500: "PROCESSING_ERROR"     # Internal processing/ES/LLM errors
    }
    
    return error_types.get(status_code, "UNKNOWN_ERROR")


def get_api_health() -> Dict:
    """
    Check health of external API
    
    Returns:
        dict: Health status information
    """
    try:
        health_url = f"{API_BASE_URL}/health"
        response = requests.get(health_url, headers=API_HEADERS, timeout=10)
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "api_url": API_BASE_URL,
                "response": response.json()
            }
        else:
            return {
                "status": "unhealthy",
                "api_url": API_BASE_URL,
                "status_code": response.status_code
            }
    
    except Exception as e:
        return {
            "status": "unreachable",
            "api_url": API_BASE_URL,
            "error": str(e)
        }



# es_updater
"""
Elasticsearch Updater - Production Ready
Supports updating with noteId and composite_key
Includes submitDateTime and submittingIssues tracking
"""

import requests
import urllib3
from medical_notes.config.config import ES_INDEX_PROCESSED_NOTES, ES_URL, ES_HEADERS

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def update_by_noteid_and_composite_key(index_name, note_id, composite_key, **fields):
    """
    Update fields for a document using BOTH noteId and composite_key.
    This ensures we update only the specific document that matches both conditions.
    
    Args:
        index_name (str): Elasticsearch index name
        note_id (str): The noteId to match
        composite_key (str): The composite_key (_id) to match
        **fields: Any fields to update (e.g., submitDateTime="2025-10-21 10:30:00")
    
    Returns:
        dict: Response from Elasticsearch with 'updated' count, None if error
    """
    if not fields:
        print("No fields to update")
        return None
    
    # Build update script
    updates = []
    params = {}
    
    for field, value in fields.items():
        if value is not None:  # Allow empty strings but not None
            updates.append(f"ctx._source.{field} = params.{field}")
            params[field] = value
    
    if not updates:
        print("No valid fields to update")
        return None
    
    payload = {
        "script": {
            "source": "; ".join(updates),
            "params": params
        },
        "query": {
            "bool": {
                "must": [
                    {"term": {"_id": composite_key}},
                    {"term": {"noteId": note_id}}
                ]
            }
        }
    }
    
    try:
        response = requests.post(
            f"{ES_URL}/{index_name}/_update_by_query",
            headers=ES_HEADERS,
            json=payload,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        updated = result.get("updated", 0)
        
        if updated > 0:
            print(f"✅ Updated {updated} document(s) with noteId: {note_id} and composite_key: {composite_key} in index: {index_name}")
        else:
            print(f"⚠️  No documents found matching noteId: {note_id} and composite_key: {composite_key} in index: {index_name}")
        
        return result
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout updating document in {index_name}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error updating document in {index_name}: {e}")
        print(f"   Response: {response.text if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"❌ Error updating document in {index_name}: {e}")
        return None


def update_by_noteid(index_name, note_id, **fields):
    """
    Update any fields for a document by noteId.
    WARNING: This will update ALL documents with the same noteId.
    Use update_by_noteid_and_composite_key() for precise updates.
    
    Args:
        index_name (str): Elasticsearch index name
        note_id (str): The noteId to update
        **fields: Any fields to update (e.g., status="processed", mrn="MRN001")
    
    Returns:
        dict: Response from Elasticsearch, None if error
    """
    if not fields:
        print("No fields to update")
        return None
    
    # Build update script
    updates = []
    params = {}
    
    for field, value in fields.items():
        if value is not None and str(value).strip():  # Skip None and empty values
            updates.append(f"ctx._source.{field} = params.{field}")
            params[field] = value
    
    if not updates:
        print("No valid fields to update")
        return None
    
    payload = {
        "query": {
            "term": {"noteId": note_id}
        },
        "script": {
            "source": "; ".join(updates),
            "params": params
        }
    }
    
    try:
        response = requests.post(
            f"{ES_URL}/{index_name}/_update_by_query",
            headers=ES_HEADERS,
            json=payload,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        updated = result.get("updated", 0)
        
        if updated > 0:
            print(f"✅ Updated {updated} document(s) with noteId: {note_id} in index: {index_name}")
        else:
            print(f"⚠️  No documents updated for noteId: {note_id} in index: {index_name}")
        
        return result
        
    except requests.exceptions.Timeout:
        print(f"❌ Timeout updating noteId {note_id} in {index_name}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error updating noteId {note_id} in {index_name}: {e}")
        print(f"   Response: {response.text if 'response' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"❌ Error updating noteId {note_id} in {index_name}: {e}")
        return None


def update_by_composite_key(index_name, composite_key, **fields):
    """
    Update any fields for a document by composite_key.
    Used for tiamd_prod_processed_notes where composite_key is the document ID.
    
    Args:
        index_name (str): Elasticsearch index name
        composite_key (str): The composite_key to update (document _id)
        **fields: Any fields to update
    
    Returns:
        dict: Response from Elasticsearch, None if error
    """
    if not fields:
        print("No fields to update")
        return None
    
    # Build update script
    updates = []
    params = {}
    
    for field, value in fields.items():
        if value is not None:  # Allow empty strings but not None
            updates.append(f"ctx._source.{field} = params.{field}")
            params[field] = value
    
    if not updates:
        print("No valid fields to update")
        return None
    
    payload = {
        "script": {
            "source": "; ".join(updates),
            "params": params
        }
    }
    
    try:
        # Update by document ID (composite_key is the _id)
        response = requests.post(
            f"{ES_URL}/{index_name}/_update/{composite_key}",
            headers=ES_HEADERS,
            json=payload,
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("result") in ["updated", "noop"]:
            print(f"✅ Updated document with composite_key: {composite_key} in index: {index_name}")
        else:
            print(f"⚠️  Update result: {result.get('result')} for composite_key: {composite_key}")
        
        return result
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"❌ Document not found with composite_key: {composite_key} in {index_name}")
        else:
            print(f"❌ HTTP Error updating composite_key {composite_key} in {index_name}: {e}")
            print(f"   Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
        return None
    except requests.exceptions.Timeout:
        print(f"❌ Timeout updating composite_key {composite_key} in {index_name}")
        return None
    except Exception as e:
        print(f"❌ Error updating composite_key {composite_key} in {index_name}: {e}")
        return None


def update_from_dataframe(index_name, notesdf, fields_to_update):
    """
    Update selected fields from DataFrame using noteId.
    
    Args:
        index_name (str): Elasticsearch index name
        notesdf (DataFrame): DataFrame with noteId and fields to update
        fields_to_update (list): List of column names to update (e.g., ['mrn', 'status'])
    
    Returns:
        dict: Summary of updates with detailed results
    """
    results = {
        "successful": 0, 
        "failed": 0,
        "details": []
    }
    
    # Check if noteId exists
    if "noteId" not in notesdf.columns:
        print("❌ Error: noteId column not found in DataFrame")
        return results
    
    # Check if requested fields exist
    missing_fields = [f for f in fields_to_update if f not in notesdf.columns]
    if missing_fields:
        print(f"⚠️  Warning: These fields not found in DataFrame: {missing_fields}")
    
    print(f"\n📄 Updating {len(notesdf)} record(s) in index: {index_name}")
    print(f"   Fields to update: {fields_to_update}")
    
    for idx, row in notesdf.iterrows():
        note_id = row.get("noteId")
        
        if not note_id:
            print(f"⚠️  Skipping row {idx} with missing noteId")
            results["failed"] += 1
            results["details"].append({
                "row": idx,
                "noteId": None,
                "status": "failed",
                "reason": "Missing noteId"
            })
            continue
        
        # Get only the specified fields from this row
        update_fields = {}
        for field in fields_to_update:
            if field in row:
                value = row[field]
                # Handle pandas NaN/None values
                if value is not None and str(value) != 'nan':
                    update_fields[field] = value
        
        if not update_fields:
            print(f"⚠️  No valid fields to update for noteId: {note_id}")
            results["failed"] += 1
            results["details"].append({
                "row": idx,
                "noteId": note_id,
                "status": "failed",
                "reason": "No valid fields"
            })
            continue
        
        result = update_by_noteid(index_name, note_id, **update_fields)
        
        if result and result.get("updated", 0) > 0:
            results["successful"] += 1
            results["details"].append({
                "row": idx,
                "noteId": note_id,
                "status": "success",
                "updated_count": result.get("updated", 0)
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "row": idx,
                "noteId": note_id,
                "status": "failed",
                "reason": "Update returned 0 documents"
            })
    
    print(f"\n{'='*60}")
    print(f"Update Summary for {index_name}:")
    print(f"  ✅ Successful: {results['successful']}")
    print(f"  ❌ Failed: {results['failed']}")
    print(f"{'='*60}\n")
    
    return results


def parse_datetime_to_epoch(datetime_str):
    """
    Parse datetime string and convert to epoch milliseconds.
    Enhanced to use TimestampManager for consistent timestamp handling.
    
    Args:
        datetime_str: Datetime string in various formats
    
    Returns:
        int or None: Epoch milliseconds or None if parsing fails
    """
    if not datetime_str or not str(datetime_str).strip():
        return None
        
    try:
        # Use enhanced TimestampManager for consistent parsing
        from medical_notes.utils.timestamp_utils import TimestampManager
        return TimestampManager.parse_datetime_to_epoch_ms(str(datetime_str))
    except:
        # Fallback to original implementation for backward compatibility
        try:
            from dateutil import parser as date_parser
            from datetime import datetime as dt
            dt_obj = date_parser.parse(str(datetime_str))
            epoch_ms = int(dt_obj.timestamp() * 1000)
            return epoch_ms
        except:
            return None


def update_status_in_processed_notes(note_id, new_status, submit_datetime=None, submitting_issues=''):
    """
    Update status and optionally submit tracking fields in tiamd_prod_processed_notes.
    WARNING: Updates ALL documents with the same noteId.
    Also updates submitDateEpoch field if submit_datetime is provided.
    
    Args:
        note_id (str): The noteId to update
        new_status (str): New status value (e.g., 'note submitted')
        submit_datetime (str): Timestamp of API submission (optional, format: yyyy-MM-dd HH:mm:ss)
        submitting_issues (str): Issues encountered during submission (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Build fields to update
    update_fields = {
        "notesProcessedStatus": new_status
    }
    
    # Add submit tracking fields if provided
    if submit_datetime:
        update_fields["submitDateTime"] = submit_datetime
        # Calculate and add submitDateEpoch
        submit_epoch = parse_datetime_to_epoch(submit_datetime)
        if submit_epoch is not None:
            update_fields["submitDateEpoch"] = submit_epoch
    
    if submitting_issues is not None:  # Allow empty string
        update_fields["submittingIssues"] = submitting_issues
    
    # Update by noteId (will find the document)
    result = update_by_noteid(ES_INDEX_PROCESSED_NOTES, note_id, **update_fields)
    
    return result is not None and result.get("updated", 0) > 0


def update_submit_tracking(note_id, submit_datetime, submitting_issues=''):
    """
    Update only submit tracking fields in tiamd_prod_processed_notes.
    WARNING: Updates ALL documents with the same noteId.
    Use update_submit_tracking_precise() for single document updates.
    Also updates submitDateEpoch field.
    
    Args:
        note_id (str): The noteId to update
        submit_datetime (str): Timestamp of API submission attempt (format: yyyy-MM-dd HH:mm:ss)
        submitting_issues (str): Issues encountered during submission
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Calculate epoch from submit_datetime
    submit_epoch = parse_datetime_to_epoch(submit_datetime)
    
    update_fields = {
        "submitDateTime": submit_datetime,
        "submittingIssues": submitting_issues
    }
    
    # Add submitDateEpoch if we successfully parsed the datetime
    if submit_epoch is not None:
        update_fields["submitDateEpoch"] = submit_epoch
    
    result = update_by_noteid(ES_INDEX_PROCESSED_NOTES, note_id, **update_fields)
    
    return result is not None and result.get("updated", 0) > 0


def update_submit_tracking_precise(note_id, composite_key, submit_datetime, submitting_issues=''):
    """
    Update submit tracking fields using BOTH noteId and composite_key.
    This ensures only ONE specific document is updated.
    RECOMMENDED for use in app.py after API push.
    Also updates submitDateEpoch field.
    
    Args:
        note_id (str): The noteId to match
        composite_key (str): The composite_key to match
        submit_datetime (str): Timestamp of API submission attempt (format: yyyy-MM-dd HH:mm:ss)
        submitting_issues (str): Issues encountered during submission (empty string if none)
    
    Returns:
        bool: True if exactly 1 document updated, False otherwise
    """
    # Calculate epoch from submit_datetime
    submit_epoch = parse_datetime_to_epoch(submit_datetime)
    
    update_fields = {
        "submitDateTime": submit_datetime,
        "submittingIssues": submitting_issues
    }
    
    # Add submitDateEpoch if we successfully parsed the datetime
    if submit_epoch is not None:
        update_fields["submitDateEpoch"] = submit_epoch
    
    result = update_by_noteid_and_composite_key(
        ES_INDEX_PROCESSED_NOTES,
        note_id,
        composite_key,
        **update_fields
    )
    
    return result is not None and result.get("updated", 0) == 1


def update_status_precise(note_id, composite_key, new_status, submit_datetime=None, submitting_issues=''):
    """
    Update status and optionally submit tracking fields using BOTH noteId and composite_key.
    This ensures only ONE specific document is updated.
    RECOMMENDED for final status updates in app.py.
    Also updates submitDateEpoch field if submit_datetime is provided.
    
    Args:
        note_id (str): The noteId to match
        composite_key (str): The composite_key to match
        new_status (str): New status value (e.g., 'note submitted')
        submit_datetime (str): Timestamp of API submission (optional)
        submitting_issues (str): Issues encountered during submission (optional)
    
    Returns:
        bool: True if exactly 1 document updated, False otherwise
    """
    update_fields = {
        "notesProcessedStatus": new_status
    }
    
    if submit_datetime:
        update_fields["submitDateTime"] = submit_datetime
        # Calculate and add submitDateEpoch
        submit_epoch = parse_datetime_to_epoch(submit_datetime)
        if submit_epoch is not None:
            update_fields["submitDateEpoch"] = submit_epoch
    
    if submitting_issues is not None:
        update_fields["submittingIssues"] = submitting_issues
    
    result = update_by_noteid_and_composite_key(
        ES_INDEX_PROCESSED_NOTES,
        note_id,
        composite_key,
        **update_fields
    )
    
    return result is not None and result.get("updated", 0) == 1


def update_submit_tracking_by_composite_key(composite_key, submit_datetime, submitting_issues=''):
    """
    Update only submit tracking fields in tiamd_prod_processed_notes using composite_key.
    Faster than searching by noteId as it directly updates by document ID.
    Also updates submitDateEpoch field.
    
    Args:
        composite_key (str): The composite_key (document _id)
        submit_datetime (str): Timestamp of API submission attempt (format: yyyy-MM-dd HH:mm:ss)
        submitting_issues (str): Issues encountered during submission
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Calculate epoch from submit_datetime
    submit_epoch = parse_datetime_to_epoch(submit_datetime)
    
    update_fields = {
        "submitDateTime": submit_datetime,
        "submittingIssues": submitting_issues
    }
    
    # Add submitDateEpoch if we successfully parsed the datetime
    if submit_epoch is not None:
        update_fields["submitDateEpoch"] = submit_epoch
    
    result = update_by_composite_key(ES_INDEX_PROCESSED_NOTES, composite_key, **update_fields)
    
    return result is not None and result.get("result") in ["updated", "noop"]


def update_status_by_composite_key(composite_key, new_status, submit_datetime=None, submitting_issues=''):
    """
    Update status and optionally submit tracking fields using composite_key.
    Faster than searching by noteId as it directly updates by document ID.
    Also updates submitDateEpoch field if submit_datetime is provided.
    
    Args:
        composite_key (str): The composite_key (document _id)
        new_status (str): New status value (e.g., 'note submitted')
        submit_datetime (str): Timestamp of API submission (optional)
        submitting_issues (str): Issues encountered during submission (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    update_fields = {
        "notesProcessedStatus": new_status
    }
    
    if submit_datetime:
        update_fields["submitDateTime"] = submit_datetime
        # Calculate and add submitDateEpoch
        submit_epoch = parse_datetime_to_epoch(submit_datetime)
        if submit_epoch is not None:
            update_fields["submitDateEpoch"] = submit_epoch
    
    if submitting_issues is not None:
        update_fields["submittingIssues"] = submitting_issues
    
    result = update_by_composite_key(ES_INDEX_PROCESSED_NOTES, composite_key, **update_fields)
    
    return result is not None and result.get("result") in ["updated", "noop"]


def bulk_update_submit_tracking(updates_df):
    """
    Bulk update submit tracking fields for multiple notes.
    Works with either noteId or composite_key (if present in DataFrame).
    
    Args:
        updates_df (DataFrame): DataFrame with columns: noteId (or composite_key), submitDateTime, submittingIssues
    
    Returns:
        dict: Update results summary
    """
    results = {
        "successful": 0,
        "failed": 0,
        "details": []
    }
    
    # Determine if we're using composite_key or noteId
    use_composite_key = "composite_key" in updates_df.columns
    id_field = "composite_key" if use_composite_key else "noteId"
    
    if id_field not in updates_df.columns:
        print(f"❌ Error: {id_field} column not found in DataFrame")
        return results
    
    print(f"\n📄 Bulk updating submit tracking for {len(updates_df)} record(s)")
    print(f"   Using: {id_field}")
    
    for idx, row in updates_df.iterrows():
        id_value = row.get(id_field)
        submit_datetime = row.get('submitDateTime', '')
        submitting_issues = row.get('submittingIssues', '')
        
        if not id_value:
            print(f"⚠️  Skipping row {idx} with missing {id_field}")
            results["failed"] += 1
            continue
        
        # Choose update method based on ID type
        if use_composite_key:
            success = update_submit_tracking_by_composite_key(
                id_value, submit_datetime, submitting_issues
            )
        else:
            success = update_submit_tracking(
                id_value, submit_datetime, submitting_issues
            )
        
        if success:
            results["successful"] += 1
            results["details"].append({
                "row": idx,
                id_field: id_value,
                "status": "success"
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "row": idx,
                id_field: id_value,
                "status": "failed"
            })
    
    print(f"\n{'='*60}")
    print(f"Bulk Update Summary:")
    print(f"  ✅ Successful: {results['successful']}")
    print(f"  ❌ Failed: {results['failed']}")
    print(f"{'='*60}\n")
    
    return results


# Example usage:
# if __name__ == "__main__":
    # Example 1: Update status in tiamd_prod_clinical_notes by noteId
    # update_by_noteid("tiamd_prod_clinical_notes", "12345", status="processed", noteType="progress_note")
    
    # Example 2: PRECISE update using both noteId and composite_key (RECOMMENDED)
    # success = update_submit_tracking_precise(
    #     note_id="12345",
    #     composite_key="20251021143512345",
    #     submit_datetime="2025-10-21 14:35:22",
    #     submitting_issues=""
    # )
    
    # Example 3: Update final status precisely (RECOMMENDED)
    # success = update_status_precise(
    #     note_id="12345",
    #     composite_key="20251021143512345",
    #     new_status="note submitted",
    #     submit_datetime="2025-10-21 14:35:22",
    #     submitting_issues=""
    # )
    
    # Example 4: Update by composite_key only (faster but no validation)
    # success = update_status_by_composite_key(
    #     "20251017143512345",
    #     "note submitted",
    #     submit_datetime="2025-10-17 14:35:22",
    #     submitting_issues=""
    # )
    
    # pass


def validate_timestamp_fields(update_fields):
    """
    Validate timestamp fields to ensure they contain valid epoch values.
    Enhanced for new timestamp tracking fields.
    
    Args:
        update_fields (dict): Dictionary of fields to update
        
    Returns:
        dict: Validated fields with corrected timestamp values
    """
    try:
        from medical_notes.utils.timestamp_utils import TimestampManager
        
        validated_fields = update_fields.copy()
        timestamp_fields = [
            'ingestionDateTimeAsEpoch', 'submitDateEpoch', 'processedDateTimeEpoch',
            'processedAtEpoch', 'processingTimeStartEpoch', 'processingTimeEndEpoch'
        ]
        
        for field in timestamp_fields:
            if field in validated_fields:
                value = validated_fields[field]
                if value is not None and not TimestampManager.validate_epoch_timestamp(value):
                    print(f"⚠️ Invalid timestamp value for {field}: {value}, using current time")
                    validated_fields[field] = TimestampManager.current_epoch_ms()
        
        return validated_fields
    except Exception as e:
        print(f"❌ Error validating timestamp fields: {str(e)}")
        return update_fields


def update_timestamp_fields_precise(note_id, composite_key, **timestamp_fields):
    """
    Update timestamp fields using BOTH noteId and composite_key for precise targeting.
    Validates timestamp values before updating.
    
    Args:
        note_id (str): The noteId to match
        composite_key (str): The composite_key to match
        **timestamp_fields: Timestamp fields to update (e.g., submitDateEpoch=123456789)
    
    Returns:
        bool: True if exactly 1 document updated, False otherwise
    """
    if not timestamp_fields:
        print("No timestamp fields to update")
        return False
    
    # Validate timestamp fields
    validated_fields = validate_timestamp_fields(timestamp_fields)
    
    result = update_by_noteid_and_composite_key(
        ES_INDEX_PROCESSED_NOTES,
        note_id,
        composite_key,
        **validated_fields
    )
    
    return result is not None and result.get("updated", 0) == 1


def bulk_update_timestamp_fields(updates_df, timestamp_field_names):
    """
    Bulk update timestamp fields for multiple notes with validation.
    
    Args:
        updates_df (DataFrame): DataFrame with noteId and timestamp fields
        timestamp_field_names (list): List of timestamp field names to validate
    
    Returns:
        dict: Update results summary
    """
    results = {
        "successful": 0,
        "failed": 0,
        "validation_corrections": 0,
        "details": []
    }
    
    if "noteId" not in updates_df.columns:
        print("❌ Error: noteId column not found in DataFrame")
        return results
    
    print(f"\n📄 Bulk updating timestamp fields for {len(updates_df)} record(s)")
    print(f"   Timestamp fields: {timestamp_field_names}")
    
    for idx, row in updates_df.iterrows():
        note_id = row.get("noteId")
        
        if not note_id:
            print(f"⚠️ Skipping row {idx} with missing noteId")
            results["failed"] += 1
            continue
        
        # Extract timestamp fields from row
        timestamp_fields = {}
        for field in timestamp_field_names:
            if field in row and row[field] is not None:
                timestamp_fields[field] = row[field]
        
        if not timestamp_fields:
            print(f"⚠️ No timestamp fields to update for noteId: {note_id}")
            results["failed"] += 1
            continue
        
        # Validate and update
        original_count = len(timestamp_fields)
        validated_fields = validate_timestamp_fields(timestamp_fields)
        
        # Count validation corrections
        corrections = sum(1 for field in timestamp_fields 
                         if timestamp_fields[field] != validated_fields.get(field))
        results["validation_corrections"] += corrections
        
        result = update_by_noteid(ES_INDEX_PROCESSED_NOTES, note_id, **validated_fields)
        
        if result and result.get("updated", 0) > 0:
            results["successful"] += 1
            results["details"].append({
                "row": idx,
                "noteId": note_id,
                "status": "success",
                "updated_count": result.get("updated", 0),
                "corrections": corrections
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "row": idx,
                "noteId": note_id,
                "status": "failed",
                "reason": "Update returned 0 documents"
            })
    
    print(f"\n{'='*60}")
    print(f"Bulk Timestamp Update Summary:")
    print(f"  ✅ Successful: {results['successful']}")
    print(f"  ❌ Failed: {results['failed']}")
    print(f"  🔧 Validation corrections: {results['validation_corrections']}")
    print(f"{'='*60}\n")
    
    return results