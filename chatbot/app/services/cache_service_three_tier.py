"""
Three-Tier Cache Service - Redis + PostgreSQL + In-Memory

Enhanced caching strategy with three tiers:
1. Redis: Fast, shared cache across app instances (primary)
2. PostgreSQL: Read-only access for existing conversations (secondary)  
3. In-Memory: Local fallback when Redis/PostgreSQL unavailable (tertiary)

Features:
- Automatic failover between tiers
- In-memory summarization (no DB writes)
- Graceful degradation when services are unavailable
- Performance monitoring and statistics
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from collections import deque
import json

from app.core.config import settings
from app.core.logging import get_logger
from app.services.conversation_summarizer import get_conversation_summarizer

logger = get_logger(__name__)

# Try to import redis
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis package not installed. Redis caching disabled.")

# Try to import asyncpg for PostgreSQL support
try:
    import asyncpg
    from urllib.parse import urlparse
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False
    logger.warning("asyncpg package not installed. PostgreSQL caching disabled.")


class PostgreSQLCacheBackend:
    """
    Simple PostgreSQL cache backend for reading conversation history.
    Reads from existing chatbot_messages table (UI team manages writes).
    """
    
    def __init__(
        self,
        connection_string: str,
        max_entries_per_session: int = 30,
        table_name: str = "chatbot_messages"
    ):
        self.connection_string = connection_string
        self.max_entries = max_entries_per_session
        self.table_name = table_name
        self._pool: Optional[asyncpg.Pool] = None
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            parsed = urlparse(self.connection_string)
            self._pool = await asyncpg.create_pool(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip('/'),
                min_size=2,
                max_size=10
            )
            logger.info(f"✅ PostgreSQL pool created for table: {self.table_name}")
        return self._pool
    
    async def get(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get conversation history from assistant rows only."""
        try:
            pool = await self._get_pool()
            
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
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, conv_id_param, self.max_entries)
                
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
                
                logger.debug(f"Retrieved {len(messages)} Q&A pairs for conversation {conversation_id}")
                return messages
                
        except Exception as e:
            logger.error(f"PostgreSQL get error: {e}")
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics from chatbot_messages table."""
        try:
            pool = await self._get_pool()
            
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
            
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query)
                
                return {
                    'backend': 'postgresql_simple',
                    'table_name': self.table_name,
                    'total_conversations': row['total_conversations'] or 0,
                    'total_qa_pairs': row['total_qa_pairs'] or 0,
                    'total_user_messages': row['total_user_messages'] or 0,
                    'estimated_size_kb': round((row['total_size_bytes'] or 0) / 1024, 2),
                    'latest_message': row['latest_message'].isoformat() if row['latest_message'] else None,
                    'earliest_message': row['earliest_message'].isoformat() if row['earliest_message'] else None
                }
                
        except Exception as e:
            logger.error(f"PostgreSQL stats error: {e}")
            return {'backend': 'postgresql_simple', 'error': str(e)}
    
    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
    """
    In-memory cache backend using deques.
    Provides local fallback when Redis and PostgreSQL are unavailable.
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
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None


