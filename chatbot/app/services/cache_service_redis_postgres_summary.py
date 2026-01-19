"""
Production Cache Service - Redis + PostgreSQL with Auto-Summarization

Features:
1. Redis: Fast, shared cache across multiple app instances
2. PostgreSQL: Persistent storage with automatic summarization
3. Auto-summarization: When conversations exceed 30 messages
4. Context preservation: Maintains conversation flow with summaries
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.postgres_cache_backend_with_summary import create_postgres_cache_backend_with_summary, ASYNCPG_AVAILABLE

logger = get_logger(__name__)

# Try to import redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed. Redis caching disabled.")


class RedisCacheBackend:
    """Redis cache backend for fast, shared access."""
    
    def __init__(
        self,
        redis_url: str = None,
        max_entries_per_session: int = 30,
        ttl_seconds: int = 3600
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.max_entries = max_entries_per_session
        self.ttl = ttl_seconds
        self._client: Optional[redis.Redis] = None
        self._key_prefix = "chatbot:session:"
    
    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._client
    
    def _session_key(self, session_id: str) -> str:
        """Get Redis key for a session."""
        return f"{self._key_prefix}{session_id}"
    
    async def get(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached responses for a session from Redis."""
        try:
            client = await self._get_client()
            redis_key = self._session_key(session_id)
            
            # Get all items from the list
            items = await client.lrange(redis_key, 0, -1)
            
            if not items:
                return None
            
            # Parse JSON entries
            responses = []
            for item in items:
                try:
                    responses.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in Redis cache: {item[:100]}")
            
            # Refresh TTL on access
            await client.expire(redis_key, self.ttl)
            
            return responses
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, session_id: str, responses: List[Dict[str, Any]]) -> None:
        """Set complete conversation history in Redis."""
        try:
            client = await self._get_client()
            redis_key = self._session_key(session_id)
            
            # Clear existing data
            await client.delete(redis_key)
            
            # Add all responses
            if responses:
                serialized_responses = [json.dumps(resp, default=str) for resp in responses]
                await client.rpush(redis_key, *serialized_responses)
                
                # Note: Don't trim here since responses might include summaries
                # The summarization happens at PostgreSQL level
            
            # Set TTL
            await client.expire(redis_key, self.ttl)
            
            logger.debug(f"Cached {len(responses)} responses in Redis for session {session_id}")
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    async def add(self, session_id: str, entry: Dict[str, Any]) -> None:
        """Add a single response to Redis cache."""
        try:
            client = await self._get_client()
            redis_key = self._session_key(session_id)
            
            # Serialize entry
            entry_json = json.dumps(entry, default=str)
            
            # Add to list (right push)
            await client.rpush(redis_key, entry_json)
            
            # Set/refresh TTL
            await client.expire(redis_key, self.ttl)
            
            logger.debug(f"Added response to Redis cache for session {session_id}")
            
        except Exception as e:
            logger.error(f"Redis add error: {e}")
    
    async def clear(self, session_id: str) -> None:
        """Clear cache for a session in Redis."""
        try:
            client = await self._get_client()
            redis_key = self._session_key(session_id)
            
            deleted = await client.delete(redis_key)
            if deleted:
                logger.info(f"Cleared Redis cache for session {session_id}")
                
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class ProductionCacheServiceWithSummary:
    """
    Production cache service with automatic conversation summarization.
    
    Features:
    1. Redis: Fast, shared cache across app instances
    2. PostgreSQL: Persistent storage with auto-summarization
    3. Smart summarization: Keeps context while managing memory
    4. Multi-instance: Shared state across all app instances
    """
    
    def __init__(self):
        # Redis cache for fast, shared access
        self.redis_cache = None
        if REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                self.redis_cache = RedisCacheBackend(
                    redis_url=settings.REDIS_URL,
                    max_entries_per_session=30,
                    ttl_seconds=getattr(settings, 'CACHE_TTL_SECONDS', 3600)
                )
                logger.info("Production cache with summarization: Redis + PostgreSQL initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")
        
        # PostgreSQL backend with summarization
        self.postgres_backend = None
        if ASYNCPG_AVAILABLE and settings.POSTGRES_CONNECTION:
            try:
                self.postgres_backend = create_postgres_cache_backend_with_summary(
                    connection_string=settings.POSTGRES_CONNECTION,
                    max_entries_per_session=30,
                    table_name="chatbot_messages"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL backend: {e}")
        
        if not self.redis_cache and not self.postgres_backend:
            logger.error("No cache backends available!")
    
    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history with summarization support:
        1. ⚡ Try Redis first (fast, shared)
        2. 🔄 Load from PostgreSQL with auto-summarization
        3. 📝 Cache summarized conversation in Redis
        """
        
        # ⚡ FAST PATH: Try Redis first
        if self.redis_cache:
            try:
                redis_responses = await self.redis_cache.get(session_id)
                if redis_responses:
                    logger.debug(f"⚡ Redis hit: Retrieved {len(redis_responses)} responses for {session_id}")
                    return redis_responses
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # 🔄 SMART LOAD: PostgreSQL with auto-summarization
        if self.postgres_backend:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    # Check if conversation was summarized
                    has_summary = any(msg.get('is_summary', False) for msg in postgres_responses)
                    
                    if has_summary:
                        logger.info(f"📝 Loaded summarized conversation for {session_id}: {len(postgres_responses)} messages")
                    else:
                        logger.debug(f"🔄 PostgreSQL hit: Loading {len(postgres_responses)} responses for {session_id}")
                    
                    # Cache in Redis for future requests (including summaries)
                    if self.redis_cache:
                        await self.redis_cache.set(session_id, postgres_responses)
                        logger.debug(f"🔄 Cached in Redis for future requests: {session_id}")
                    
                    return postgres_responses
                else:
                    logger.debug(f"🔄 No data in PostgreSQL for {session_id}")
            except Exception as e:
                logger.error(f"PostgreSQL get error: {e}")
        
        # 🆕 NEW CONVERSATION
        logger.debug(f"🆕 New conversation: {session_id}")
        return []
    
    async def save_response(
        self,
        session_id: str,
        query: str,
        response_text: str,
        used_indices: List[str]
    ) -> None:
        """
        Save response to Redis cache.
        
        Note: UI team handles PostgreSQL persistence.
        Summarization happens when reading from PostgreSQL.
        """
        entry = {
            'query': query,
            'response': response_text,
            'used_indices': used_indices,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save to Redis for shared access across instances
        if self.redis_cache:
            await self.redis_cache.add(session_id, entry)
            logger.debug(f"⚡ Saved response to Redis cache for session {session_id}")
        else:
            logger.warning(f"No Redis cache available to save response for {session_id}")
    
    async def clear_session(self, session_id: str) -> None:
        """
        Clear session from Redis cache.
        PostgreSQL data remains (managed by UI team).
        """
        if self.redis_cache:
            await self.redis_cache.clear(session_id)
            logger.debug(f"🧹 Cleared Redis cache for session {session_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics including summarization info."""
        stats = {
            'cache_type': 'production_redis_postgresql_with_summarization',
            'strategy': 'redis_first_with_postgresql_auto_summarization',
            'redis_available': self.redis_cache is not None,
            'postgres_available': self.postgres_backend is not None,
            'summarization_enabled': True
        }
        
        if self.redis_cache:
            try:
                # Get basic Redis info
                client = await self.redis_cache._get_client()
                info = await client.info()
                stats['redis_cache'] = {
                    'backend': 'redis_production',
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            except Exception as e:
                stats['redis_cache'] = {'error': str(e)}
        
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
        Handles both regular messages and summaries.
        """
        history = []
        
        for resp in responses:
            if resp.get('is_summary', False):
                # Summary message
                history.append({
                    'question': '[Previous conversation summary]',
                    'answer': resp.get('response', ''),
                    'timestamp': resp.get('timestamp', ''),
                    'is_summary': True,
                    'message_count': resp.get('message_count', 0)
                })
            else:
                # Regular message
                history.append({
                    'question': resp.get('query', ''),
                    'answer': resp.get('response', ''),
                    'timestamp': resp.get('timestamp', '')
                })
        
        return history
    
    async def force_summarization(self, session_id: str) -> bool:
        """
        Manually trigger summarization for a conversation.
        Useful for testing or maintenance.
        """
        if not self.postgres_backend:
            return False
        
        try:
            # Clear Redis cache to force reload from PostgreSQL
            if self.redis_cache:
                await self.redis_cache.clear(session_id)
            
            # Get conversation from PostgreSQL (will trigger summarization if needed)
            responses = await self.postgres_backend.get(session_id)
            
            # Cache the result in Redis
            if responses and self.redis_cache:
                await self.redis_cache.set(session_id, responses)
            
            logger.info(f"Forced summarization check for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to force summarization for {session_id}: {e}")
            return False
    
    def get_performance_info(self) -> Dict[str, Any]:
        """Get performance and feature information."""
        return {
            'strategy': 'redis_first_with_postgresql_auto_summarization',
            'features': {
                'auto_summarization': 'Conversations > 30 messages automatically summarized',
                'context_preservation': 'Summaries maintain conversation context',
                'memory_management': 'Reduces memory usage while keeping context',
                'multi_instance_sharing': 'Redis shares state across app instances',
                'persistent_summaries': 'Summaries stored in PostgreSQL'
            },
            'benefits': {
                'redis_hit': '⚡ Super fast, shared across instances',
                'postgresql_with_summary': '📝 Smart context management',
                'new_conversations': '⚡ Immediate (no database query)',
                'long_conversations': '📝 Automatically summarized for efficiency',
                'context_maintained': '🧠 Summaries preserve conversation flow'
            }
        }


# Singleton instance
_cache_service: Optional[ProductionCacheServiceWithSummary] = None


def get_cache_service() -> ProductionCacheServiceWithSummary:
    """Get the production cache service with summarization."""
    global _cache_service
    if _cache_service is None:
        _cache_service = ProductionCacheServiceWithSummary()
    return _cache_service