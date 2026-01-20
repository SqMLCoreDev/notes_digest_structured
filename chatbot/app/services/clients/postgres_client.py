"""
PostgreSQL Client - Reusable PostgreSQL Connection Management

Centralized PostgreSQL client for services that need direct database access:
- Conversation history (cache service)
- Health checks and monitoring
- Database statistics and administration
- Custom queries and operations

NOTE: This client is NOT used by:
- PGVector operations (uses LangChain's PGVector with its own connections)
- Vector embeddings (managed by LangChain)

Features:
- Connection pooling for performance
- Automatic reconnection on failures
- Query utilities and error handling
- Singleton pattern for shared connections
"""

from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import asyncpg
try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg package not installed. PostgreSQL client disabled.")


class PostgreSQLClient:
    """
    Reusable PostgreSQL client with connection pooling.
    
    Used by services that need direct PostgreSQL access:
    - Cache service (conversation history)
    - Health checks and monitoring
    - Database administration
    - Custom queries and statistics
    
    NOT used by:
    - PGVector operations (LangChain manages its own connections)
    - Vector embeddings (handled by LangChain's PGVector)
    """
    
    def __init__(
        self,
        connection_string: str = None,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        command_timeout: int = 30
    ):
        """
        Initialize PostgreSQL client.
        
        Args:
            connection_string: PostgreSQL connection string
            min_pool_size: Minimum connections in pool
            max_pool_size: Maximum connections in pool
            command_timeout: Command timeout in seconds
        """
        self.connection_string = connection_string or settings.POSTGRES_CONNECTION
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.command_timeout = command_timeout
        self._pool: Optional[asyncpg.Pool] = None
        self._connection_info = None
        
        if not ASYNCPG_AVAILABLE:
            raise ImportError("asyncpg package required for PostgreSQL client")
        
        if not self.connection_string:
            raise ValueError("PostgreSQL connection string is required")
        
        # Parse connection string for logging
        parsed = urlparse(self.connection_string)
        self._connection_info = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username
        }
    
    async def get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            await self._create_pool()
        return self._pool
    
    async def _create_pool(self) -> None:
        """Create connection pool."""
        try:
            parsed = urlparse(self.connection_string)
            
            self._pool = await asyncpg.create_pool(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=self.command_timeout
            )
            
            logger.info(f"✅ PostgreSQL pool created: {parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL pool: {e}")
            raise
    
    async def execute_query(
        self,
        query: str,
        *args,
        fetch_mode: str = 'all'
    ) -> Union[List[asyncpg.Record], asyncpg.Record, Any, None]:
        """
        Execute a query with automatic connection management.
        
        Args:
            query: SQL query string
            *args: Query parameters
            fetch_mode: 'all', 'one', 'val', or 'none'
            
        Returns:
            Query results based on fetch_mode
        """
        try:
            pool = await self.get_pool()
            
            async with pool.acquire() as conn:
                if fetch_mode == 'all':
                    return await conn.fetch(query, *args)
                elif fetch_mode == 'one':
                    return await conn.fetchrow(query, *args)
                elif fetch_mode == 'val':
                    return await conn.fetchval(query, *args)
                elif fetch_mode == 'none':
                    await conn.execute(query, *args)
                    return None
                else:
                    raise ValueError(f"Invalid fetch_mode: {fetch_mode}")
                    
        except Exception as e:
            logger.error(f"PostgreSQL query error: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Args: {args}")
            raise
    
    async def test_connection(self) -> bool:
        """
        Test PostgreSQL connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = await self.execute_query("SELECT 1 as test", fetch_mode='val')
            return result == 1
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table information
        """
        try:
            # Get table existence and row count
            exists_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
            """
            
            table_exists = await self.execute_query(exists_query, table_name, fetch_mode='val')
            
            if not table_exists:
                return {
                    'table_name': table_name,
                    'exists': False,
                    'row_count': 0,
                    'columns': []
                }
            
            # Get row count
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            row_count = await self.execute_query(count_query, fetch_mode='val')
            
            # Get column information
            columns_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
            """
            
            columns = await self.execute_query(columns_query, table_name, fetch_mode='all')
            column_info = [
                {
                    'name': col['column_name'],
                    'type': col['data_type'],
                    'nullable': col['is_nullable'] == 'YES'
                }
                for col in columns
            ]
            
            return {
                'table_name': table_name,
                'exists': True,
                'row_count': row_count,
                'columns': column_info
            }
            
        except Exception as e:
            logger.error(f"Error getting table info for {table_name}: {e}")
            return {
                'table_name': table_name,
                'exists': False,
                'error': str(e)
            }
    
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("🔌 PostgreSQL connection pool closed")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for logging/debugging."""
        return {
            'connection_info': self._connection_info,
            'pool_config': {
                'min_size': self.min_pool_size,
                'max_size': self.max_pool_size,
                'command_timeout': self.command_timeout
            },
            'available': ASYNCPG_AVAILABLE,
            'connected': self._pool is not None
        }


# Singleton instance
_postgres_client: Optional[PostgreSQLClient] = None


def get_postgres_client(
    connection_string: str = None,
    min_pool_size: int = 2,
    max_pool_size: int = 10,
    command_timeout: int = 30
) -> PostgreSQLClient:
    """
    Get PostgreSQL client singleton.
    
    Args:
        connection_string: PostgreSQL connection string
        min_pool_size: Minimum connections in pool
        max_pool_size: Maximum connections in pool
        command_timeout: Command timeout in seconds
        
    Returns:
        PostgreSQLClient instance
    """
    global _postgres_client
    
    if _postgres_client is None:
        _postgres_client = PostgreSQLClient(
            connection_string=connection_string,
            min_pool_size=min_pool_size,
            max_pool_size=max_pool_size,
            command_timeout=command_timeout
        )
    
    return _postgres_client


async def test_postgres_connection(connection_string: str = None) -> bool:
    """
    Test PostgreSQL connection without creating singleton.
    
    Args:
        connection_string: PostgreSQL connection string
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        client = PostgreSQLClient(connection_string=connection_string)
        result = await client.test_connection()
        await client.close()
        return result
    except Exception as e:
        logger.error(f"PostgreSQL connection test failed: {e}")
        return False