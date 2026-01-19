"""
Production Cache Service - Redis + PostgreSQL

Optimized for multiple sessions and production scalability:
1. Redis: Fast, shared cache across multiple app instances
2. PostgreSQL: Persistent storage for existing conversations
3. TTL: Automatic cleanup of inactive sessions
4. Scalable: Handles thousands of concurrent sessions
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.postgres_cache_backend_improved import create_improved_postgres_cache_backend, ASYNCPG_AVAILABLE

logger = get_logger(__name__)

# Try to import redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed. Redis caching disabled.")


class RedisCacheBackend:
    """
    Redis cache backend optimized for multiple sessions.
    """
    
    def __init__(
        self,
        redis_url: str = None,
        max_entries_per_session: int = 30,
        ttl_seconds: int = 3600  # 1 hour default
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
                
                # Trim to max entries (keep most recent)
                await client.ltrim(redis_key, -self.max_entries, -1)
            
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
            
            # Trim to max entries (keep most recent)
            await client.ltrim(redis_key, -self.max_entries, -1)
            
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
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics from Redis."""
        try:
            client = await self._get_client()
            
            # Get all session keys
            pattern = f"{self._key_prefix}*"
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            total_sessions = len(keys)
            total_responses = 0
            total_size_bytes = 0
            
            # Sample stats from a subset of keys (performance)
            sample_keys = keys[:20] if len(keys) > 20 else keys
            for key in sample_keys:
                items = await client.lrange(key, 0, -1)
                total_responses += len(items)
                for item in items:
                    total_size_bytes += len(item)
            
            # Extrapolate if sampled
            if len(keys) > 20:
                ratio = len(keys) / 20
                total_responses = int(total_responses * ratio)
                total_size_bytes = int(total_size_bytes * ratio)
            
            return {
                'backend': 'redis_production',
                'redis_url': self.redis_url.split('@')[-1] if '@' in self.redis_url else self.redis_url,
                'total_sessions': total_sessions,
                'total_responses': total_responses,
                'estimated_size_kb': round(total_size_bytes / 1024, 2),
                'ttl_seconds': self.ttl,
                'max_entries_per_session': self.max_entries
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'backend': 'redis_production', 'error': str(e)}
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class ProductionCacheService:
    """
    Production-ready cache service for multiple sessions.
    
    Strategy:
    1. Redis: Fast, shared cache across app instances
    2. PostgreSQL: Persistent storage for existing conversations
    3. Automatic TTL: Cleanup inactive sessions
    4. Scalable: Handles thousands of concurrent sessions
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
                logger.info("Production cache: Redis + PostgreSQL initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")
        
        # PostgreSQL backend for persistent data
        self.postgres_backend = None
        if ASYNCPG_AVAILABLE and settings.POSTGRES_CONNECTION:
            try:
                self.postgres_backend = create_improved_postgres_cache_backend(
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
        Get conversation history with production optimization:
        1. ⚡ Try Redis first (fast, shared across instances)
        2. 🔄 Load from PostgreSQL and cache in Redis
        3. 🆕 Return empty for new conversations
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
        
        # 🔄 WARM-UP PATH: Load from PostgreSQL and cache in Redis
        if self.postgres_backend:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    logger.debug(f"🔄 PostgreSQL hit: Loading {len(postgres_responses)} responses for {session_id}")
                    
                    # Cache in Redis for future requests
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
        This updates the shared Redis cache.
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
        """Get combined statistics from both backends."""
        stats = {
            'cache_type': 'production_redis_postgresql',
            'strategy': 'redis_first_with_postgresql_warmup',
            'redis_available': self.redis_cache is not None,
            'postgres_available': self.postgres_backend is not None
        }
        
        if self.redis_cache:
            try:
                redis_stats = await self.redis_cache.get_stats()
                stats['redis_cache'] = redis_stats
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
        Manually warm up a session by loading from PostgreSQL to Redis.
        """
        if self.postgres_backend and self.redis_cache:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    await self.redis_cache.set(session_id, postgres_responses)
                    logger.debug(f"🔥 Warmed up session {session_id} in Redis")
                    return True
            except Exception as e:
                logger.error(f"Warm-up error for {session_id}: {e}")
        
        return False
    
    def get_performance_info(self) -> Dict[str, Any]:
        """Get performance-related information."""
        return {
            'strategy': 'redis_first_with_postgresql_warmup',
            'benefits': {
                'redis_hit': '⚡ Super fast, shared across instances',
                'postgresql_warmup': 'Loads existing conversations once',
                'new_conversations': '⚡ Immediate (no database query)',
                'multiple_instances': 'Shared state across app instances',
                'auto_cleanup': 'TTL removes inactive sessions'
            },
            'scalability': {
                'concurrent_sessions': 'Thousands',
                'memory_management': 'Redis handles eviction',
                'instance_sharing': 'Yes',
                'restart_persistence': 'Yes (Redis + PostgreSQL)'
            }
        }


# Singleton instance
_cache_service: Optional[ProductionCacheService] = None


def get_cache_service() -> ProductionCacheService:
    """Get the production cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = ProductionCacheService()
    return _cache_service