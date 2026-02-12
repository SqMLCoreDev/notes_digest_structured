"""
app/core/config.py - Application Configuration

Type-safe configuration using Pydantic Settings with environment variable validation.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings can be overridden via .env file or environment.
    """
    
    # ===========================================
    # Application Settings
    # ===========================================
    APP_NAME: str = Field(default="MCP Chatbot API", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    
    # ===========================================
    # AWS Credentials
    # ===========================================
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, description="AWS Access Key ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, description="AWS Secret Access Key")
    AWS_REGION: str = Field(default="us-east-1", description="AWS Region")
    
    # ===========================================
    # Bedrock Model Configuration
    # ===========================================
    CLAUDE_SONNET_3_5: str = Field(
        default="us.anthropic.claude-3-5-sonnet-20241022-v2",
        description="Claude Sonnet 3.5 model ID"
    )
    CLAUDE_HAIKU_3_5: str = Field(
        default="us.anthropic.claude-3-5-haiku-20241022-v1",
        description="Claude Haiku 3.5 model ID"
    )
    CLAUDE_HAIKU_4_5: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1",
        description="Claude Haiku 4.5 model ID"
    )
    CLAUDE_OPUS_4_1: str = Field(
        default="us.anthropic.claude-opus-4-1-20250805-v1",
        description="Claude Opus 4.1 model ID"
    )
    MISTRAL_7_B: str = Field(
        default="mistral.mistral-7b-instruct-v0:2",
        description="Mistral 7B model ID"
    )
    MODEL: str = Field(default="CLAUDE_HAIKU_4_5", description="Model name to use")
    MAX_TOKENS: int = Field(default=100000, description="Maximum tokens for model response")
    
    # ===========================================
    # Elasticsearch Configuration
    # ===========================================
    ES_URL: Optional[str] = Field(default=None, description="Elasticsearch cluster URL")
    ES_USER: Optional[str] = Field(default=None, description="Elasticsearch username")
    ES_PASSWORD: Optional[str] = Field(default=None, description="Elasticsearch password")
    
    # NotesDigest Elasticsearch indices
    ES_INDEX_CLINICAL_NOTES: Optional[str] = Field(default=None, description="Clinical notes index")
    ES_INDEX_PROCESSED_NOTES: Optional[str] = Field(default=None, description="Processed notes index")
    ES_INDEX_NOTES_DIGEST: Optional[str] = Field(default=None, description="Notes digest index")
    ES_INDEX_TOKEN_USAGE: Optional[str] = Field(default=None, description="Token usage index")
    
    # ===========================================
    # Cache Configuration
    # ===========================================
    CACHE_TYPE: str = Field(default="memory", description="Cache type: memory, redis")
    REDIS_URL: Optional[str] = Field(default=None, description="Redis URL for caching")
    MAX_RESPONSES_PER_SESSION: int = Field(default=10, description="Max responses to cache per session")
    CACHE_TTL_SECONDS: int = Field(default=3600, description="Cache TTL in seconds (Redis only)")
    
    # ===========================================
    # Vector Store & Embeddings Configuration
    # ===========================================
    POSTGRES_CONNECTION: Optional[str] = Field(
        default=None, 
        description="PostgreSQL connection string for PGVector (e.g., postgresql://user:pass@host:5432/db)"
    )
    COLLECTION_NAME: str = Field(
        default="medical_notes_embeddings",
        description="Vector collection name for storing embeddings"
    )
    VECTOR_DB_COLLECTION_NAME: str = Field(
        default="medical_notes_embeddings",
        description="Vector collection name (NotesDigest compatibility)"
    )
    EMBEDDINGS_MODEL: str = Field(
        default="amazon.titan-embed-text-v2:0", 
        description="Embeddings model ID for Amazon Titan"
    )
    EMBEDDINGS_CHUNK_SIZE: int = Field(default=2000, description="Text chunk size for embeddings")
    EMBEDDINGS_CHUNK_OVERLAP: int = Field(default=300, description="Text chunk overlap for embeddings")
    EMBEDDINGS_MAX_RETRIES: int = Field(default=3, description="Max retries for embeddings")
    EMBEDDINGS_RETRY_DELAY: float = Field(default=1.0, description="Retry delay for embeddings")
    ENABLE_EMBEDDINGS_PROCESSING: bool = Field(default=True, description="Enable embeddings processing")
    ENABLE_DATA_FLATTENING: bool = Field(default=True, description="Enable data flattening")
    
    # ===========================================
    # API Configuration
    # ===========================================
    CORS_ORIGINS: str = Field(default="*", description="Allowed CORS origins (comma-separated)")
    MAPPING_INDEX: str = Field(default="chatbotconfiguration_data", description="Index for user mapping")
    
    # NotesDigest API Configuration
    API_BASE_URL: Optional[str] = Field(default=None, description="API base URL for NotesDigest")
    API_NOTE_HEADER_TOKEN: Optional[str] = Field(default=None, description="API note header token")
    N_PREVIOUS_VISITS: int = Field(default=1, description="Number of previous visits to include")
    
    # Processing Configuration
    MAX_CONCURRENT_NOTES: int = Field(default=10, description="Max concurrent notes processing")
    MAX_QUEUE_SIZE: int = Field(default=20, description="Max queue size for processing")
    NOTE_PROCESSING_TIMEOUT: int = Field(default=1800, description="Note processing timeout in seconds")
    BEDROCK_RATE_LIMIT_RPS: int = Field(default=30, description="Bedrock rate limit RPS")
    
    @property
    def model_id(self) -> str:
        """Get the actual model ID based on MODEL setting."""
        model_mapping = {
            "CLAUDE_SONNET_3_5": self.CLAUDE_SONNET_3_5,
            "CLAUDE_HAIKU_4_5": self.CLAUDE_HAIKU_4_5,
            "CLAUDE_HAIKU_3_5": self.CLAUDE_HAIKU_3_5,
            "CLAUDE_OPUS_4_1": self.CLAUDE_OPUS_4_1,
            "MISTRAL_7_B": self.MISTRAL_7_B,
        }
        return model_mapping.get(self.MODEL, self.CLAUDE_HAIKU_4_5)
    
    @property
    def cors_origins_list(self) -> list:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def es_auth(self) -> Optional[str]:
        """Get base64 encoded auth string for Elasticsearch."""
        if self.ES_USER and self.ES_PASSWORD:
            import base64
            credentials = f"{self.ES_USER}:{self.ES_PASSWORD}"
            return base64.b64encode(credentials.encode()).decode()
        return None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid re-reading environment on every call.
    """
    return Settings()


# Convenience instance for direct imports
settings = get_settings()
