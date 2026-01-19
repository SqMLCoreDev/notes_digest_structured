"""
Performance-Optimized Cache Service - Memory-First with PostgreSQL Warm-Up

Strategy:
1. Memory-first: Check memory cache first (fastest path)
2. PostgreSQL warm-up: Load from DB once, then cache in memory
3. Track loaded sessions to avoid unnecessary DB queries
4. All subsequent requests use fast memory access
"""

from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.services.cache_service import InMemoryCacheBackend
from app.services.postgres_cache_backend_improved import create_improved_postgres_cache_backend, ASYNCPG_AVAILABLE

logger = get_logger(__name__)


class CacheService:
    """
    Performance-optimized cache service that uses memory-first strategy.
    
    Flow:
    1. Check memory first (⚡ fast path)
    2. If not in memory, load from PostgreSQL once
    3. Cache PostgreSQL data in memory for future speed
    4. Track which conversations are loaded to avoid DB queries
    """
    
    def __init__(self):
        # In-memory cache for fast access
        self.memory_cache = InMemoryCacheBackend(
            max_entries_per_session=30
        )
        
        # Track which conversations are already loaded in memory
        self.loaded_sessions: Set[str] = set()
        
        # PostgreSQL backend for initial data loading
        self.postgres_backend = None
        if ASYNCPG_AVAILABLE and settings.POSTGRES_CONNECTION:
            try:
                self.postgres_backend = create_improved_postgres_cache_backend(
                    connection_string=settings.POSTGRES_CONNECTION,
                    max_entries_per_session=30,
                    table_name="chatbot_messages"
                )
                logger.info("Performance cache initialized: Memory-first with PostgreSQL warm-up")
            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL backend: {e}. Using memory only.")
        else:
            logger.info("PostgreSQL not available. Using memory-only cache.")
    
    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history with performance optimization:
        1. ⚡ Fast path: Return from memory if already loaded
        2. 🔄 Warm-up path: Load from PostgreSQL once, cache in memory
        3. 🆕 New conversation: Start with empty memory cache
        """
        
        # ⚡ FAST PATH: Check memory first
        if session_id in self.loaded_sessions:
            memory_responses = await self.memory_cache.get(session_id)
            if memory_responses:
                logger.debug(f"⚡ Fast path: Retrieved {len(memory_responses)} responses from memory for {session_id}")
                return memory_responses
            else:
                # Session was loaded but memory is empty (cleared or new)
                logger.debug(f"⚡ Fast path: Empty memory cache for loaded session {session_id}")
                return []
        
        # 🔄 WARM-UP PATH: Load from PostgreSQL and cache in memory
        if self.postgres_backend:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    logger.debug(f"🔄 Warm-up: Loading {len(postgres_responses)} responses from PostgreSQL for {session_id}")
                    
                    # Cache all responses in memory for future speed
                    for response in postgres_responses:
                        await self.memory_cache.add(session_id, response)
                    
                    # Mark as loaded to use fast path next time
                    self.loaded_sessions.add(session_id)
                    
                    logger.debug(f"🔄 Warm-up complete: {session_id} now cached in memory")
                    return postgres_responses
                else:
                    logger.debug(f"🔄 Warm-up: No data in PostgreSQL for {session_id}")
            except Exception as e:
                logger.error(f"PostgreSQL warm-up error for {session_id}: {e}")
        
        # 🆕 NEW CONVERSATION: Mark as loaded and start with empty cache
        self.loaded_sessions.add(session_id)
        logger.debug(f"🆕 New conversation: {session_id} marked as loaded")
        return []
    
    async def save_response(
        self,
        session_id: str,
        query: str,
        response_text: str,
        used_indices: List[str]
    ) -> None:
        """
        Save response to memory cache (⚡ fast operation).
        
        Note: UI team handles PostgreSQL persistence.
        This only updates the fast memory cache.
        """
        entry = {
            'query': query,
            'response': response_text,
            'used_indices': used_indices,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Always save to memory for fast access
        await self.memory_cache.add(session_id, entry)
        
        # Mark session as loaded (active)
        self.loaded_sessions.add(session_id)
        
        logger.debug(f"⚡ Saved response to memory cache for session {session_id}")
    
    async def clear_session(self, session_id: str) -> None:
        """
        Clear session from memory cache and loaded sessions tracking.
        Next request will warm-up from PostgreSQL again.
        """
        await self.memory_cache.clear(session_id)
        self.loaded_sessions.discard(session_id)
        logger.debug(f"🧹 Cleared session {session_id} from memory and loaded sessions")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics from both backends."""
        memory_stats = await self.memory_cache.get_stats()
        
        stats = {
            'cache_type': 'performance_optimized',
            'strategy': 'memory_first_with_postgresql_warmup',
            'loaded_sessions_count': len(self.loaded_sessions),
            'loaded_sessions': list(self.loaded_sessions) if len(self.loaded_sessions) <= 10 else f"{len(self.loaded_sessions)} sessions",
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
    
    async def warm_up_session(self, session_id: str) -> bool:
        """
        Manually warm up a session by loading from PostgreSQL.
        Useful for pre-loading frequently accessed conversations.
        
        Returns:
            bool: True if data was loaded, False if no data found
        """
        if session_id in self.loaded_sessions:
            logger.debug(f"🔥 Session {session_id} already warmed up")
            return True
        
        if self.postgres_backend:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    # Load into memory
                    for response in postgres_responses:
                        await self.memory_cache.add(session_id, response)
                    
                    self.loaded_sessions.add(session_id)
                    logger.debug(f"🔥 Warmed up session {session_id} with {len(postgres_responses)} responses")
                    return True
            except Exception as e:
                logger.error(f"Warm-up error for {session_id}: {e}")
        
        return False
    
    def get_performance_info(self) -> Dict[str, Any]:
        """Get performance-related information."""
        return {
            'strategy': 'memory_first_with_postgresql_warmup',
            'loaded_sessions_count': len(self.loaded_sessions),
            'memory_cache_sessions': len(self.memory_cache.cache) if hasattr(self.memory_cache, 'cache') else 0,
            'performance_benefits': {
                'first_request': 'PostgreSQL load + memory cache',
                'subsequent_requests': '⚡ Memory only (fast)',
                'new_conversations': '⚡ Memory only (fast)',
                'active_sessions': '⚡ Memory only (fast)'
            }
        }


# Singleton instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the performance-optimized cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service