"""
PostgreSQL Service - Conversation History Management

Specialized service for chatbot conversation history operations.
Uses the reusable PostgreSQL client for connection management.

Features:
- Conversation history retrieval from chatbot_messages table
- Database statistics and monitoring
- Built on top of reusable PostgreSQL client
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.services.clients.postgres_client import get_postgres_client, PostgreSQLClient, ASYNCPG_AVAILABLE

logger = get_logger(__name__)


class PostgreSQLService:
    """
    Specialized PostgreSQL service for chatbot conversations.
    Uses the reusable PostgreSQL client for connection management.
    """
    
    def __init__(
        self,
        postgres_client: PostgreSQLClient = None,
        max_entries_per_session: int = 30,
        table_name: str = "chatbot_messages"
    ):
        """
        Initialize PostgreSQL service.
        
        Args:
            postgres_client: PostgreSQL client instance (uses singleton if None)
            max_entries_per_session: Maximum entries per session
            table_name: Database table name
        """
        self.postgres_client = postgres_client or get_postgres_client()
        self.max_entries = max_entries_per_session
        self.table_name = table_name
        
        logger.info(f"✅ PostgreSQL service initialized with table: {table_name}")
    
    async def get_conversation_history(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get conversation history from chatbot_messages table.
        Reads from assistant rows only (contains both query and response).
        
        Args:
            conversation_id: Conversation ID (string or int)
            
        Returns:
            List of conversation messages or None if not found
        """
        try:
            # Convert conversation_id to int if it's numeric
            try:
                conv_id_param = int(conversation_id)
            except (ValueError, TypeError):
                conv_id_param = conversation_id
            
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
            
            rows = await self.postgres_client.execute_query(
                query, conv_id_param, self.max_entries, fetch_mode='all'
            )
            
            if not rows:
                return None
            
            messages = []
            for row in rows:
                messages.append({
                    'query': row['query'] or '',
                    'response': row['response'] or '',
                    'used_indices': [],  # Not stored in existing table
                    'timestamp': row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat(),
                    'message_id': row['id']
                })
            
            logger.debug(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages
                
        except Exception as e:
            logger.error(f"PostgreSQL get error: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            query = f"""
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
            
            row = await self.postgres_client.execute_query(query, fetch_mode='one')
            connection_info = self.postgres_client.get_connection_info()
            
            return {
                'service': 'postgresql_conversation_history',
                'table_name': self.table_name,
                'total_conversations': row['total_conversations'] or 0,
                'total_qa_pairs': row['total_qa_pairs'] or 0,
                'total_user_messages': row['total_user_messages'] or 0,
                'estimated_size_kb': round((row['total_size_bytes'] or 0) / 1024, 2),
                'max_entries_per_session': self.max_entries,
                'latest_message': row['latest_message'].isoformat() if row['latest_message'] else None,
                'earliest_message': row['earliest_message'].isoformat() if row['earliest_message'] else None,
                'connection_host': connection_info.get('connection_info', {}).get('host', 'unknown'),
                'using_shared_client': True
            }
                
        except Exception as e:
            logger.error(f"PostgreSQL stats error: {e}")
            return {'service': 'postgresql_conversation_history', 'error': str(e)}
    
    async def test_connection(self) -> bool:
        """
        Test PostgreSQL connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        return await self.postgres_client.test_connection()
    
    async def get_table_info(self) -> Dict[str, Any]:
        """
        Get information about the chatbot_messages table.
        
        Returns:
            Dictionary with table information
        """
        return await self.postgres_client.get_table_info(self.table_name)
    
    async def close(self) -> None:
        """Close PostgreSQL connection (handled by shared client)."""
        # Connection is managed by the shared client
        logger.debug("PostgreSQL service closed (connection managed by shared client)")


# Singleton instance
_postgres_service: Optional[PostgreSQLService] = None


def get_postgres_service(
    connection_string: str = None,
    max_entries_per_session: int = 30,
    table_name: str = "chatbot_messages"
) -> PostgreSQLService:
    """
    Get PostgreSQL service singleton.
    
    Args:
        connection_string: PostgreSQL connection string (passed to client)
        max_entries_per_session: Maximum entries per session
        table_name: Database table name
    
    Returns:
        PostgreSQLService instance
    """
    global _postgres_service
    
    if _postgres_service is None:
        # Get or create the shared PostgreSQL client
        postgres_client = get_postgres_client(connection_string=connection_string)
        
        _postgres_service = PostgreSQLService(
            postgres_client=postgres_client,
            max_entries_per_session=max_entries_per_session,
            table_name=table_name
        )
    
    return _postgres_service