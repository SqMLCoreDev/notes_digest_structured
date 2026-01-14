"""
app/services/cache_service.py - Response Caching Service

Provides an abstraction layer for response caching with multiple backend support.
Supports in-memory (development) and Redis (production) backends.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# Try to import redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed. Redis caching disabled.")


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached responses for a session."""
        pass
    
    @abstractmethod
    async def add(self, key: str, entry: Dict[str, Any]) -> None:
        """Add a response to the cache."""
        pass
    
    @abstractmethod
    async def clear(self, key: str) -> None:
        """Clear cache for a session."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class InMemoryCacheBackend(CacheBackend):
    """
    In-memory cache backend using deques.
    Suitable for development and single-instance deployments.
    """
    
    def __init__(self, max_entries_per_session: int = 10):
        self.cache: Dict[str, deque] = {}
        self.max_entries = max_entries_per_session
    
    async def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        if key not in self.cache:
            return None
        return list(self.cache[key])
    
    async def add(self, key: str, entry: Dict[str, Any]) -> None:
        if key not in self.cache:
            self.cache[key] = deque(maxlen=self.max_entries)
        self.cache[key].append(entry)
    
    async def clear(self, key: str) -> None:
        if key in self.cache:
            count = len(self.cache[key])
            del self.cache[key]
            logger.info(f"Cleared {count} entries from cache for session {key}")
    
    async def get_stats(self) -> Dict[str, Any]:
        total_responses = sum(len(responses) for responses in self.cache.values())
        total_sessions = len(self.cache)
        
        # Estimate memory usage (text only)
        total_size_bytes = 0
        for responses in self.cache.values():
            for resp in responses:
                total_size_bytes += len(resp.get('response', ''))
                total_size_bytes += len(resp.get('query', ''))
        
        return {
            'backend': 'memory',
            'total_sessions': total_sessions,
            'total_responses': total_responses,
            'estimated_size_kb': round(total_size_bytes / 1024, 2),
            'avg_responses_per_session': round(total_responses / total_sessions, 1) if total_sessions > 0 else 0
        }


class RedisCacheBackend(CacheBackend):
    """
    Redis cache backend for production deployments.
    Provides persistence, multi-instance support, and TTL.
    """
    
    def __init__(
        self,
        redis_url: str = None,
        max_entries_per_session: int = 10,
        ttl_seconds: int = 3600  # 1 hour default
    ):
        self.redis_url = redis_url or settings.REDIS_URL
        self.max_entries = max_entries_per_session
        self.ttl = ttl_seconds
        self._client: Optional[redis.Redis] = None
        self._key_prefix = "mcp:session:"
    
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
    
    async def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached responses for a session from Redis."""
        try:
            client = await self._get_client()
            redis_key = self._session_key(key)
            
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
                    logger.warning(f"Invalid JSON in cache: {item[:100]}")
            
            return responses
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def add(self, key: str, entry: Dict[str, Any]) -> None:
        """Add a response to the Redis cache."""
        try:
            client = await self._get_client()
            redis_key = self._session_key(key)
            
            # Serialize entry
            entry_json = json.dumps(entry, default=str)
            
            # Add to list (right push)
            await client.rpush(redis_key, entry_json)
            
            # Trim to max entries (keep most recent)
            await client.ltrim(redis_key, -self.max_entries, -1)
            
            # Set/refresh TTL
            await client.expire(redis_key, self.ttl)
            
            logger.debug(f"Cached response in Redis for session {key}")
            
        except Exception as e:
            logger.error(f"Redis add error: {e}")
    
    async def clear(self, key: str) -> None:
        """Clear cache for a session in Redis."""
        try:
            client = await self._get_client()
            redis_key = self._session_key(key)
            
            deleted = await client.delete(redis_key)
            if deleted:
                logger.info(f"Cleared Redis cache for session {key}")
                
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
            sample_keys = keys[:10] if len(keys) > 10 else keys
            for key in sample_keys:
                items = await client.lrange(key, 0, -1)
                total_responses += len(items)
                for item in items:
                    total_size_bytes += len(item)
            
            # Extrapolate if sampled
            if len(keys) > 10:
                ratio = len(keys) / 10
                total_responses = int(total_responses * ratio)
                total_size_bytes = int(total_size_bytes * ratio)
            
            return {
                'backend': 'redis',
                'redis_url': self.redis_url.split('@')[-1] if '@' in self.redis_url else self.redis_url,
                'total_sessions': total_sessions,
                'total_responses': total_responses,
                'estimated_size_kb': round(total_size_bytes / 1024, 2),
                'ttl_seconds': self.ttl
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'backend': 'redis', 'error': str(e)}
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class CacheService:
    """
    Cache service that provides a unified interface for response caching.
    Supports multiple backends (memory, redis).
    Automatically selects Redis if available and configured.
    """
    
    def __init__(self, backend: Optional[CacheBackend] = None):
        if backend is None:
            backend = self._create_default_backend()
        self.backend = backend
    
    def _create_default_backend(self) -> CacheBackend:
        """Create the appropriate cache backend based on config."""
        # Try Redis first if available and configured
        if REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                logger.info(f"Using Redis cache backend")
                return RedisCacheBackend(
                    redis_url=settings.REDIS_URL,
                    max_entries_per_session=settings.MAX_RESPONSES_PER_SESSION,
                    ttl_seconds=settings.CACHE_TTL_SECONDS
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}. Falling back to memory.")
        
        # Fallback to in-memory
        logger.info("Using in-memory cache backend")
        return InMemoryCacheBackend(
            max_entries_per_session=settings.MAX_RESPONSES_PER_SESSION
        )
    
    async def save_response(
        self,
        session_id: str,
        query: str,
        response_text: str,
        used_indices: List[str]
    ) -> None:
        """
        Save a response to the cache.
        
        Args:
            session_id: Session identifier
            query: User's query
            response_text: AI response
            used_indices: Indices used in the query
        """
        entry = {
            'query': query,
            'response': response_text,
            'used_indices': used_indices,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await self.backend.add(session_id, entry)
        logger.debug(f"Cached response for session {session_id}")
    
    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all cached responses for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of response dictionaries (oldest to newest)
        """
        responses = await self.backend.get(session_id)
        if responses is None:
            return []
        
        logger.debug(f"Retrieved {len(responses)} cached responses for session {session_id}")
        return responses
    
    async def clear_session(self, session_id: str) -> None:
        """
        Clear all cached responses for a session.
        
        Args:
            session_id: Session identifier
        """
        await self.backend.clear(session_id)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return await self.backend.get_stats()
    
    def responses_to_conversation_history(
        self,
        responses: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert cached responses to conversation history format.
        
        Args:
            responses: List of cached response entries
            
        Returns:
            List of conversation history entries
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
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
