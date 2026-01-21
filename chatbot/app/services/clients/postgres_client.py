"""
Improved PostgreSQL Cache Backend for Chatbot Memory

This version handles edge cases better and ensures proper question-answer pairing.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.core.config import settings


logger = get_logger(__name__)

# Try to import asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg package not installed. PostgreSQL caching disabled.")




class PostgresClient:
    """
    Generic PostgreSQL client for handling database connections and queries.
    """
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or settings.POSTGRES_CONNECTION
        self._pool: Optional[asyncpg.Pool] = None
    
    async def get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            # Parse connection string to get components
            parsed = urlparse(self.connection_string)
            
            self._pool = await asyncpg.create_pool(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                min_size=2,
                max_size=10
            )
            logger.info("Initialized generic PostgreSQL connection pool")
        
        return self._pool
    
    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Execute a query and return a list of records."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)
            
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Execute a query and return a single record."""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed PostgreSQL client connection pool")


# Singleton instance
_postgres_client: Optional[PostgresClient] = None

def get_postgres_client(connection_string: str = None) -> PostgresClient:
    """Get the PostgreSQL client singleton."""
    global _postgres_client
    if _postgres_client is None:
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg package required for PostgreSQL client")
        _postgres_client = PostgresClient(connection_string)
    return _postgres_client

