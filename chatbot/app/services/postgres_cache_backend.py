"""
PostgreSQL Cache Backend for Chatbot Memory

Uses existing PostgreSQL connection to store conversation history
in a dedicated table instead of Redis.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.core.config import settings
from app.services.cache_service import CacheBackend

logger = get_logger(__name__)

# Try to import asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg package not installed. PostgreSQL caching disabled.")


class PostgresCacheBackend(CacheBackend):
    """
    PostgreSQL cache backend using existing chatbot_messages table.
    Retrieves conversation history from existing table structure.
    """
    
    def __init__(
        self,
        connection_string: str = None,
        max_entries_per_session: int = 30,
        ttl_seconds: int = 3600,
        table_name: str = "chatbot_messages"
    ):
        self.connection_string = connection_string or settings.POSTGRES_CONNECTION
        self.max_entries = max_entries_per_session
        self.ttl = ttl_seconds
        self.table_name = table_name
        self._pool: Optional[asyncpg.Pool] = None
    
    async def _get_pool(self) -> asyncpg.Pool:
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
            
            logger.info(f"Connected to existing PostgreSQL table: {self.table_name}")
        
        return self._pool
    
    async def _initialize_table(self):
        """Create the conversation cache table if it doesn't exist."""
        pool = await self._get_pool()
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            used_indices JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            INDEX (session_id, created_at),
            INDEX (expires_at)
        );
        
        -- Create index for efficient session queries
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_session_time 
        ON {self.table_name} (session_id, created_at);
        
        -- Create index for cleanup queries
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_expires 
        ON {self.table_name} (expires_at);
        """
        
        async with pool.acquire() as conn:
            await conn.execute(create_table_sql)
            logger.info(f"Initialized PostgreSQL cache table: {self.table_name}")
    
    async def get(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached responses for a conversation from existing chatbot_messages table."""
        try:
            pool = await self._get_pool()
            
            # Get both user and assistant messages, ordered by id to maintain conversation flow
            query = f"""
            SELECT role, query, response, created_at, id, parent_id
            FROM {self.table_name}
            WHERE conversation_id = $1 
              AND deleted_at IS NULL
              AND role IN ('user', 'assistant')
            ORDER BY id ASC
            """
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, conversation_id)
                
                if not rows:
                    return None
                
                # Build conversation pairs (question -> answer)
                conversation_pairs = []
                current_question = None
                
                for row in rows:
                    if row['role'] == 'user':
                        # Store the user question
                        current_question = {
                            'query': row['query'] or '',
                            'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                            'id': row['id']
                        }
                    elif row['role'] == 'assistant' and current_question:
                        # Match assistant response with the previous user question
                        conversation_pairs.append({
                            'query': current_question['query'],
                            'response': row['response'] or '',
                            'used_indices': [],  # Not stored in existing table
                            'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                            'question_id': current_question['id'],
                            'response_id': row['id']
                        })
                        current_question = None  # Reset for next pair
                
                # Get the most recent N conversation pairs (not individual messages)
                recent_pairs = conversation_pairs[-self.max_entries:] if len(conversation_pairs) > self.max_entries else conversation_pairs
                
                logger.debug(f"Retrieved {len(recent_pairs)} conversation pairs from {self.table_name} for conversation {conversation_id}")
                return recent_pairs
                
        except Exception as e:
            logger.error(f"PostgreSQL get error: {e}")
            return None
    
    async def add(self, conversation_id: str, entry: Dict[str, Any]) -> None:
        """
        Note: This method is not used for reading from existing table.
        The existing table is populated by another process.
        This is a no-op to maintain interface compatibility.
        """
        logger.debug(f"Add operation skipped - using existing data in {self.table_name} for conversation {conversation_id}")
        pass
    
    async def clear(self, conversation_id: str) -> None:
        """
        Note: This method is not used for reading from existing table.
        The existing table is managed by another process.
        This is a no-op to maintain interface compatibility.
        """
        logger.debug(f"Clear operation skipped - using existing data in {self.table_name} for conversation {conversation_id}")
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics from existing chatbot_messages table."""
        try:
            pool = await self._get_pool()
            
            stats_query = f"""
            SELECT 
                COUNT(DISTINCT conversation_id) as total_conversations,
                COUNT(*) FILTER (WHERE role = 'assistant') as total_responses,
                COUNT(*) FILTER (WHERE role = 'user') as total_queries,
                SUM(LENGTH(COALESCE(query, '') || COALESCE(response, ''))) as total_size_bytes,
                MAX(created_at) as latest_message,
                MIN(created_at) as earliest_message
            FROM {self.table_name}
            WHERE deleted_at IS NULL
            """
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(stats_query)
                
                return {
                    'backend': 'postgresql_existing',
                    'connection': self.connection_string.split('@')[-1] if '@' in self.connection_string else 'localhost',
                    'table_name': self.table_name,
                    'total_conversations': row['total_conversations'] or 0,
                    'total_responses': row['total_responses'] or 0,
                    'total_queries': row['total_queries'] or 0,
                    'estimated_size_kb': round((row['total_size_bytes'] or 0) / 1024, 2),
                    'max_entries_per_session': self.max_entries,
                    'latest_message': row['latest_message'].isoformat() if row['latest_message'] else None,
                    'earliest_message': row['earliest_message'].isoformat() if row['earliest_message'] else None,
                    'note': 'Reading from existing table - add/clear operations are no-ops'
                }
                
        except Exception as e:
            logger.error(f"PostgreSQL stats error: {e}")
            return {'backend': 'postgresql_existing', 'error': str(e)}
    
    async def _cleanup_expired(self) -> None:
        """Not needed - existing table is managed by another process."""
        pass
    
    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed PostgreSQL cache connection pool")


# Factory function to create PostgreSQL cache backend for existing table
def create_postgres_cache_backend(
    connection_string: str = None,
    max_entries_per_session: int = 30,
    ttl_seconds: int = 3600,
    table_name: str = "chatbot_messages"
) -> PostgresCacheBackend:
    """
    Create a PostgreSQL cache backend instance for existing chatbot_messages table.
    
    Args:
        connection_string: PostgreSQL connection string (uses settings.POSTGRES_CONNECTION if None)
        max_entries_per_session: Maximum cached responses per conversation (default: 30)
        ttl_seconds: Not used for existing table (kept for interface compatibility)
        table_name: Name of the existing table (default: "chatbot_messages")
    
    Returns:
        PostgresCacheBackend instance
    """
    if not ASYNCPG_AVAILABLE:
        raise ImportError("asyncpg package required for PostgreSQL cache backend")
    
    return PostgresCacheBackend(
        connection_string=connection_string,
        max_entries_per_session=max_entries_per_session,
        ttl_seconds=ttl_seconds,
        table_name=table_name
    )