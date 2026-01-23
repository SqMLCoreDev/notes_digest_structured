"""
Configuration additions for PostgreSQL cache backend

Add these settings to your existing config.py or use as reference
"""

from pydantic import Field
from typing import Optional

# Add these fields to your existing Settings class:

class PostgresCacheSettings:
    """Additional settings for PostgreSQL cache backend"""
    
    # Cache Configuration (modify existing)
    CACHE_TYPE: str = Field(default="postgres", description="Cache type: memory, redis, postgres")
    
    # PostgreSQL Cache Settings (new)
    POSTGRES_CACHE_TABLE: str = Field(
        default="chatbot_conversation_cache", 
        description="Table name for conversation cache"
    )
    POSTGRES_CACHE_TTL: int = Field(
        default=3600, 
        description="Cache TTL in seconds for PostgreSQL backend"
    )
    POSTGRES_CACHE_MAX_ENTRIES: int = Field(
        default=10, 
        description="Max cached responses per session in PostgreSQL"
    )
    
    # Reuse existing POSTGRES_CONNECTION for cache
    # POSTGRES_CONNECTION is already defined in your config.py

# Environment variables to add to .env:
"""
# PostgreSQL Cache Configuration
CACHE_TYPE=postgres
POSTGRES_CACHE_TABLE=chatbot_conversation_cache
POSTGRES_CACHE_TTL=3600
POSTGRES_CACHE_MAX_ENTRIES=10

# Uses existing POSTGRES_CONNECTION for database access
"""