class ThreeTierCacheService:
    """
    Three-tier cache service with automatic failover.
    
    Tier 1: Redis (fast, shared across instances)
    Tier 2: PostgreSQL (read-only, existing conversations)
    Tier 3: In-Memory (local fallback)
    
    Features:
    - Automatic failover between tiers
    - In-memory summarization (no DB writes)
    - Performance monitoring
    - Graceful degradation
    """
    
    def __init__(self):
        # Tier 1: Redis cache for fast, shared access
        self.redis_cache = None
        if REDIS_AVAILABLE and settings.REDIS_URL:
            try:
                self.redis_cache = RedisCacheBackend(
                    redis_url=settings.REDIS_URL,
                    max_entries_per_session=30,
                    ttl_seconds=getattr(settings, 'CACHE_TTL_SECONDS', 3600)
                )
                logger.info("✅ Tier 1: Redis cache initialized")
            except Exception as e:
                logger.warning(f"❌ Tier 1: Redis initialization failed: {e}")
        
        # Tier 2: PostgreSQL backend for reading existing data (read-only)
        self.postgres_backend = None
        if ASYNCPG_AVAILABLE and settings.POSTGRES_CONNECTION:
            try:
                self.postgres_backend = PostgreSQLCacheBackend(
                    connection_string=settings.POSTGRES_CONNECTION,
                    max_entries_per_session=100,  # Read more from DB for summarization
                    table_name="chatbot_messages"
                )
                logger.info("✅ Tier 2: PostgreSQL cache initialized (read-only)")
            except Exception as e:
                logger.warning(f"❌ Tier 2: PostgreSQL initialization failed: {e}")
        
        # Tier 3: In-memory cache as final fallback
        self.memory_cache = InMemoryCacheBackend(
            max_entries_per_session=30
        )
        logger.info("✅ Tier 3: In-memory cache initialized (fallback)")
        
        # Conversation summarizer
        self.summarizer = get_conversation_summarizer()
        
        # Performance tracking
        self.tier_stats = {
            'redis_hits': 0,
            'postgres_hits': 0,
            'memory_hits': 0,
            'total_requests': 0
        }
        
        # Log final configuration
        available_tiers = []
        if self.redis_cache: available_tiers.append("Redis")
        if self.postgres_backend: available_tiers.append("PostgreSQL")
        available_tiers.append("In-Memory")
        
        logger.info(f"🚀 Three-tier cache service initialized: {' → '.join(available_tiers)}")
    
    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation history with three-tier fallback:
        1. ⚡ Try Redis first (Tier 1 - fastest)
        2. 🔄 Try PostgreSQL (Tier 2 - persistent)
        3. 💾 Try In-Memory (Tier 3 - local fallback)
        4. 📝 Apply summarization if needed
        """
        self.tier_stats['total_requests'] += 1
        
        # ⚡ TIER 1: Try Redis first
        if self.redis_cache and self.redis_cache.is_available():
            try:
                redis_responses = await self.redis_cache.get(session_id)
                if redis_responses:
                    self.tier_stats['redis_hits'] += 1
                    logger.debug(f"⚡ Tier 1 (Redis) hit: {len(redis_responses)} responses for {session_id}")
                    return redis_responses
            except Exception as e:
                logger.error(f"Tier 1 (Redis) error: {e}")
        
        # 🔄 TIER 2: Try PostgreSQL
        if self.postgres_backend:
            try:
                postgres_responses = await self.postgres_backend.get(session_id)
                if postgres_responses:
                    self.tier_stats['postgres_hits'] += 1
                    logger.debug(f"🔄 Tier 2 (PostgreSQL) hit: {len(postgres_responses)} responses for {session_id}")
                    
                    # 📝 Apply summarization if needed
                    final_responses = await self._apply_summarization(session_id, postgres_responses)
                    
                    # Cache in higher tiers for next time
                    await self._cache_in_higher_tiers(session_id, final_responses)
                    
                    return final_responses
            except Exception as e:
                logger.error(f"Tier 2 (PostgreSQL) error: {e}")
        
        # 💾 TIER 3: Try In-Memory fallback
        try:
            memory_responses = await self.memory_cache.get(session_id)
            if memory_responses:
                self.tier_stats['memory_hits'] += 1
                logger.debug(f"💾 Tier 3 (In-Memory) hit: {len(memory_responses)} responses for {session_id}")
                return memory_responses
        except Exception as e:
            logger.error(f"Tier 3 (In-Memory) error: {e}")
        
        # 🆕 NEW CONVERSATION
        logger.debug(f"🆕 New conversation (all tiers empty): {session_id}")
        return []
    
    async def _apply_summarization(self, session_id: str, responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply in-memory summarization if needed."""
        if await self.summarizer.should_summarize(responses):
            logger.info(f"📝 Summarizing conversation {session_id}: {len(responses)} messages")
            
            # Summarize in-memory (don't save to DB)
            summarized_conversation, summary_entry = await self.summarizer.summarize_conversation(responses)
            
            logger.info(f"📝 Summarization complete: {len(responses)} → {len(summarized_conversation)} messages")
            return summarized_conversation
        
        return responses
    
    async def _cache_in_higher_tiers(self, session_id: str, responses: List[Dict[str, Any]]) -> None:
        """Cache responses in higher tiers for faster future access."""
        # Cache in Redis (Tier 1)
        if self.redis_cache and self.redis_cache.is_available():
            await self.redis_cache.set(session_id, responses)
            logger.debug(f"⚡ Cached in Tier 1 (Redis): {session_id}")
        
        # Cache in Memory (Tier 3) as backup
        await self.memory_cache.set(session_id, responses)
        logger.debug(f"💾 Cached in Tier 3 (In-Memory): {session_id}")
    
    async def save_response(
        self,
        session_id: str,
        query: str,
        response_text: str,
        used_indices: List[str]
    ) -> None:
        """
        Save response to all available cache tiers.
        
        Note: UI team handles PostgreSQL persistence.
        We update Redis and In-Memory caches for current session.
        """
        entry = {
            'query': query,
            'response': response_text,
            'used_indices': used_indices,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Save to Redis (Tier 1)
        if self.redis_cache and self.redis_cache.is_available():
            await self.redis_cache.add(session_id, entry)
            logger.debug(f"⚡ Saved to Tier 1 (Redis): {session_id}")
        
        # Save to In-Memory (Tier 3) as backup
        await self.memory_cache.add(session_id, entry)
        logger.debug(f"💾 Saved to Tier 3 (In-Memory): {session_id}")
    
    async def clear_session(self, session_id: str) -> None:
        """Clear session from all cache tiers."""
        # Clear Redis (Tier 1)
        if self.redis_cache:
            await self.redis_cache.clear(session_id)
            logger.debug(f"⚡ Cleared Tier 1 (Redis): {session_id}")
        
        # Clear In-Memory (Tier 3)
        await self.memory_cache.clear(session_id)
        logger.debug(f"💾 Cleared Tier 3 (In-Memory): {session_id}")
        
        # Note: PostgreSQL (Tier 2) is read-only, managed by UI team
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all tiers."""
        stats = {
            'cache_type': 'three_tier_redis_postgresql_memory',
            'strategy': 'redis_first_postgresql_fallback_memory_backup',
            'tiers': {
                'tier_1': 'Redis (fast, shared)',
                'tier_2': 'PostgreSQL (persistent, read-only)',
                'tier_3': 'In-Memory (local fallback)'
            },
            'performance': self.tier_stats.copy()
        }
        
        # Add hit rates
        total_requests = self.tier_stats['total_requests']
        if total_requests > 0:
            stats['hit_rates'] = {
                'redis_hit_rate': round(self.tier_stats['redis_hits'] / total_requests * 100, 1),
                'postgres_hit_rate': round(self.tier_stats['postgres_hits'] / total_requests * 100, 1),
                'memory_hit_rate': round(self.tier_stats['memory_hits'] / total_requests * 100, 1)
            }
        
        # Redis stats
        if self.redis_cache:
            try:
                client = await self.redis_cache._get_client()
                info = await client.info()
                stats['tier_1_redis'] = {
                    'available': self.redis_cache.is_available(),
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            except Exception as e:
                stats['tier_1_redis'] = {'available': False, 'error': str(e)}
        else:
            stats['tier_1_redis'] = {'available': False, 'reason': 'not_configured'}
        
        # PostgreSQL stats
        if self.postgres_backend:
            try:
                postgres_stats = await self.postgres_backend.get_stats()
                stats['tier_2_postgresql'] = postgres_stats
            except Exception as e:
                stats['tier_2_postgresql'] = {'available': False, 'error': str(e)}
        else:
            stats['tier_2_postgresql'] = {'available': False, 'reason': 'not_configured'}
        
        # In-Memory stats
        memory_stats = await self.memory_cache.get_stats()
        stats['tier_3_memory'] = memory_stats
        
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
                # Summary entry
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
        Clears all cache tiers and reloads from database.
        """
        try:
            # Clear all cache tiers
            await self.clear_session(session_id)
            
            # Reload from PostgreSQL (will trigger summarization if needed)
            responses = await self.get_responses(session_id)
            
            logger.info(f"🔄 Force refreshed conversation {session_id} from PostgreSQL")
            return True
            
        except Exception as e:
            logger.error(f"Failed to force refresh {session_id}: {e}")
            return False
    
    def get_performance_info(self) -> Dict[str, Any]:
        """Get performance and feature information."""
        return {
            'strategy': 'three_tier_cache_with_automatic_failover',
            'tiers': {
                'tier_1': {
                    'name': 'Redis',
                    'purpose': 'Fast, shared cache across app instances',
                    'fallback': 'PostgreSQL if Redis unavailable'
                },
                'tier_2': {
                    'name': 'PostgreSQL', 
                    'purpose': 'Read existing conversations (UI team writes)',
                    'fallback': 'In-Memory if PostgreSQL unavailable'
                },
                'tier_3': {
                    'name': 'In-Memory',
                    'purpose': 'Local fallback when other tiers fail',
                    'fallback': 'New conversation if all tiers empty'
                }
            },
            'features': {
                'automatic_failover': 'Seamlessly falls back between tiers',
                'in_memory_summarization': 'Smart context management without DB writes',
                'performance_monitoring': 'Tracks hit rates and tier usage',
                'graceful_degradation': 'Works even when Redis/PostgreSQL unavailable',
                'multi_instance_sharing': 'Redis shares state across app instances'
            },
            'benefits': {
                'redis_hit': '⚡ Super fast, shared across instances',
                'postgresql_fallback': '🔄 Reads existing conversations when Redis fails',
                'memory_backup': '💾 Always works, even when services are down',
                'zero_data_loss': '🛡️ Multiple redundant storage layers',
                'performance_insights': '📊 Detailed statistics and monitoring'
            }
        }


# Singleton instance
_cache_service: Optional[ThreeTierCacheService] = None


def get_cache_service() -> ThreeTierCacheService:
    """Get the three-tier cache service."""
    global _cache_service
    if _cache_service is None:
        _cache_service = ThreeTierCacheService()
    return _cache_service