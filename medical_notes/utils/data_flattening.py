"""
Data Structure Flattening System
Transforms all nested objects into flat field structures for improved 
Elasticsearch query performance and simplified data access patterns.
"""

from typing import Dict, Any, List, Tuple
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Demographics fields to flatten
DEMOGRAPHICS_FIELDS = [
    "Patientname", "mrn", "age", "sex", "dateofbirth", 
    "dateofadmission", "dateofdischarge", "dateofservice", "CSN | FIN"
]

# Service details fields to flatten  
SERVICE_DETAILS_FIELDS = [
    "consultant_name", "department", "signature_information",
    "practice_name", "location", "contact_information", 
    "additional_providers", "attending_details", "pcp_details"
]

# Simple content objects to flatten (22 objects)
SIMPLE_CONTENT_OBJECTS = [
    "cpt", "plan", "vitals", "allergies", "red_flags", "impression",
    "identifiers", "overview", "chief_complaint", "history_of_present_illness",
    "past_medical_history", "surgical_history", "family_history", "social_history",
    "review_of_systems", "physical_exam", "secondary_diagnoses", "differential_diagnoses",
    "comorbidities", "procedures", "clinical_timeline", "clinical_course",
    "care_coordination", "risk_assessment", "continuity_recommendations", "follow_up"
]

# Complex array objects to flatten
COMPLEX_ARRAY_OBJECTS = {
    "medications": ["past", "current", "infusing", "PRN"],
    "lab": ["content"]
}


