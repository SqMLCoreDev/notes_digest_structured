"""
PostgreSQL Memory Backend for Chatbot

Handles reading conversation history from the existing chatbot_messages table.
Uses the generic PostgresClient for database access.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.logging import get_logger
from app.services.cache_service import CacheBackend
from app.services.clients.postgres_client import PostgresClient

logger = get_logger(__name__)


class PostgresMemoryBackend(CacheBackend):
    """
    PostgreSQL backend for chatbot memory.
    Implements CacheBackend interface but specialized for retrieving Q&A pairs.
    """
    
    def __init__(
        self,
        postgres_client: PostgresClient,
        max_entries_per_session: int = 30,
        table_name: str = "chatbot_messages"
    ):
        self.client = postgres_client
        self.max_entries = max_entries_per_session
        self.table_name = table_name
    
    async def get(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation history from assistant rows only.
        Each assistant row contains both query and response columns.
        
        Note: The database conversation_id is bigint, but we receive string session IDs.
        We'll try to convert to int, and if that fails, we'll return None (no history).
        """
        try:
            # The database conversation_id is bigint, so we need to convert string to int
            try:
                conv_id_param = int(conversation_id)
                logger.debug(f"Converted session_id '{conversation_id}' to conversation_id {conv_id_param}")
            except ValueError:
                # If session_id is not numeric (e.g., "test-session-123"), 
                # we can't find it in the database since conversation_id is bigint
                logger.debug(f"Session_id '{conversation_id}' is not numeric, cannot query bigint conversation_id")
                return None
            
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
            
            rows = await self.client.fetch(query, conv_id_param, self.max_entries)
            
            if not rows:
                logger.debug(f"No conversation history found for conversation_id: {conv_id_param}")
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
            
            logger.info(f"✅ Retrieved {len(qa_pairs)} Q&A pairs from PostgreSQL for conversation_id {conv_id_param}")
            return qa_pairs
            
        except Exception as e:
            logger.error(f"PostgreSQL Memory get error for session_id '{conversation_id}': {e}")
            return None
    
    async def add(self, conversation_id: str, entry: Dict[str, Any]) -> None:
        """
        Note: This method is not used for reading from existing table.
        The existing table is populated by another process.
        This is a no-op to maintain interface compatibility.
        """
        pass
    
    async def clear(self, conversation_id: str) -> None:
        """
        Note: This method is not used for reading from existing table.
        The existing table is managed by another process.
        """
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics from existing chatbot_messages table."""
        try:
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
            
            row = await self.client.fetchrow(stats_query)
            
            if not row:
                return {'error': 'No stats available'}

            return {
                'backend': 'postgresql_memory',
                'table_name': self.table_name,
                'total_conversations': row['total_conversations'] or 0,
                'total_qa_pairs': row['total_qa_pairs'] or 0,
                'total_user_messages': row['total_user_messages'] or 0,
                'estimated_size_kb': round((row['total_size_bytes'] or 0) / 1024, 2),
                'max_qa_pairs_per_session': self.max_entries,
                'latest_message': row['latest_message'].isoformat() if row['latest_message'] else None,
                'earliest_message': row['earliest_message'].isoformat() if row['earliest_message'] else None
            }
                
        except Exception as e:
            logger.error(f"PostgreSQL Memory stats error: {e}")
            return {'backend': 'postgresql_memory', 'error': str(e)}
