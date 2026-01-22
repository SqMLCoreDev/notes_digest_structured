#!/usr/bin/env python3
"""
Test PostgreSQL connection and table structure
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_postgres_connection():
    """Test direct PostgreSQL connection"""
    
    print("🔗 Testing PostgreSQL Connection...")
    
    try:
        from app.services.clients.postgres_client import get_postgres_client, ASYNCPG_AVAILABLE
        from app.core.config import settings
        
        if not ASYNCPG_AVAILABLE:
            print("❌ asyncpg not available")
            return False
            
        if not settings.POSTGRES_CONNECTION:
            print("❌ POSTGRES_CONNECTION not configured")
            return False
            
        print(f"📊 Connection string: {settings.POSTGRES_CONNECTION[:50]}...")
        
        # Test connection
        client = get_postgres_client()
        
        # Test basic query
        print("🧪 Testing basic connection...")
        result = await client.fetchrow("SELECT version()")
        print(f"✅ PostgreSQL version: {result['version'][:50]}...")
        
        # Check if table exists
        print("🧪 Checking chatbot_messages table...")
        table_check = await client.fetchrow("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'chatbot_messages' 
            AND column_name = 'conversation_id'
        """)
        
        if table_check:
            print(f"✅ Table exists: conversation_id is {table_check['data_type']}")
        else:
            print("❌ chatbot_messages table or conversation_id column not found")
            
            # List available tables
            tables = await client.fetch("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            print(f"📋 Available tables: {[t['table_name'] for t in tables]}")
            return False
        
        # Test with sample data
        print("🧪 Testing sample query...")
        sample_data = await client.fetch("""
            SELECT conversation_id, role, query, response 
            FROM chatbot_messages 
            WHERE deleted_at IS NULL 
            LIMIT 3
        """)
        
        print(f"✅ Found {len(sample_data)} sample records")
        for i, row in enumerate(sample_data):
            print(f"  {i+1}. conversation_id='{row['conversation_id']}', role='{row['role']}'")
        
        # Test with string conversation_id
        print("🧪 Testing conversation_id query...")
        string_test = await client.fetch("""
            SELECT conversation_id, role, query, response 
            FROM chatbot_messages 
            WHERE conversation_id = $1 
            AND deleted_at IS NULL
            LIMIT 5
        """, 1)  # Use integer 1 since conversation_id is bigint
        
        print(f"✅ Conversation query result: {len(string_test)} rows")
        for row in string_test:
            print(f"  conversation_id={row['conversation_id']}, role={row['role']}")
        
        # Test type conversion
        print("🧪 Testing type conversion...")
        try:
            # Test if we can convert string to int
            test_session_id = "123"
            int_session_id = int(test_session_id)
            print(f"✅ Can convert '{test_session_id}' to {int_session_id}")
        except ValueError:
            print(f"❌ Cannot convert '{test_session_id}' to integer")
        
        try:
            # Test if we can convert non-numeric string
            test_session_id = "test-session-1"
            int_session_id = int(test_session_id)
            print(f"✅ Can convert '{test_session_id}' to {int_session_id}")
        except ValueError:
            print(f"⚠️ Cannot convert '{test_session_id}' to integer - this is expected")
        
        await client.close()
        print("🎉 PostgreSQL Connection Test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_postgres_connection())
    sys.exit(0 if success else 1)