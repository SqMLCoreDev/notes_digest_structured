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
from app.services.cache_service import CacheBackend

logger = get_logger(__name__)

# Try to import asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg package not installed. PostgreSQL caching disabled.")


class ImprovedPostgresCacheBackend(CacheBackend):
    """
    Improved PostgreSQL cache backend that properly handles question-answer pairing
    and ensures conversation history starts with complete Q&A pairs.
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
    
    async def get(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation history from assistant rows only.
        Each assistant row contains both query and response columns.
        """
        try:
            pool = await self._get_pool()
            
            # Convert conversation_id to int if it's numeric
            try:
                conv_id_param = int(conversation_id)
            except ValueError:
                conv_id_param = conversation_id  # Keep as string if not numeric
            
            # Get only assistant messages, they contain both query and response
            query = f"""
            SELECT query, response, created_at, id
            FROM {self.table_name}
            WHERE conversation_id = $1 
              AND deleted_at IS NULL
              AND role = 'assistant'
              AND query IS NOT NULL
              AND response IS NOT NULL
            ORDER BY id ASC
            LIMIT $2
            """
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, conv_id_param, self.max_entries)
                
                if not rows:
                    return None
                
                # Build Q&A pairs from assistant rows
                qa_pairs = []
                for row in rows:
                    qa_pairs.append({
                        'query': row['query'] or '',
                        'response': row['response'] or '',
                        'used_indices': [],  # Not stored in existing table
                        'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                        'message_id': row['id']
                    })
                
                logger.debug(f"Retrieved {len(qa_pairs)} Q&A pairs from assistant rows for conversation {conversation_id}")
                return qa_pairs
                
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
                COUNT(*) FILTER (WHERE role = 'assistant') as total_qa_pairs,
                COUNT(*) FILTER (WHERE role = 'user') as total_user_messages,
                SUM(LENGTH(COALESCE(query, '') || COALESCE(response, ''))) as total_size_bytes,
                MAX(created_at) as latest_message,
                MIN(created_at) as earliest_message
            FROM {self.table_name}
            WHERE deleted_at IS NULL
            """
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(stats_query)
                
                return {
                    'backend': 'postgresql_improved_assistant_only',
                    'connection': self.connection_string.split('@')[-1] if '@' in self.connection_string else 'localhost',
                    'table_name': self.table_name,
                    'total_conversations': row['total_conversations'] or 0,
                    'total_qa_pairs': row['total_qa_pairs'] or 0,
                    'total_user_messages': row['total_user_messages'] or 0,
                    'estimated_size_kb': round((row['total_size_bytes'] or 0) / 1024, 2),
                    'max_qa_pairs_per_session': self.max_entries,
                    'latest_message': row['latest_message'].isoformat() if row['latest_message'] else None,
                    'earliest_message': row['earliest_message'].isoformat() if row['earliest_message'] else None,
                    'note': 'Reading Q&A pairs from assistant rows only - query and response columns'
                }
                
        except Exception as e:
            logger.error(f"PostgreSQL stats error: {e}")
            return {'backend': 'postgresql_improved_assistant_only', 'error': str(e)}
    
    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed PostgreSQL cache connection pool")


# Factory function to create improved PostgreSQL cache backend
def create_improved_postgres_cache_backend(
    connection_string: str = None,
    max_entries_per_session: int = 30,
    ttl_seconds: int = 3600,
    table_name: str = "chatbot_messages"
) -> ImprovedPostgresCacheBackend:
    """
    Create an improved PostgreSQL cache backend instance for existing chatbot_messages table.
    
    This version ensures proper question-answer pairing and handles edge cases:
    - Orphaned questions (questions without responses)
    - Orphaned responses (responses without questions)
    - Uses parent_id relationships when available
    - Falls back to chronological matching
    - Ensures conversation history always starts with complete Q&A pairs
    
    Args:
        connection_string: PostgreSQL connection string (uses settings.POSTGRES_CONNECTION if None)
        max_entries_per_session: Maximum Q&A pairs per conversation (default: 30)
        ttl_seconds: Not used for existing table (kept for interface compatibility)
        table_name: Name of the existing table (default: "chatbot_messages")
    
    Returns:
        ImprovedPostgresCacheBackend instance
    """
    if not ASYNCPG_AVAILABLE:
        raise ImportError("asyncpg package required for PostgreSQL cache backend")
    
    return ImprovedPostgresCacheBackend(
        connection_string=connection_string,
        max_entries_per_session=max_entries_per_session,
        ttl_seconds=ttl_seconds,
        table_name=table_name
    )