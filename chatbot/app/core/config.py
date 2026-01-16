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
    CLAUDE_HAIKU_4_5: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1",
        description="Claude Haiku 4.5 model ID"
    )
    MODEL: str = Field(default="CLAUDE_HAIKU_4_5", description="Model name to use")
    MAX_TOKENS: int = Field(default=100000, description="Maximum tokens for model response")
    
    # ===========================================
    # Elasticsearch Configuration
    # ===========================================
    ES_URL: Optional[str] = Field(default=None, description="Elasticsearch cluster URL")
    ES_USER: Optional[str] = Field(default=None, description="Elasticsearch username")
    ES_PASSWORD: Optional[str] = Field(default=None, description="Elasticsearch password")
    
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
        default="postgresql+psycopg://teleqcuser:LqXlObT4t4Y0g8H@3.21.212.7:5432/tiatelemdqc", 
        description="PostgreSQL connection string for PGVector (e.g., postgresql://user:pass@host:5432/db)"
    )
    COLLECTION_NAME: str = Field(
        default="tia_qa",
        description="Vector collection name for storing embeddings"
    )
    EMBEDDINGS_MODEL: str = Field(
        default="amazon.titan-embed-text-v2:0", 
        description="Embeddings model ID for Amazon Titan"
    )
    
    # ===========================================
    # API Configuration
    # ===========================================
    CORS_ORIGINS: str = Field(default="*", description="Allowed CORS origins (comma-separated)")
    MAPPING_INDEX: str = Field(default="chatbotconfiguration_data", description="Index for user mapping")
    
    @property
    def model_id(self) -> str:
        """Get the actual model ID based on MODEL setting."""
        model_mapping = {
            "CLAUDE_SONNET_3_5": self.CLAUDE_SONNET_3_5,
            "CLAUDE_HAIKU_4_5": self.CLAUDE_HAIKU_4_5,
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
