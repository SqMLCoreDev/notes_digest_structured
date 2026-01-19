"""
Clean Cache Service - No Redis, PostgreSQL + Memory Only

This replaces the original cache_service.py with a simplified version
that removes all Redis code and uses the hybrid approach.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


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
    Used for new conversations and as fallback.
    """
    
    def __init__(self, max_entries_per_session: int = 30):
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
            logger.info(f"Cleared {count} entries from memory cache for session {key}")
    
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
            'avg_responses_per_session': round(total_responses / total_sessions, 1) if total_sessions > 0 else 0,
            'max_entries_per_session': self.max_entries
        }


# Import the hybrid cache service as the main cache service
from app.services.cache_service_hybrid import HybridCacheService as CacheService, get_cache_service

# For backward compatibility, expose the same interface
__all__ = ['CacheService', 'get_cache_service', 'CacheBackend', 'InMemoryCacheBackend']