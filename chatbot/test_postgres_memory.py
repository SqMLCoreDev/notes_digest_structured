#!/usr/bin/env python3
"""
Test script to verify PostgreSQL memory backend is working
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_postgres_memory():
    """Test PostgreSQL memory backend functionality"""
    
    print("🧪 Testing PostgreSQL Memory Backend...")
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from app.services.postgre_memory.cache_service_three_tier import get_cache_service
        from app.services.clients.postgres_client import ASYNCPG_AVAILABLE
        from app.core.config import settings
        
        print(f"✅ Imports successful")
        print(f"📊 ASYNCPG_AVAILABLE: {ASYNCPG_AVAILABLE}")
        print(f"🔗 POSTGRES_CONNECTION configured: {bool(settings.POSTGRES_CONNECTION)}")
        print(f"🔗 REDIS_URL configured: {bool(settings.REDIS_URL)}")
        
        # Test cache service initialization
        print("\n🚀 Initializing cache service...")
        cache_service = get_cache_service()
        
        # Get cache statistics
        print("\n📈 Getting cache statistics...")
        stats = await cache_service.get_stats()
        
        print("\n📊 Cache Service Stats:")
        print(f"  Cache Type: {stats.get('cache_type', 'unknown')}")
        print(f"  Strategy: {stats.get('strategy', 'unknown')}")
        
        # Check each tier
        if 'tier_1_redis' in stats:
            redis_stats = stats['tier_1_redis']
            print(f"\n⚡ Tier 1 (Redis): Available = {redis_stats.get('available', False)}")
            if redis_stats.get('available'):
                print(f"    Sessions: {redis_stats.get('total_sessions', 0)}")
        
        if 'tier_2_postgresql' in stats:
            pg_stats = stats['tier_2_postgresql']
            print(f"\n🔄 Tier 2 (PostgreSQL): Available = {pg_stats.get('available', False)}")
            if pg_stats.get('available'):
                print(f"    Conversations: {pg_stats.get('total_conversations', 0)}")
                print(f"    Q&A Pairs: {pg_stats.get('total_qa_pairs', 0)}")
            elif 'error' in pg_stats:
                print(f"    Error: {pg_stats['error']}")
        
        if 'tier_3_memory' in stats:
            mem_stats = stats['tier_3_memory']
            print(f"\n💾 Tier 3 (In-Memory): Available = True")
            print(f"    Sessions: {mem_stats.get('total_sessions', 0)}")
            print(f"    Responses: {mem_stats.get('total_responses', 0)}")
        
        # Test a simple operation
        print(f"\n🧪 Testing cache operations...")
        
        # Test getting responses for a non-existent session
        test_session = "test_session_123"
        responses = await cache_service.get_responses(test_session)
        print(f"✅ get_responses('{test_session}'): {len(responses)} responses")
        
        # Test saving a response
        await cache_service.save_response(
            session_id=test_session,
            query="Test query",
            response_text="Test response",
            used_indices=["test_index"]
        )
        print(f"✅ save_response() completed")
        
        # Test getting responses again
        responses_after = await cache_service.get_responses(test_session)
        print(f"✅ get_responses('{test_session}') after save: {len(responses_after)} responses")
        
        # Clean up
        await cache_service.clear_session(test_session)
        print(f"✅ clear_session() completed")
        
        print(f"\n🎉 PostgreSQL Memory Backend Test PASSED!")
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Make sure asyncpg is installed: pip install asyncpg>=0.29.0")
        return False
        
    except Exception as e:
        print(f"❌ Test Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_postgres_memory())
    sys.exit(0 if success else 1)