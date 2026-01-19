"""
Enhanced PostgreSQL Cache Backend with Automatic Summarization

Features:
1. Reads existing conversations from chatbot_messages table
2. Automatically summarizes when conversations exceed 30 messages
3. Stores summaries back to PostgreSQL for persistence
4. Maintains context while managing memory usage
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.core.config import settings
from app.services.cache_service import CacheBackend
from app.services.conversation_summarizer import get_conversation_summarizer

logger = get_logger(__name__)

# Try to import asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg package not installed. PostgreSQL caching disabled.")


class PostgresCacheBackendWithSummary(CacheBackend):
    """
    Enhanced PostgreSQL cache backend with automatic conversation summarization.
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
        self.summarizer = get_conversation_summarizer()
    
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
            
            logger.info(f"Connected to PostgreSQL table with summarization: {self.table_name}")
        
        return self._pool
    
    async def get(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation history with automatic summarization.
        
        If conversation > 30 messages, automatically summarizes and returns
        summary + recent messages.
        """
        try:
            pool = await self._get_pool()
            
            # Get all messages for this conversation, ordered by id
            query = f"""
            SELECT role, query, response, created_at, id, parent_id, meta
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
                
                # Build complete conversation pairs
                qa_pairs = self._build_qa_pairs(rows)
                
                if not qa_pairs:
                    return None
                
                # Check if summarization is needed
                if await self.summarizer.should_summarize(qa_pairs):
                    logger.info(f"Conversation {conversation_id} has {len(qa_pairs)} messages, summarizing...")
                    
                    # Summarize the conversation
                    summarized_conversation, summary_entry = await self.summarizer.summarize_conversation(qa_pairs)
                    
                    # Store summary in PostgreSQL for persistence
                    if summary_entry:
                        await self._store_summary(conversation_id, summary_entry)
                    
                    logger.info(f"Summarized conversation {conversation_id}: {len(qa_pairs)} → {len(summarized_conversation)} messages")
                    return summarized_conversation
                
                # No summarization needed
                logger.debug(f"Retrieved {len(qa_pairs)} Q&A pairs from {self.table_name} for conversation {conversation_id}")
                return qa_pairs
                
        except Exception as e:
            logger.error(f"PostgreSQL get error: {e}")
            return None
    
    def _build_qa_pairs(self, rows: List[asyncpg.Record]) -> List[Dict[str, Any]]:
        """
        Build question-answer pairs from database rows.
        Handles existing summaries and regular messages.
        """
        qa_pairs = []
        pending_question = None
        
        for row in rows:
            # Check if this is an existing summary
            meta = row.get('meta')
            if meta and isinstance(meta, (str, dict)):
                try:
                    if isinstance(meta, str):
                        meta_dict = json.loads(meta)
                    else:
                        meta_dict = meta
                    
                    if meta_dict.get('is_summary'):
                        # This is an existing summary
                        qa_pairs.append({
                            'query': '[CONVERSATION SUMMARY]',
                            'response': row['response'] or '',
                            'used_indices': [],
                            'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                            'message_count': meta_dict.get('message_count', 10),
                            'is_summary': True
                        })
                        continue
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Regular message processing
            if row['role'] == 'user':
                # If we have a pending question without an answer, skip it
                if pending_question:
                    logger.debug(f"Skipping orphaned question: {pending_question['query'][:50]}...")
                
                # Store new question
                pending_question = {
                    'query': row['query'] or '',
                    'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                    'id': row['id']
                }
                
            elif row['role'] == 'assistant':
                if pending_question:
                    # Complete the Q&A pair
                    qa_pairs.append({
                        'query': pending_question['query'],
                        'response': row['response'] or '',
                        'used_indices': [],  # Not stored in existing table
                        'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                        'question_id': pending_question['id'],
                        'response_id': row['id']
                    })
                    pending_question = None
                else:
                    # Orphaned response - try to find the question
                    question_text = self._find_question_for_response(row, rows)
                    if question_text:
                        qa_pairs.append({
                            'query': question_text,
                            'response': row['response'] or '',
                            'used_indices': [],
                            'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                            'question_id': None,
                            'response_id': row['id']
                        })
                    else:
                        logger.debug(f"Skipping orphaned response: {row['response'][:50] if row['response'] else 'None'}...")
        
        return qa_pairs
    
    def _find_question_for_response(self, response_row: asyncpg.Record, all_rows: List[asyncpg.Record]) -> Optional[str]:
        """Try to find the question for an orphaned response."""
        # Method 1: Use parent_id if available
        if response_row['parent_id'] and response_row['parent_id'] != 0:
            for row in all_rows:
                if row['id'] == response_row['parent_id'] and row['role'] == 'user':
                    return row['query'] or ''
        
        # Method 2: Find the most recent user message before this response
        response_id = response_row['id']
        for i in range(len(all_rows) - 1, -1, -1):
            row = all_rows[i]
            if row['id'] < response_id and row['role'] == 'user':
                return row['query'] or ''
        
        # Method 3: Use the query field from the response row itself
        if response_row['query']:
            return response_row['query']
        
        return None
    
    async def _store_summary(self, conversation_id: str, summary_entry: Dict[str, Any]) -> None:
        """
        Store conversation summary in PostgreSQL for persistence.
        """
        try:
            pool = await self._get_pool()
            
            # Create meta data for the summary
            meta_data = {
                'is_summary': True,
                'message_count': summary_entry.get('message_count', 0),
                'created_by': 'auto_summarizer',
                'summary_timestamp': summary_entry.get('timestamp')
            }
            
            insert_query = f"""
            INSERT INTO {self.table_name} 
            (conversation_id, parent_id, role, query, response, meta, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            """
            
            async with pool.acquire() as conn:
                await conn.execute(
                    insert_query,
                    conversation_id,
                    0,  # parent_id
                    'assistant',  # role
                    '[CONVERSATION SUMMARY]',  # query
                    summary_entry['response'],  # response (the summary text)
                    json.dumps(meta_data)  # meta
                )
                
                logger.info(f"Stored conversation summary for {conversation_id} in PostgreSQL")
                
        except Exception as e:
            logger.error(f"Failed to store summary in PostgreSQL: {e}")
    
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
        """Get cache statistics including summarization info."""
        try:
            pool = await self._get_pool()
            
            stats_query = f"""
            SELECT 
                COUNT(DISTINCT conversation_id) as total_conversations,
                COUNT(*) FILTER (WHERE role = 'assistant') as total_responses,
                COUNT(*) FILTER (WHERE role = 'user') as total_questions,
                COUNT(*) FILTER (WHERE meta::text LIKE '%is_summary%') as total_summaries,
                SUM(LENGTH(COALESCE(query, '') || COALESCE(response, ''))) as total_size_bytes,
                MAX(created_at) as latest_message,
                MIN(created_at) as earliest_message
            FROM {self.table_name}
            WHERE deleted_at IS NULL
            """
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(stats_query)
                
                return {
                    'backend': 'postgresql_with_summarization',
                    'connection': self.connection_string.split('@')[-1] if '@' in self.connection_string else 'localhost',
                    'table_name': self.table_name,
                    'total_conversations': row['total_conversations'] or 0,
                    'total_responses': row['total_responses'] or 0,
                    'total_questions': row['total_questions'] or 0,
                    'total_summaries': row['total_summaries'] or 0,
                    'estimated_size_kb': round((row['total_size_bytes'] or 0) / 1024, 2),
                    'max_qa_pairs_per_session': self.max_entries,
                    'latest_message': row['latest_message'].isoformat() if row['latest_message'] else None,
                    'earliest_message': row['earliest_message'].isoformat() if row['earliest_message'] else None,
                    'summarization_enabled': True,
                    'note': 'Automatically summarizes conversations > 30 messages'
                }
                
        except Exception as e:
            logger.error(f"PostgreSQL stats error: {e}")
            return {'backend': 'postgresql_with_summarization', 'error': str(e)}
    
    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed PostgreSQL cache connection pool")


# Factory function to create enhanced PostgreSQL cache backend
def create_postgres_cache_backend_with_summary(
    connection_string: str = None,
    max_entries_per_session: int = 30,
    ttl_seconds: int = 3600,
    table_name: str = "chatbot_messages"
) -> PostgresCacheBackendWithSummary:
    """
    Create an enhanced PostgreSQL cache backend with automatic summarization.
    
    Features:
    - Reads from existing chatbot_messages table
    - Automatically summarizes conversations > 30 messages
    - Stores summaries back to PostgreSQL
    - Maintains context while managing memory
    
    Args:
        connection_string: PostgreSQL connection string
        max_entries_per_session: Trigger summarization threshold (default: 30)
        ttl_seconds: Not used for existing table (kept for compatibility)
        table_name: Name of the existing table (default: "chatbot_messages")
    
    Returns:
        PostgresCacheBackendWithSummary instance
    """
    if not ASYNCPG_AVAILABLE:
        raise ImportError("asyncpg package required for PostgreSQL cache backend")
    
    return PostgresCacheBackendWithSummary(
        connection_string=connection_string,
        max_entries_per_session=max_entries_per_session,
        ttl_seconds=ttl_seconds,
        table_name=table_name
    )