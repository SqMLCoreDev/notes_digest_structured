"""
Centralized Configuration Module for TIA-2 Medical Notes Processing
Loads all configuration from environment variables with sensible defaults
Uses separate .env files for different environments (.env.production, .env.nonprod)
"""

import os
from typing import Dict, Any
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# AWS CONFIGURATION
# ============================================================================

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS = os.getenv("AWS_SECRET_ACCESS")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# ============================================================================
# CLAUDE MODEL CONFIGURATION
# ============================================================================

CLAUDE_OPUS_4_1 = os.getenv("CLAUDE_OPUS_4_1", "us.anthropic.claude-opus-4-1-20250805-v1:0")
CLAUDE_HAIKU_4_5 = os.getenv("CLAUDE_HAIKU_4_5", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
CLAUDE_SONNET_3_5 = os.getenv("CLAUDE_SONNET_3_5", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
CLAUDE_HAIKU_3_5 = os.getenv("CLAUDE_HAIKU_3_5", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
MISTRAL_7_B = os.getenv("MISTRAL_7_B", "mistral.mistral-7b-instruct-v0:2")

# ============================================================================
# ELASTICSEARCH CONFIGURATION
# ============================================================================

ES_URL = os.getenv("ES_URL")
ES_ENCODED_AUTH = os.getenv("ES_ENCODED_AUTH")
ES_USER = os.getenv("ES_USER", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD")

# Elasticsearch indices
ES_INDEX_CLINICAL_NOTES = os.getenv("ES_INDEX_CLINICAL_NOTES")
ES_INDEX_PROCESSED_NOTES = os.getenv("ES_INDEX_PROCESSED_NOTES")

ES_INDEX_NOTES_DIGEST = os.getenv("ES_INDEX_NOTES_DIGEST")
ES_INDEX_TOKEN_USAGE = os.getenv("ES_INDEX_TOKEN_USAGE")

# Create ES_HEADERS dictionary with proper authentication
ES_HEADERS = {
    "Authorization": f"Basic {ES_ENCODED_AUTH}" if ES_ENCODED_AUTH else "",
    "Content-Type": "application/json"
}

# Token usage index
ES_INDEX_TOKEN_USAGE = os.getenv("ES_INDEX_TOKEN_USAGE")

# ============================================================================
# API CONFIGURATION
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL")
API_NOTE_HEADER_TOKEN = os.getenv("API_NOTE_HEADER_TOKEN")

# Create API_HEADERS dictionary with proper authentication
API_HEADERS = {
    "Content-Type": "application/json",
    "noteHeadertoken": API_NOTE_HEADER_TOKEN if API_NOTE_HEADER_TOKEN else ""
}

# Construct full API endpoint
API_ENDPOINT = f"{API_BASE_URL}/savePatientDigestNote" if API_BASE_URL else None

# ============================================================================
# PROCESSING CONFIGURATION
# ============================================================================

# Number of previous visits to include in historical context (default: 1)
N_PREVIOUS_VISITS = int(os.getenv("N_PREVIOUS_VISITS", "1"))

# Enable/disable data structure flattening for note digests (default: True)
ENABLE_DATA_FLATTENING = os.getenv("ENABLE_DATA_FLATTENING", "true").lower() in ("true", "1", "yes", "on")

# ============================================================================
# CONCURRENCY CONFIGURATION
# ============================================================================

# Maximum number of notes to process concurrently (default: 5)
MAX_CONCURRENT_NOTES = int(os.getenv("MAX_CONCURRENT_NOTES", "5"))

# Maximum number of jobs in the queue before rejecting new requests (default: 20)
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "20"))

# Timeout for individual note processing in seconds (default: 600 = 10 minutes)
NOTE_PROCESSING_TIMEOUT = int(os.getenv("NOTE_PROCESSING_TIMEOUT", "600"))

# AWS Bedrock rate limiting - requests per second (default: 10)
BEDROCK_RATE_LIMIT_RPS = int(os.getenv("BEDROCK_RATE_LIMIT_RPS", "10"))

# Elasticsearch bulk operation batch size (default: 100)
ES_BULK_BATCH_SIZE = int(os.getenv("ES_BULK_BATCH_SIZE", "100"))

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_url_format(url: str, url_name: str) -> None:
    """
    Validate URL format and accessibility.
    
    Args:
        url: The URL to validate
        url_name: Name of the URL for error messages
    
    Raises:
        ValueError: If URL format is invalid
    """
    if not url:
        raise ValueError(f"{url_name} is required but not set")
    
    if not url.startswith(('http://', 'https://')):
        raise ValueError(
            f"{url_name} must start with http:// or https://, got: {url}\n"
            f"Example: https://example.com"
        )
    
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError(
                f"{url_name} must have a valid domain name, got: {url}\n"
                f"Example: https://example.com"
            )
        
        # Additional validation for domain name
        domain = parsed.netloc
        if not domain or '.' not in domain:
            raise ValueError(
                f"{url_name} must have a valid domain with TLD, got: {url}\n"
                f"Example: https://example.com"
            )
        
        # Check for invalid characters in domain
        invalid_chars = ['[', ']', ' ', '?', '<', '>', '"', '{', '}', '|', '\\', '^', '`', ',']
        if any(char in domain for char in invalid_chars):
            raise ValueError(
                f"{url_name} contains invalid characters in domain, got: {url}\n"
                f"Example: https://example.com"
            )
            
    except Exception as e:
        if "must have a valid domain" in str(e) or "contains invalid characters" in str(e):
            raise e  # Re-raise our custom validation errors
        raise ValueError(
            f"{url_name} has invalid format: {url}\n"
            f"Error: {str(e)}\n"
            f"Example: https://example.com"
        )

def validate_elasticsearch_config():
    """
    Validate Elasticsearch configuration.
    Raises ValueError if required Elasticsearch config is missing or invalid.
    """
    errors = []
    
    # Validate ES_URL format
    try:
        validate_url_format(ES_URL, "ES_URL")
    except ValueError as e:
        errors.append(str(e))
    
    if not ES_ENCODED_AUTH:
        errors.append("ES_ENCODED_AUTH is required but not set")
    
    if not ES_USER:
        errors.append("ES_USER is required but not set")
    
    # Check that required indices are set
    required_indices = [
        ("ES_INDEX_CLINICAL_NOTES", ES_INDEX_CLINICAL_NOTES),
        ("ES_INDEX_PROCESSED_NOTES", ES_INDEX_PROCESSED_NOTES),
        ("ES_INDEX_NOTES_DIGEST", ES_INDEX_NOTES_DIGEST),
        ("ES_INDEX_TOKEN_USAGE", ES_INDEX_TOKEN_USAGE)
    ]
    
    for index_name, index_value in required_indices:
        if not index_value:
            errors.append(f"{index_name} is required but not set")
    
    if errors:
        raise ValueError(
            f"Elasticsearch configuration errors:\n" + 
            "\n".join(f"  - {error}" for error in errors)
        )

def validate_api_config():
    """
    Validate API configuration.
    Raises ValueError if required API config is missing or invalid.
    """
    errors = []
    
    # Validate API_BASE_URL format
    try:
        validate_url_format(API_BASE_URL, "API_BASE_URL")
    except ValueError as e:
        errors.append(str(e))
    
    if not API_NOTE_HEADER_TOKEN:
        errors.append("API_NOTE_HEADER_TOKEN is required but not set")
    
    # Validate endpoint construction
    if API_BASE_URL and not API_ENDPOINT:
        errors.append("API_ENDPOINT could not be constructed from API_BASE_URL")
    
    if errors:
        raise ValueError(
            f"API configuration errors:\n" + 
            "\n".join(f"  - {error}" for error in errors)
        )

def validate_config():
    """
    Validate that all required configuration variables are set.
    Raises ValueError if any required config is missing or invalid.
    """
    errors = []
    
    # Validate AWS configuration
    required_aws_vars = {
        "AWS_ACCESS_KEY": AWS_ACCESS_KEY,
        "AWS_SECRET_ACCESS": AWS_SECRET_ACCESS,
        "AWS_REGION": AWS_REGION,
    }
    
    missing_aws = [key for key, value in required_aws_vars.items() if not value]
    if missing_aws:
        errors.append(f"Missing required AWS variables: {', '.join(missing_aws)}")
    
    try:
        validate_elasticsearch_config()
    except ValueError as e:
        errors.append(str(e))
    
    try:
        validate_api_config()
    except ValueError as e:
        errors.append(str(e))
    
    if errors:
        raise ValueError(
            f"Configuration validation failed:\n" + 
            "\n".join(f"  {error}" for error in errors) +
            "\nPlease check your environment file and environment variables."
        )

def _mask_sensitive_value(value: str, mask_char: str = "*") -> str:
    """
    Mask sensitive values for secure logging.
    
    Args:
        value: The value to mask
        mask_char: Character to use for masking
    
    Returns:
        Masked value showing only first 4 and last 4 characters
    """
    if not value or len(value) <= 8:
        return mask_char * 8
    
    return value[:4] + mask_char * (len(value) - 8) + value[-4:]

def get_masked_config_summary() -> Dict[str, Any]:
    """
    Return a dictionary summarizing current configuration with sensitive values masked.
    Useful for debugging and logging without exposing credentials.
    """
    return {
        "env_file": env_file,
        "aws_region": AWS_REGION,
        "aws_access_key": _mask_sensitive_value(AWS_ACCESS_KEY) if AWS_ACCESS_KEY else "NOT_SET",
        "claude_model": CLAUDE_HAIKU_4_5,
        "elasticsearch": {
            "url": ES_URL,
            "encoded_auth": _mask_sensitive_value(ES_ENCODED_AUTH) if ES_ENCODED_AUTH else "NOT_SET",
            "user": ES_USER,
            "password": _mask_sensitive_value(ES_PASSWORD) if ES_PASSWORD else "NOT_SET",
            "indices": {
                "clinical_notes": ES_INDEX_CLINICAL_NOTES,
                "processed_notes": ES_INDEX_PROCESSED_NOTES,
                "notes_digest": ES_INDEX_NOTES_DIGEST,
                "token_usage": ES_INDEX_TOKEN_USAGE,
            }
        },
        "api": {
            "base_url": API_BASE_URL,
            "endpoint": API_ENDPOINT,
            "note_header_token": _mask_sensitive_value(API_NOTE_HEADER_TOKEN) if API_NOTE_HEADER_TOKEN else "NOT_SET",
        },
        "processing": {
            "n_previous_visits": N_PREVIOUS_VISITS,
            "enable_data_flattening": ENABLE_DATA_FLATTENING,
        },
        "concurrency": {
            "max_concurrent_notes": MAX_CONCURRENT_NOTES,
            "max_queue_size": MAX_QUEUE_SIZE,
            "note_processing_timeout": NOTE_PROCESSING_TIMEOUT,
            "bedrock_rate_limit_rps": BEDROCK_RATE_LIMIT_RPS,
            "es_bulk_batch_size": ES_BULK_BATCH_SIZE,
        }
    }

def get_config_summary():
    """
    Return a dictionary summarizing current configuration.
    Useful for debugging and logging.
    
    Note: This function is maintained for backward compatibility.
    Use get_masked_config_summary() for secure logging.
    """
    return get_masked_config_summary()

# ============================================================================
# ENVIRONMENT SWITCHING HELPER
# ============================================================================

def get_current_environment() -> str:
    """Get the current environment based on the loaded env file."""
    if ".env.production" in env_file:
        return "production"
    elif ".env.nonprod" in env_file:
        return "nonprod"
    else:
        return "unknown"