def flatten_all_nested_objects(record: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Flatten all nested objects in medical note digest records.
    
    This function extracts all fields from nested demographics, service_details, 
    clinical data objects, medications, and lab objects, placing them at the root 
    level of the record. Simple content objects are flattened with _content suffix,
    while complex array objects are converted to JSON strings.
    
    If the record is already flattened (no nested objects), it returns the record
    unchanged with no processing issues.
    
    Args:
        record: Dictionary containing note digest with all nested objects
        
    Returns:
        tuple: (completely_flattened_record, issues_list)
            - completely_flattened_record: Record with all fields at root level
            - issues_list: List of processing issues encountered
    """
    if not isinstance(record, dict):
        return record, ["Input record is not a dictionary"]
    
    # Check if record is already flattened (no nested objects present)
    if _is_already_flattened(record):
        logger.info("Record is already flattened, returning unchanged")
        return record, []
    
    # Create a copy of the original record to avoid modifying the input
    flattened_record = record.copy()
    issues = []
    
    try:
        # Validate input structure before processing
        input_validation_issues = _validate_input_structure(flattened_record)
        issues.extend(input_validation_issues)
        
        # Process demographics object
        demographics_issues = _extract_demographics_fields(flattened_record)
        issues.extend(demographics_issues)
        
        # Process service_details object
        service_details_issues = _extract_service_details_fields(flattened_record)
        issues.extend(service_details_issues)
        
        # Process simple content objects
        simple_content_issues = _extract_simple_content_objects(flattened_record)
        issues.extend(simple_content_issues)
        
        # Process complex array objects
        complex_array_issues = _extract_complex_array_objects(flattened_record)
        issues.extend(complex_array_issues)
        
        # Validate required fields are at root level
        validation_issues = _validate_required_fields_at_root_level(flattened_record)
        issues.extend(validation_issues)
        
        # Remove all original nested objects after successful extraction
        _remove_nested_objects(flattened_record)
        
        # Preserve field order for consistency
        flattened_record = _preserve_field_order(flattened_record)
            
        # Final output validation
        output_validation_issues = _validate_output_structure(flattened_record)
        issues.extend(output_validation_issues)
        
        # Comprehensive success logging with field count information
        _log_comprehensive_success(flattened_record, issues)
        
    except Exception as e:
        error_msg = f"Complete flattening failure: {str(e)}"
        logger.error(error_msg)
        issues.append(error_msg)
        # Return original structure on complete failure
        return record, issues
    
    return flattened_record, issues


def _is_already_flattened(record: Dict[str, Any]) -> bool:
    """
    Check if a record is already flattened (no nested objects present).
    
    A record is considered already flattened if:
    1. It has no nested objects (demographics, service_details, clinical objects)
    2. It has some expected flattened fields at the root level
    
    Args:
        record: Record to check
        
    Returns:
        True if record is already flattened, False otherwise
    """
    # Check if any nested objects are present
    has_demographics = 'demographics' in record and record['demographics'] is not None
    has_service_details = 'service_details' in record and record['service_details'] is not None
    has_clinical_objects = any(obj in record and record[obj] is not None for obj in SIMPLE_CONTENT_OBJECTS)
    has_complex_objects = any(obj in record and record[obj] is not None for obj in COMPLEX_ARRAY_OBJECTS.keys())
    
    # If any nested objects are present, it's not flattened
    if has_demographics or has_service_details or has_clinical_objects or has_complex_objects:
        return False
    
    # Check if some expected flattened fields are present at root level
    # This indicates the record has already been processed
    expected_root_fields = [
        'patientName', 'patientmrn', 'noteId', 'noteType',  # Common root fields
        'Patientname', 'mrn', 'age', 'sex',  # Demographics fields
        'consultant_name', 'department', 'location',  # Service details fields
    ]
    
    # If we have some expected root fields and no nested objects, it's already flattened
    root_fields_present = sum(1 for field in expected_root_fields if field in record)
    
    # Consider it flattened if we have at least 3 expected root fields and no nested objects
    return root_fields_present >= 3


def _log_comprehensive_success(flattened_record: Dict[str, Any], issues: List[str]) -> None:
    """
    Log comprehensive success information with field count details for all processed object types.
    
    Args:
        flattened_record: The successfully flattened record
        issues: List of issues encountered during processing
    """
    # Count flattened fields by type
    demographics_count = sum(1 for field in DEMOGRAPHICS_FIELDS if field in flattened_record)
    service_details_count = sum(1 for field in SERVICE_DETAILS_FIELDS if field in flattened_record)
    
    simple_content_count = 0
    for object_name in SIMPLE_CONTENT_OBJECTS:
        field_name = f"{object_name}_content"
        if field_name in flattened_record:
            simple_content_count += 1
    
    complex_array_count = 0
    for object_name, array_keys in COMPLEX_ARRAY_OBJECTS.items():
        for array_key in array_keys:
            if object_name == "medications":
                field_name = f"{object_name}_{array_key}"
            else:
                field_name = f"{object_name}_{array_key}"
            if field_name in flattened_record:
                complex_array_count += 1
    
    total_flattened_fields = demographics_count + service_details_count + simple_content_count + complex_array_count
    total_fields = len(flattened_record)
    
    logger.info(f"Successfully flattened record: "
                f"Demographics={demographics_count}/{len(DEMOGRAPHICS_FIELDS)}, "
                f"ServiceDetails={service_details_count}/{len(SERVICE_DETAILS_FIELDS)}, "
                f"SimpleContent={simple_content_count}/{len(SIMPLE_CONTENT_OBJECTS)}, "
                f"ComplexArrays={complex_array_count}/{sum(len(keys) for keys in COMPLEX_ARRAY_OBJECTS.values())}, "
                f"TotalFlattened={total_flattened_fields}, "
                f"TotalFields={total_fields}, "
                f"Issues={len(issues)}")
    
    if issues:
        logger.warning(f"Processing completed with {len(issues)} issues:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"  Issue {i}: {issue}")
    else:
        logger.info("Processing completed with no issues")


def _extract_simple_content_objects(record: Dict[str, Any]) -> List[str]:
    """
    Extract all fields from simple content objects and place them at root level with _content suffix.
    Includes comprehensive error handling for all clinical objects.
    
    Args:
        record: Record dictionary to modify in-place
        
    Returns:
        List of issues encountered during extraction
    """
    issues = []
    
    for object_name in SIMPLE_CONTENT_OBJECTS:
        try:
            nested_object = record.get(object_name)
            
            if nested_object is None:
                # Handle missing object with empty string default
                field_name = f"{object_name}_content"
                record[field_name] = ""
                logger.debug(f"{object_name} object is missing, using empty string default")
                continue
            
            if not isinstance(nested_object, dict):
                # Handle malformed object
                logger.warning(f"{object_name} object is not a dictionary, using empty string default")
                field_name = f"{object_name}_content"
                record[field_name] = ""
                issues.append(f"{object_name} object malformed - used empty string default")
                continue
            
            # Extract content field from nested object
            content = nested_object.get('content', '')
            field_name = f"{object_name}_content"
            
            if content is None:
                record[field_name] = ""
                logger.debug(f"{object_name}.content is null, using empty string default")
            else:
                try:
                    # Preserve content exactly as it appears, with type-appropriate handling
                    if isinstance(content, (dict, list)):
                        # For complex content, convert to JSON string
                        record[field_name] = json.dumps(content, ensure_ascii=False)
                        logger.debug(f"{object_name}.content converted from complex type to JSON string")
                    else:
                        # For simple content, convert to string
                        record[field_name] = str(content)
                except (TypeError, ValueError) as json_error:
                    # Handle JSON serialization errors
                    logger.warning(f"Failed to process {object_name}.content: {json_error}")
                    record[field_name] = str(content) if content is not None else ""
                    issues.append(f"{object_name}.content processing failed - used string representation")
                
        except Exception as e:
            error_msg = f"{object_name} extraction error: {str(e)}"
            logger.error(error_msg)
            issues.append(error_msg)
            # Provide empty string default on error
            field_name = f"{object_name}_content"
            record[field_name] = ""
    
    return issues


def _extract_complex_array_objects(record: Dict[str, Any]) -> List[str]:
    """
    Extract complex array objects and convert them to JSON strings at root level.
    Includes comprehensive error handling for complex clinical structures.
    
    Args:
        record: Record dictionary to modify in-place
        
    Returns:
        List of issues encountered during extraction
    """
    issues = []
    
    for object_name, array_keys in COMPLEX_ARRAY_OBJECTS.items():
        try:
            nested_object = record.get(object_name)
            
            if nested_object is None:
                # Handle missing object with empty string defaults for all array keys
                logger.debug(f"{object_name} object is missing, using empty string defaults")
                for array_key in array_keys:
                    if object_name == "medications":
                        field_name = f"{object_name}_{array_key}"
                    else:
                        field_name = f"{object_name}_{array_key}"
                    record[field_name] = ""
                continue
            
            if not isinstance(nested_object, dict):
                # Handle malformed object
                logger.warning(f"{object_name} object is not a dictionary, using empty string defaults")
                for array_key in array_keys:
                    if object_name == "medications":
                        field_name = f"{object_name}_{array_key}"
                    else:
                        field_name = f"{object_name}_{array_key}"
                    record[field_name] = ""
                issues.append(f"{object_name} object malformed - used empty string defaults")
                continue
            
            # Extract each array from the nested object with comprehensive error handling
            for array_key in array_keys:
                try:
                    array_data = nested_object.get(array_key, [])
                    
                    if object_name == "medications":
                        field_name = f"{object_name}_{array_key}"
                    else:
                        field_name = f"{object_name}_{array_key}"
                    
                    if array_data is None:
                        record[field_name] = ""
                        logger.debug(f"{object_name}.{array_key} is null, using empty string default")
                    elif isinstance(array_data, list):
                        # Handle empty arrays
                        if len(array_data) == 0:
                            record[field_name] = "[]"
                            logger.debug(f"{object_name}.{array_key} is empty array")
                        else:
                            # Convert array to JSON string while preserving structure
                            try:
                                # Validate array contents before serialization
                                validated_array = []
                                for item in array_data:
                                    if item is None:
                                        validated_array.append(None)
                                    elif isinstance(item, dict):
                                        # Ensure all dict values are serializable
                                        validated_item = {}
                                        for k, v in item.items():
                                            try:
                                                json.dumps(v)  # Test serializability
                                                validated_item[k] = v
                                            except (TypeError, ValueError):
                                                validated_item[k] = str(v) if v is not None else None
                                        validated_array.append(validated_item)
                                    else:
                                        validated_array.append(item)
                                
                                record[field_name] = json.dumps(validated_array, ensure_ascii=False)
                                logger.debug(f"{object_name}.{array_key} successfully serialized to JSON")
                            except (TypeError, ValueError) as json_error:
                                logger.warning(f"Failed to serialize {object_name}.{array_key} to JSON: {json_error}")
                                record[field_name] = str(array_data)
                                issues.append(f"JSON serialization failed for {object_name}.{array_key} - used string representation")
                    else:
                        # Handle non-array data
                        try:
                            if isinstance(array_data, dict):
                                record[field_name] = json.dumps(array_data, ensure_ascii=False)
                                logger.debug(f"{object_name}.{array_key} converted from dict to JSON string")
                            else:
                                record[field_name] = json.dumps(array_data, ensure_ascii=False)
                                logger.debug(f"{object_name}.{array_key} converted to JSON string")
                        except (TypeError, ValueError):
                            record[field_name] = str(array_data)
                            issues.append(f"Non-array data in {object_name}.{array_key} - converted to string")
                
                except Exception as array_error:
                    # Handle partial failure for individual array keys
                    error_msg = f"{object_name}.{array_key} processing error: {str(array_error)}"
                    logger.error(error_msg)
                    issues.append(error_msg)
                    # Provide empty string default for this specific array key
                    if object_name == "medications":
                        field_name = f"{object_name}_{array_key}"
                    else:
                        field_name = f"{object_name}_{array_key}"
                    record[field_name] = ""
                
        except Exception as e:
            error_msg = f"{object_name} extraction error: {str(e)}"
            logger.error(error_msg)
            issues.append(error_msg)
            # Provide empty string defaults for all array keys on error
            for array_key in array_keys:
                if object_name == "medications":
                    field_name = f"{object_name}_{array_key}"
                else:
                    field_name = f"{object_name}_{array_key}"
                record[field_name] = ""
    
    return issues


def _remove_nested_objects(record: Dict[str, Any]) -> None:
    """
    Remove all nested objects after successful extraction.
    
    Args:
        record: Record dictionary to modify in-place
    """
    # Remove demographics and service_details objects
    if 'demographics' in record:
        del record['demographics']
    if 'service_details' in record:
        del record['service_details']
    
    # Remove simple content objects
    for object_name in SIMPLE_CONTENT_OBJECTS:
        if object_name in record:
            del record[object_name]
    
    # Remove complex array objects
    for object_name in COMPLEX_ARRAY_OBJECTS.keys():
        if object_name in record:
            del record[object_name]


def _preserve_field_order(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preserve field order for consistency across all flattened object types.
    
    Args:
        record: Record dictionary to reorder
        
    Returns:
        Reordered dictionary with consistent field order
    """
    ordered_record = {}
    
    # First, add non-flattened fields in their original order
    for key, value in record.items():
        if not _is_flattened_field(key):
            ordered_record[key] = value
    
    # Then add demographics fields in consistent order
    for field in DEMOGRAPHICS_FIELDS:
        if field in record:
            ordered_record[field] = record[field]
    
    # Then add service details fields in consistent order
    for field in SERVICE_DETAILS_FIELDS:
        if field in record:
            ordered_record[field] = record[field]
    
    # Then add simple content fields in alphabetical order for consistency
    for object_name in sorted(SIMPLE_CONTENT_OBJECTS):
        field_name = f"{object_name}_content"
        if field_name in record:
            ordered_record[field_name] = record[field_name]
    
    # Finally add complex array fields in consistent order
    for object_name in sorted(COMPLEX_ARRAY_OBJECTS.keys()):
        array_keys = COMPLEX_ARRAY_OBJECTS[object_name]
        for array_key in sorted(array_keys):
            if object_name == "medications":
                field_name = f"{object_name}_{array_key}"
            else:
                field_name = f"{object_name}_{array_key}"
            if field_name in record:
                ordered_record[field_name] = record[field_name]
    
    return ordered_record


def _is_flattened_field(field_name: str) -> bool:
    """
    Check if a field name is a flattened field from nested objects.
    
    Args:
        field_name: Field name to check
        
    Returns:
        True if field is a flattened field, False otherwise
    """
    # Check if it's a demographics field
    if field_name in DEMOGRAPHICS_FIELDS:
        return True
    
    # Check if it's a service details field
    if field_name in SERVICE_DETAILS_FIELDS:
        return True
    
    # Check if it's a simple content field
    if field_name.endswith('_content'):
        object_name = field_name[:-8]  # Remove '_content' suffix
        if object_name in SIMPLE_CONTENT_OBJECTS:
            return True
    
    # Check if it's a complex array field
    for object_name, array_keys in COMPLEX_ARRAY_OBJECTS.items():
        for array_key in array_keys:
            if object_name == "medications":
                expected_field = f"{object_name}_{array_key}"
            else:
                expected_field = f"{object_name}_{array_key}"
            if field_name == expected_field:
                return True
    
    return False


def _extract_demographics_fields(record: Dict[str, Any]) -> List[str]:
    """
    Extract all fields from demographics object and place them at root level.
    Includes special handling for date formats and CSN/FIN fields.
    
    Args:
        record: Record dictionary to modify in-place
        
    Returns:
        List of issues encountered during extraction
    """
    issues = []
    demographics = record.get('demographics')
    
    if demographics is None:
        # Handle missing demographics object with empty string defaults
        logger.warning("Demographics object is missing, using empty string defaults")
        for field in DEMOGRAPHICS_FIELDS:
            record[field] = ""
        issues.append("Demographics object missing - used empty string defaults")
        return issues
    
    if not isinstance(demographics, dict):
        # Handle malformed demographics object
        logger.warning("Demographics object is not a dictionary, using empty string defaults")
        for field in DEMOGRAPHICS_FIELDS:
            record[field] = ""
        issues.append("Demographics object malformed - used empty string defaults")
        return issues
    
    try:
        # Extract all fields from demographics object
        for field_name, field_value in demographics.items():
            # Preserve field names exactly as they appear in nested structure
            if field_value is None:
                record[field_name] = ""
            else:
                # Special handling for date fields and special values
                processed_value = _process_date_and_special_values(field_name, field_value)
                record[field_name] = processed_value
        
        # Special handling for CSN/FIN field - preserve whichever values are present
        _handle_csn_fin_field(record, demographics, issues)
        
        # Ensure all expected demographics fields are present with defaults if missing
        for expected_field in DEMOGRAPHICS_FIELDS:
            if expected_field not in record:
                record[expected_field] = ""
                issues.append(f"Demographics field '{expected_field}' missing - used empty string default")
                
    except Exception as e:
        error_msg = f"Demographics extraction error: {str(e)}"
        logger.error(error_msg)
        issues.append(error_msg)
        # Provide empty string defaults for all expected fields on error
        for field in DEMOGRAPHICS_FIELDS:
            if field not in record:
                record[field] = ""
    
    return issues


def _extract_service_details_fields(record: Dict[str, Any]) -> List[str]:
    """
    Extract all fields from service_details object and place them at root level.
    Includes preservation of provider information structure and contact formatting.
    
    Args:
        record: Record dictionary to modify in-place
        
    Returns:
        List of issues encountered during extraction
    """
    issues = []
    service_details = record.get('service_details')
    
    if service_details is None:
        # Handle missing service_details object with empty string defaults
        logger.warning("Service_details object is missing, using empty string defaults")
        for field in SERVICE_DETAILS_FIELDS:
            record[field] = ""
        issues.append("Service_details object missing - used empty string defaults")
        return issues
    
    if not isinstance(service_details, dict):
        # Handle malformed service_details object
        logger.warning("Service_details object is not a dictionary, using empty string defaults")
        for field in SERVICE_DETAILS_FIELDS:
            record[field] = ""
        issues.append("Service_details object malformed - used empty string defaults")
        return issues
    
    try:
        # Extract all fields from service_details object
        for field_name, field_value in service_details.items():
            # Preserve field names exactly as they appear in nested structure
            if field_value is None:
                record[field_name] = ""
            else:
                # Preserve provider information structure and contact formatting
                processed_value = _preserve_provider_and_contact_formatting(field_name, field_value)
                record[field_name] = processed_value
        
        # Ensure all expected service details fields are present with defaults if missing
        for expected_field in SERVICE_DETAILS_FIELDS:
            if expected_field not in record:
                record[expected_field] = ""
                issues.append(f"Service details field '{expected_field}' missing - used empty string default")
                
    except Exception as e:
        error_msg = f"Service details extraction error: {str(e)}"
        logger.error(error_msg)
        issues.append(error_msg)
        # Provide empty string defaults for all expected fields on error
        for field in SERVICE_DETAILS_FIELDS:
            if field not in record:
                record[field] = ""
    
    return issues
    """
    Extract all fields from demographics object and place them at root level.
    Includes special handling for date formats and CSN/FIN fields.
    
    Args:
        record: Record dictionary to modify in-place
        
    Returns:
        List of issues encountered during extraction
    """
    issues = []
    demographics = record.get('demographics')
    
    if demographics is None:
        # Handle missing demographics object with empty string defaults
        logger.warning("Demographics object is missing, using empty string defaults")
        for field in DEMOGRAPHICS_FIELDS:
            record[field] = ""
        issues.append("Demographics object missing - used empty string defaults")
        return issues
    
    if not isinstance(demographics, dict):
        # Handle malformed demographics object
        logger.warning("Demographics object is not a dictionary, using empty string defaults")
        for field in DEMOGRAPHICS_FIELDS:
            record[field] = ""
        issues.append("Demographics object malformed - used empty string defaults")
        return issues
    
    try:
        # Extract all fields from demographics object
        for field_name, field_value in demographics.items():
            # Preserve field names exactly as they appear in nested structure
            if field_value is None:
                record[field_name] = ""
            else:
                # Special handling for date fields and special values
                processed_value = _process_date_and_special_values(field_name, field_value)
                record[field_name] = processed_value
        
        # Special handling for CSN/FIN field - preserve whichever values are present
        _handle_csn_fin_field(record, demographics, issues)
        
        # Ensure all expected demographics fields are present with defaults if missing
        for expected_field in DEMOGRAPHICS_FIELDS:
            if expected_field not in record:
                record[expected_field] = ""
                issues.append(f"Demographics field '{expected_field}' missing - used empty string default")
                
    except Exception as e:
        error_msg = f"Demographics extraction error: {str(e)}"
        logger.error(error_msg)
        issues.append(error_msg)
        # Provide empty string defaults for all expected fields on error
        for field in DEMOGRAPHICS_FIELDS:
            if field not in record:
                record[field] = ""
    
    return issues


def _extract_service_details_fields(record: Dict[str, Any]) -> List[str]:
    """
    Extract all fields from service_details object and place them at root level.
    Includes preservation of provider information structure and contact formatting.
    
    Args:
        record: Record dictionary to modify in-place
        
    Returns:
        List of issues encountered during extraction
    """
    issues = []
    service_details = record.get('service_details')
    
    if service_details is None:
        # Handle missing service_details object with empty string defaults
        logger.warning("Service_details object is missing, using empty string defaults")
        for field in SERVICE_DETAILS_FIELDS:
            record[field] = ""
        issues.append("Service_details object missing - used empty string defaults")
        return issues
    
    if not isinstance(service_details, dict):
        # Handle malformed service_details object
        logger.warning("Service_details object is not a dictionary, using empty string defaults")
        for field in SERVICE_DETAILS_FIELDS:
            record[field] = ""
        issues.append("Service_details object malformed - used empty string defaults")
        return issues
    
    try:
        # Extract all fields from service_details object
        for field_name, field_value in service_details.items():
            # Preserve field names exactly as they appear in nested structure
            if field_value is None:
                record[field_name] = ""
            else:
                # Preserve provider information structure and contact formatting
                processed_value = _preserve_provider_and_contact_formatting(field_name, field_value)
                record[field_name] = processed_value
        
        # Ensure all expected service details fields are present with defaults if missing
        for expected_field in SERVICE_DETAILS_FIELDS:
            if expected_field not in record:
                record[expected_field] = ""
                issues.append(f"Service details field '{expected_field}' missing - used empty string default")
                
    except Exception as e:
        error_msg = f"Service details extraction error: {str(e)}"
        logger.error(error_msg)
        issues.append(error_msg)
        # Provide empty string defaults for all expected fields on error
        for field in SERVICE_DETAILS_FIELDS:
            if field not in record:
                record[field] = ""
    
    return issues


def _validate_input_structure(record: Dict[str, Any]) -> List[str]:
    """
    Validate that the input contains the expected nested structure for all object types.
    
    Args:
        record: Input record to validate
        
    Returns:
        List of validation issues
    """
    issues = []
    
    if not isinstance(record, dict):
        issues.append("Input record is not a dictionary")
        return issues
    
    # Check if at least one of the expected nested objects is present
    has_demographics = 'demographics' in record
    has_service_details = 'service_details' in record
    has_clinical_objects = any(obj in record for obj in SIMPLE_CONTENT_OBJECTS)
    has_complex_objects = any(obj in record for obj in COMPLEX_ARRAY_OBJECTS.keys())
    
    if not (has_demographics or has_service_details or has_clinical_objects or has_complex_objects):
        issues.append("Input record contains no recognizable nested objects")
    
    # Validate structure of demographics object if present
    if has_demographics:
        demographics = record['demographics']
        if demographics is not None and not isinstance(demographics, dict):
            issues.append("Demographics object is not a dictionary")
    
    # Validate structure of service_details object if present
    if has_service_details:
        service_details = record['service_details']
        if service_details is not None and not isinstance(service_details, dict):
            issues.append("Service_details object is not a dictionary")
    
    # Validate structure of simple content objects if present
    for object_name in SIMPLE_CONTENT_OBJECTS:
        if object_name in record:
            nested_object = record[object_name]
            if nested_object is not None and not isinstance(nested_object, dict):
                issues.append(f"{object_name} object is not a dictionary")
    
    # Validate structure of complex array objects if present
    for object_name in COMPLEX_ARRAY_OBJECTS.keys():
        if object_name in record:
            nested_object = record[object_name]
            if nested_object is not None and not isinstance(nested_object, dict):
                issues.append(f"{object_name} object is not a dictionary")
    
    return issues


def _validate_required_fields_at_root_level(record: Dict[str, Any]) -> List[str]:
    """
    Validate that required fields from all nested object types are at root level.
    
    Args:
        record: Flattened record to validate
        
    Returns:
        List of validation issues
    """
    issues = []
    
    # Required demographics fields that should be at root level
    required_demographics_fields = ["Patientname", "mrn", "age", "sex"]
    date_fields = ["dateofbirth", "dateofadmission", "dateofdischarge", "dateofservice"]
    
    # Check required demographics fields
    for field in required_demographics_fields:
        if field not in record:
            issues.append(f"Required demographics field '{field}' missing at root level")
        elif not isinstance(record[field], str):
            issues.append(f"Required demographics field '{field}' is not a string at root level")
    
    # Check date fields are present (they can be empty strings)
    for field in date_fields:
        if field not in record:
            issues.append(f"Date field '{field}' missing at root level")
    
    # Check CSN/FIN field
    if "CSN | FIN" not in record:
        issues.append("CSN/FIN field missing at root level")
    
    # Required service details fields that should be at root level
    required_service_fields = ["consultant_name", "department", "signature_information", "practice_name"]
    
    # Check required service details fields
    for field in required_service_fields:
        if field not in record:
            issues.append(f"Required service details field '{field}' missing at root level")
        elif not isinstance(record[field], str):
            issues.append(f"Required service details field '{field}' is not a string at root level")
    
    # Check that all simple content objects have their flattened fields
    for object_name in SIMPLE_CONTENT_OBJECTS:
        field_name = f"{object_name}_content"
        if field_name not in record:
            issues.append(f"Required clinical field '{field_name}' missing at root level")
        elif not isinstance(record[field_name], str):
            issues.append(f"Required clinical field '{field_name}' is not a string at root level")
    
    # Check that all complex array objects have their flattened fields
    for object_name, array_keys in COMPLEX_ARRAY_OBJECTS.items():
        for array_key in array_keys:
            if object_name == "medications":
                field_name = f"{object_name}_{array_key}"
            else:
                field_name = f"{object_name}_{array_key}"
            
            if field_name not in record:
                issues.append(f"Required complex field '{field_name}' missing at root level")
            elif not isinstance(record[field_name], str):
                issues.append(f"Required complex field '{field_name}' is not a string at root level")
    
    return issues


def _validate_output_structure(record: Dict[str, Any]) -> List[str]:
    """
    Validate that the output contains all required top-level fields and no nested objects.
    
    Args:
        record: Output record to validate
        
    Returns:
        List of validation issues
    """
    issues = []
    
    # Ensure no nested objects remain
    if 'demographics' in record:
        issues.append("Nested demographics object still present in output")
    
    if 'service_details' in record:
        issues.append("Nested service_details object still present in output")
    
    # Check that no simple content objects remain
    for object_name in SIMPLE_CONTENT_OBJECTS:
        if object_name in record:
            issues.append(f"Nested {object_name} object still present in output")
    
    # Check that no complex array objects remain
    for object_name in COMPLEX_ARRAY_OBJECTS.keys():
        if object_name in record:
            issues.append(f"Nested {object_name} object still present in output")
    
    # Verify all expected demographics fields are present
    for field in DEMOGRAPHICS_FIELDS:
        if field not in record:
            issues.append(f"Expected demographics field '{field}' missing from output")
    
    # Verify all expected service details fields are present
    for field in SERVICE_DETAILS_FIELDS:
        if field not in record:
            issues.append(f"Expected service details field '{field}' missing from output")
    
    # Verify all expected simple content fields are present
    for object_name in SIMPLE_CONTENT_OBJECTS:
        field_name = f"{object_name}_content"
        if field_name not in record:
            issues.append(f"Expected flattened field '{field_name}' missing from output")
    
    # Verify all expected complex array fields are present
    for object_name, array_keys in COMPLEX_ARRAY_OBJECTS.items():
        for array_key in array_keys:
            if object_name == "medications":
                field_name = f"{object_name}_{array_key}"
            else:
                field_name = f"{object_name}_{array_key}"
            if field_name not in record:
                issues.append(f"Expected flattened field '{field_name}' missing from output")
    
    return issues


def _process_date_and_special_values(field_name: str, field_value: Any) -> str:
    """
    Process date fields and special values, maintaining original formats.
    
    Args:
        field_name: Name of the field being processed
        field_value: Value to process
        
    Returns:
        Processed field value as string
    """
    if field_value is None:
        return ""
    
    # Convert to string to preserve formatting
    str_value = str(field_value)
    
    # Check if this is a date field
    date_field_names = ["dateofbirth", "dateofadmission", "dateofdischarge", "dateofservice"]
    
    if field_name.lower() in [name.lower() for name in date_field_names]:
        # Preserve special values exactly as they are
        special_values = [
            "No relevant information on file",
            "Not available",
            "Unknown",
            "N/A",
            ""
        ]
        
        # If it's a special value, preserve it exactly
        for special_value in special_values:
            if str_value.strip() == special_value:
                return str_value
        
        # For actual dates, preserve the original format
        # Don't attempt to parse or reformat - just preserve as-is
        return str_value
    
    return str_value


def _handle_csn_fin_field(record: Dict[str, Any], demographics: Dict[str, Any], issues: List[str]) -> None:
    """
    Handle CSN/FIN field, preserving whichever values are present in source data.
    
    Args:
        record: Record being processed (modified in-place)
        demographics: Original demographics object
        issues: Issues list to append to
    """
    csn_fin_field = "CSN | FIN"
    
    # Check if the exact field name exists
    if csn_fin_field in demographics:
        value = demographics[csn_fin_field]
        record[csn_fin_field] = str(value) if value is not None else ""
        return
    
    # Check for variations of CSN/FIN field names
    csn_fin_variations = [
        "CSN | FIN", "CSN|FIN", "CSN/FIN", "CSN", "FIN", 
        "csn | fin", "csn|fin", "csn/fin", "csn", "fin"
    ]
    
    found_field = None
    found_value = None
    
    for variation in csn_fin_variations:
        if variation in demographics:
            found_field = variation
            found_value = demographics[variation]
            break
    
    if found_field:
        # Use the found field name and preserve its value
        record[csn_fin_field] = str(found_value) if found_value is not None else ""
        # Also preserve the original field name if different
        if found_field != csn_fin_field:
            record[found_field] = str(found_value) if found_value is not None else ""
    else:
        # No CSN/FIN field found, use empty string default
        record[csn_fin_field] = ""
        issues.append("CSN/FIN field not found in demographics - used empty string default")


def _preserve_provider_and_contact_formatting(field_name: str, field_value: Any) -> str:
    """
    Preserve provider information structure and contact formatting.
    
    Args:
        field_name: Name of the field being processed
        field_value: Value to process
        
    Returns:
        Processed field value with preserved formatting
    """
    if field_value is None:
        return ""
    
    # Convert to string to preserve formatting
    str_value = str(field_value)
    
    # Fields that should preserve special formatting
    formatting_sensitive_fields = [
        "contact_information", "location", "additional_providers", 
        "attending_details", "pcp_details", "signature_information"
    ]
    
    if field_name.lower() in [name.lower() for name in formatting_sensitive_fields]:
        # Preserve all formatting including newlines, spaces, and special characters
        # This maintains the structure of contact information and provider lists
        return str_value
    
    return str_value