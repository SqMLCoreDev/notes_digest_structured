"""
app/services/cache_service.py - Response Caching Interfaces & Backends

Provides the abstract base class and reusable backend implementations (Redis, In-Memory).
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
    Provides local fallback when other tiers are unavailable.
    """
    
    def __init__(self, max_entries_per_session: int = 30):
        self.cache: Dict[str, deque] = {}
        self.max_entries = max_entries_per_session
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'clears': 0
        }
    
    async def get(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached responses for a session."""
        if session_id not in self.cache:
            self.stats['misses'] += 1
            return None
        
        self.stats['hits'] += 1
        return list(self.cache[session_id])
    
    async def set(self, session_id: str, responses: List[Dict[str, Any]]) -> None:
        """Set complete conversation history."""
        # Create new deque with max length
        self.cache[session_id] = deque(responses, maxlen=self.max_entries)
        self.stats['sets'] += 1
    
    async def add(self, session_id: str, entry: Dict[str, Any]) -> None:
        """Add a single response to cache."""
        if session_id not in self.cache:
            self.cache[session_id] = deque(maxlen=self.max_entries)
        
        self.cache[session_id].append(entry)
        self.stats['sets'] += 1
    
    async def clear(self, session_id: str) -> None:
        """Clear cache for a session."""
        if session_id in self.cache:
            del self.cache[session_id]
            self.stats['clears'] += 1
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_responses = sum(len(responses) for responses in self.cache.values())
        total_sessions = len(self.cache)
        
        # Estimate memory usage
        total_size_bytes = 0
        for responses in self.cache.values():
            for resp in responses:
                total_size_bytes += len(resp.get('response', ''))
                total_size_bytes += len(resp.get('query', ''))
        
        return {
            'backend': 'in_memory',
            'total_sessions': total_sessions,
            'total_responses': total_responses,
            'estimated_size_kb': round(total_size_bytes / 1024, 2),
            'avg_responses_per_session': round(total_responses / total_sessions, 1) if total_sessions > 0 else 0,
            'max_entries_per_session': self.max_entries,
            'performance': self.stats.copy()
        }


class RedisCacheBackend(CacheBackend):
    """
    Redis cache backend for fast, shared access.
    Provides persistence, multi-instance support, and TTL.
    """
    
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
        self._available = True
    
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
        if not self._available:
            return None
            
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
            self._available = False  # Mark as unavailable
            return None
    
    async def set(self, session_id: str, responses: List[Dict[str, Any]]) -> None:
        """Set complete conversation history in Redis."""
        if not self._available:
            return
            
        try:
            client = await self._get_client()
            redis_key = self._session_key(session_id)
            
            # Clear existing data
            await client.delete(redis_key)
            
            # Add all responses
            if responses:
                serialized_responses = [json.dumps(resp, default=str) for resp in responses]
                await client.rpush(redis_key, *serialized_responses)
            
            # Set TTL
            await client.expire(redis_key, self.ttl)
            
            logger.debug(f"Cached {len(responses)} responses in Redis for session {session_id}")
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            self._available = False
    
    async def add(self, session_id: str, entry: Dict[str, Any]) -> None:
        """Add a single response to Redis cache."""
        if not self._available:
            return
            
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
            self._available = False
    
    async def clear(self, session_id: str) -> None:
        """Clear cache for a session in Redis."""
        if not self._available:
            return
            
        try:
            client = await self._get_client()
            redis_key = self._session_key(session_id)
            
            deleted = await client.delete(redis_key)
            if deleted:
                logger.info(f"Cleared Redis cache for session {session_id}")
                
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            self._available = False
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics from Redis."""
        if not self._available:
            return {"backend": "redis", "available": False}
            
        try:
            client = await self._get_client()
            info = await client.info()
            
            # Count keys with prefix
            # Using SCAN instead of KEYS for safety in async redis
            sessions_count = 0
            async for _ in client.scan_iter(match=f"{self._key_prefix}*"):
                sessions_count += 1
                
            return {
                "backend": "redis",
                "available": True,
                "total_sessions": sessions_count,
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_in_days": info.get("uptime_in_days", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "max_entries_per_session": self.max_entries,
                "ttl_seconds": self.ttl
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"backend": "redis", "available": False, "error": str(e)}

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
