"""
Simplified Cache Service - Redis + PostgreSQL with In-Memory Summarization

Strategy:
1. Read from PostgreSQL (UI team saves everything)
2. Summarize in-memory when >30 messages (don't save to DB)
3. Cache summarized version in Redis for speed
4. Let UI team handle all PostgreSQL operations
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.postgres_cache_backend_improved import create_improved_postgres_cache_backend, ASYNCPG_AVAILABLE
from app.services.conversation_summarizer import get_conversation_summarizer

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


class SimplifiedCacheService:
    """
    Simplified cache service with in-memory summarization only.
    
    Strategy:
    1. Redis: Fast, shared cache across app instances
    2. PostgreSQL: Read-only access (UI team handles writes)
    3. In-memory summarization: Summarize on-the-fly, don't save to DB
    4. Cache summarized conversations in Redis for speed
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
                logger.info("Simplified cache: Redis + PostgreSQL (read-only) + in-memory summarization")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")
        
        # PostgreSQL backend for reading existing data (read-only)
        self.postgres_backend = None
        if ASYNCPG_AVAILABLE and settings.POSTGRES_CONNECTION:
            try:
                self.postgres_backend = create_improved_postgres_cache_backend(
                    connection_string=settings.POSTGRES_CONNECTION,
                    max_entries_per_session=100,  # Read more from DB for summarization
                    table_name="chatbot_messages"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL backend: {e}")
        
        # Conversation summarizer
        self.summarizer = get_conversation_summarizer()
        
        if not self.redis_cache and not self.postgres_backend:
            logger.error("No cache backends available!")
    
    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history with in-memory summarization:
        1. ⚡ Try Redis first (fast, may contain summarized version)
        2. 🔄 Load from PostgreSQL (read-only)
        3. 📝 Summarize in-memory if >30 messages
        4. ⚡ Cache summarized version in Redis
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
        
        # 🔄 LOAD FROM POSTGRESQL: Read existing conversation
        if self.postgres_backend:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    logger.debug(f"🔄 PostgreSQL hit: Loading {len(postgres_responses)} responses for {session_id}")
                    
                    # 📝 CHECK IF SUMMARIZATION NEEDED
                    if await self.summarizer.should_summarize(postgres_responses):
                        logger.info(f"📝 Summarizing conversation {session_id}: {len(postgres_responses)} messages")
                        
                        # Summarize in-memory (don't save to DB)
                        summarized_conversation, summary_entry = await self.summarizer.summarize_conversation(postgres_responses)
                        
                        # Cache summarized version in Redis
                        if self.redis_cache and summarized_conversation:
                            await self.redis_cache.set(session_id, summarized_conversation)
                            logger.debug(f"📝 Cached summarized conversation in Redis: {session_id}")
                        
                        logger.info(f"📝 In-memory summarization complete: {len(postgres_responses)} → {len(summarized_conversation)} messages")
                        return summarized_conversation
                    else:
                        # No summarization needed, cache as-is
                        if self.redis_cache:
                            await self.redis_cache.set(session_id, postgres_responses)
                            logger.debug(f"🔄 Cached full conversation in Redis: {session_id}")
                        
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
        Save response to Redis cache only.
        
        Note: UI team handles PostgreSQL persistence.
        We only update the Redis cache for current session.
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
        Clear session from Redis cache only.
        PostgreSQL data remains (managed by UI team).
        """
        if self.redis_cache:
            await self.redis_cache.clear(session_id)
            logger.debug(f"🧹 Cleared Redis cache for session {session_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        stats = {
            'cache_type': 'simplified_redis_postgresql_with_memory_summarization',
            'strategy': 'redis_first_with_postgresql_readonly_and_memory_summarization',
            'redis_available': self.redis_cache is not None,
            'postgres_available': self.postgres_backend is not None,
            'summarization_mode': 'in_memory_only',
            'database_writes': 'handled_by_ui_team'
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
        Handles both regular messages and in-memory summaries.
        """
        history = []
        
        for resp in responses:
            if resp.get('is_summary', False):
                # In-memory summary
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
    
    async def force_refresh(self, session_id: str) -> bool:
        """
        Force refresh conversation from PostgreSQL.
        Clears Redis cache and reloads from database.
        """
        try:
            # Clear Redis cache
            if self.redis_cache:
                await self.redis_cache.clear(session_id)
            
            # Reload from PostgreSQL (will trigger summarization if needed)
            responses = await self.get_responses(session_id)
            
            logger.info(f"Force refreshed conversation {session_id} from PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"Failed to force refresh {session_id}: {e}")
            return False
    
    def get_performance_info(self) -> Dict[str, Any]:
        """Get performance and feature information."""
        return {
            'strategy': 'simplified_redis_postgresql_with_memory_summarization',
            'features': {
                'in_memory_summarization': 'Conversations > 30 messages summarized on-the-fly',
                'no_database_writes': 'UI team handles all PostgreSQL operations',
                'redis_caching': 'Summarized conversations cached for speed',
                'multi_instance_sharing': 'Redis shares state across app instances',
                'read_only_postgresql': 'Only reads existing conversations'
            },
            'benefits': {
                'redis_hit': '⚡ Super fast, shared across instances',
                'postgresql_readonly': '🔄 Reads existing conversations only',
                'memory_summarization': '📝 Smart context management without DB writes',
                'ui_team_independence': '🤝 No interference with UI team operations',
                'cache_efficiency': '⚡ Summarized conversations cached for speed'
            }
        }


# Singleton instance
_cache_service: Optional[SimplifiedCacheService] = None


def get_cache_service() -> SimplifiedCacheService:
    """Get the simplified cache service."""
    global _cache_service
    if _cache_service is None:
        _cache_service = SimplifiedCacheService()
    return _cache_service