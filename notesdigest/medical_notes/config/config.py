"""
Centralized Configuration Module for TIA-2 Medical Notes Processing
Loads all configuration from environment variables via .env file
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

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
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
MAX_CONCURRENT_NOTES = int(os.getenv("MAX_CONCURRENT_NOTES", "10"))

# Maximum number of jobs in the queue before rejecting new requests (default: 20)
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "100"))

# Timeout for individual note processing in seconds (default: 600 = 10 minutes)
NOTE_PROCESSING_TIMEOUT = int(os.getenv("NOTE_PROCESSING_TIMEOUT", "1200"))

# AWS Bedrock rate limiting - requests per second (default: 10)
BEDROCK_RATE_LIMIT_RPS = int(os.getenv("BEDROCK_RATE_LIMIT_RPS", "50"))

# Elasticsearch bulk operation batch size (default: 100)
ES_BULK_BATCH_SIZE = int(os.getenv("ES_BULK_BATCH_SIZE", "200"))

# ============================================================================
# EMBEDDINGS CONFIGURATION
# ============================================================================

# PostgreSQL Vector Database Configuration (shared with Chatbot)
POSTGRES_CONNECTION = os.getenv("POSTGRES_CONNECTION")
VECTOR_DB_COLLECTION_NAME = os.getenv("VECTOR_DB_COLLECTION_NAME", "medical_notes_embeddings")

# Embeddings Model Configuration
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "amazon.titan-embed-text-v2:0")

# Text Chunking Configuration
EMBEDDINGS_CHUNK_SIZE = int(os.getenv("EMBEDDINGS_CHUNK_SIZE", "300"))
EMBEDDINGS_CHUNK_OVERLAP = int(os.getenv("EMBEDDINGS_CHUNK_OVERLAP", "50"))

# Retry Configuration for Embeddings
EMBEDDINGS_MAX_RETRIES = int(os.getenv("EMBEDDINGS_MAX_RETRIES", "3"))
EMBEDDINGS_RETRY_DELAY = float(os.getenv("EMBEDDINGS_RETRY_DELAY", "1.0"))

# Enable/disable embeddings processing (default: True)
ENABLE_EMBEDDINGS_PROCESSING = os.getenv("ENABLE_EMBEDDINGS_PROCESSING", "true").lower() in ("true", "1", "yes", "on")

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

def validate_embeddings_config():
    """
    Validate embeddings configuration.
    Raises ValueError if required embeddings config is missing or invalid.
    """
    errors = []
    
    if not POSTGRES_CONNECTION:
        errors.append("POSTGRES_CONNECTION is required but not set")
    
    if not VECTOR_DB_COLLECTION_NAME:
        errors.append("VECTOR_DB_COLLECTION_NAME is required but not set")
    
    if not EMBEDDINGS_MODEL:
        errors.append("EMBEDDINGS_MODEL is required but not set")
    
    # Validate chunk size parameters
    if EMBEDDINGS_CHUNK_SIZE <= 0:
        errors.append(f"EMBEDDINGS_CHUNK_SIZE must be positive, got: {EMBEDDINGS_CHUNK_SIZE}")
    
    if EMBEDDINGS_CHUNK_OVERLAP < 0:
        errors.append(f"EMBEDDINGS_CHUNK_OVERLAP must be non-negative, got: {EMBEDDINGS_CHUNK_OVERLAP}")
    
    if EMBEDDINGS_CHUNK_OVERLAP >= EMBEDDINGS_CHUNK_SIZE:
        errors.append(f"EMBEDDINGS_CHUNK_OVERLAP ({EMBEDDINGS_CHUNK_OVERLAP}) must be less than EMBEDDINGS_CHUNK_SIZE ({EMBEDDINGS_CHUNK_SIZE})")
    
    if errors:
        raise ValueError(
            f"Embeddings configuration errors:\n" + 
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
        "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
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
    
    try:
        validate_embeddings_config()
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
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "aws_region": AWS_REGION,
        "aws_access_key_id": _mask_sensitive_value(AWS_ACCESS_KEY_ID) if AWS_ACCESS_KEY_ID else "NOT_SET",
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
        },
        "embeddings": {
            "postgres_connection": _mask_sensitive_value(POSTGRES_CONNECTION) if POSTGRES_CONNECTION else "NOT_SET",
            "collection_name": VECTOR_DB_COLLECTION_NAME,
            "model_id": EMBEDDINGS_MODEL,
            "chunk_size": EMBEDDINGS_CHUNK_SIZE,
            "chunk_overlap": EMBEDDINGS_CHUNK_OVERLAP,
            "max_retries": EMBEDDINGS_MAX_RETRIES,
            "retry_delay": EMBEDDINGS_RETRY_DELAY,
            "enabled": ENABLE_EMBEDDINGS_PROCESSING,
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