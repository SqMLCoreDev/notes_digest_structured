"""
Hybrid Cache Service - PostgreSQL Primary with In-Memory Fallback

This is the main cache service that:
1. Uses PostgreSQL for existing conversations (read-only)
2. Uses in-memory cache for new conversations and current session
3. No Redis dependency
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.services.cache_service import InMemoryCacheBackend
from app.services.postgres_cache_backend_improved import create_improved_postgres_cache_backend, ASYNCPG_AVAILABLE

logger = get_logger(__name__)


class HybridCacheService:
    """
    Hybrid cache service that uses PostgreSQL for existing conversations
    and in-memory cache for new conversations.
    
    Flow:
    1. get_responses(): Try PostgreSQL first, fallback to memory
    2. save_response(): Always save to memory (PostgreSQL is read-only)
    3. clear_session(): Clear memory cache only
    """
    
    def __init__(self):
        # Always create in-memory cache for fallback and new conversations
        self.memory_cache = InMemoryCacheBackend(
            max_entries_per_session=30
        )
        
        # Create PostgreSQL backend if available (read-only)
        self.postgres_backend = None
        if ASYNCPG_AVAILABLE and settings.POSTGRES_CONNECTION:
            try:
                self.postgres_backend = create_improved_postgres_cache_backend(
                    connection_string=settings.POSTGRES_CONNECTION,
                    max_entries_per_session=30,
                    table_name="chatbot_messages"
                )
                logger.info("Hybrid cache initialized: PostgreSQL (read) + In-Memory (read/write)")
            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL backend: {e}. Using memory only.")
        else:
            logger.info("PostgreSQL not available. Using in-memory cache only.")
    
    async def save_response(
        self,
        session_id: str,
        query: str,
        response_text: str,
        used_indices: List[str]
    ) -> None:
        """
        Save a response to in-memory cache.
        
        Note: PostgreSQL is read-only (populated by another process).
        All new responses go to memory cache for the current session.
        """
        entry = {
            'query': query,
            'response': response_text,
            'used_indices': used_indices,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Always save to memory cache for current session
        await self.memory_cache.add(session_id, entry)
        logger.debug(f"Saved response to memory cache for session {session_id}")
    
    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history with hybrid approach:
        1. Try PostgreSQL first (existing conversations)
        2. If not found, try in-memory cache (new conversations)
        3. Return empty list if neither has data
        """
        # Try PostgreSQL first if available
        if self.postgres_backend:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    logger.debug(f"Found {len(postgres_responses)} responses in PostgreSQL for session {session_id}")
                    return postgres_responses
            except Exception as e:
                logger.error(f"PostgreSQL get error: {e}")
        
        # Fallback to in-memory cache
        memory_responses = await self.memory_cache.get(session_id)
        if memory_responses:
            logger.debug(f"Found {len(memory_responses)} responses in memory cache for session {session_id}")
            return memory_responses
        
        # No responses found in either cache
        logger.debug(f"No conversation history found for session {session_id}")
        return []
    
    async def clear_session(self, session_id: str) -> None:
        """
        Clear session from in-memory cache only.
        
        Note: PostgreSQL is read-only and managed by another process.
        This only clears the current session's memory cache.
        """
        await self.memory_cache.clear(session_id)
        logger.debug(f"Cleared memory cache for session {session_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics from both backends."""
        memory_stats = await self.memory_cache.get_stats()
        
        stats = {
            'cache_type': 'hybrid',
            'memory_cache': memory_stats,
            'postgres_available': self.postgres_backend is not None
        }
        
        if self.postgres_backend:
            try:
                postgres_stats = await self.postgres_backend.get_stats()
                stats['postgres_cache'] = postgres_stats
            except Exception as e:
                stats['postgres_cache'] = {'error': str(e)}
        
        return stats
    
    def responses_to_conversation_history(
        self,
        responses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert cached responses to conversation history format.
        Works with responses from either PostgreSQL or memory cache.
        """
        return [
            {
                'question': resp.get('query', ''),
                'answer': resp.get('response', ''),
                'timestamp': resp.get('timestamp', '')
            }
            for resp in responses
        ]


# Singleton instance
_cache_service: Optional[HybridCacheService] = None


def get_cache_service() -> HybridCacheService:
    """Get the hybrid cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = HybridCacheService()
    return _cache_service