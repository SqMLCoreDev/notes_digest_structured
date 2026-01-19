#!/usr/bin/env python3
"""
Check PostgreSQL conversation ID '1' specifically for chatbot history debugging
"""

import psycopg
from datetime import datetime

def check_conversation_1():
    """Check conversation ID '1' in PostgreSQL chatbot_messages table"""
    
    connection_string = "postgresql://teleqcuser:LqXlObT4t4Y0g8H@3.21.212.7:5432/tiatelemdqc"
    conversation_id = "1"
    
    try:
        print("🔍 Connecting to PostgreSQL...")
        conn = psycopg.connect(connection_string)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'chatbot_messages'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        if not table_exists:
            print("❌ Table 'chatbot_messages' does not exist")
            return
        
        print("✅ Connected to PostgreSQL")
        print("📋 Table 'chatbot_messages' exists")
        
        # Check specifically for conversation_id = '1'
        print(f"\n=== Checking Conversation ID '{conversation_id}' ===")
        
        cursor.execute("""
            SELECT COUNT(*) as total_messages,
                   COUNT(*) FILTER (WHERE role = 'user') as user_messages,
                   COUNT(*) FILTER (WHERE role = 'assistant') as assistant_messages,
                   MIN(created_at) as first_message, 
                   MAX(created_at) as last_message
            FROM chatbot_messages 
            WHERE conversation_id = %s 
            AND deleted_at IS NULL
        """, (conversation_id,))
        
        result = cursor.fetchone()
        total, user_count, assistant_count, first, last = result
        
        if total == 0:
            print(f"❌ No messages found for conversation_id '{conversation_id}'")
            
            # Check what conversation IDs do exist
            cursor.execute("""
                SELECT DISTINCT conversation_id 
                FROM chatbot_messages 
                WHERE deleted_at IS NULL
                ORDER BY conversation_id
                LIMIT 10
            """)
            existing_ids = cursor.fetchall()
            if existing_ids:
                print(f"\n📋 Available conversation IDs:")
                for row in existing_ids:
                    print(f"   - '{row[0]}'")
            else:
                print(f"\n📋 No conversations found in the database")
            return
        
        print(f"✅ Found conversation_id '{conversation_id}'!")
        print(f"📊 Total messages: {total}")
        print(f"👤 User messages: {user_count}")
        print(f"🤖 Assistant messages: {assistant_count}")
        print(f"📅 First message: {first.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Last message: {last.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show all messages from conversation_id = '1'
        print(f"\n=== All Messages in Conversation '{conversation_id}' ===")
        
        cursor.execute("""
            SELECT id, role, query, response, created_at 
            FROM chatbot_messages 
            WHERE conversation_id = %s 
            AND deleted_at IS NULL
            ORDER BY id ASC
        """, (conversation_id,))
        
        messages = cursor.fetchall()
        
        for i, msg in enumerate(messages, 1):
            msg_id, role, query, response, created = msg
            content = query if query else response
            timestamp = created.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"\n{i:2d}. Message ID: {msg_id}")
            print(f"    Role: {role}")
            print(f"    Time: {timestamp}")
            
            if content:
                # Show full content for conversation_id = '1'
                print(f"    Content: {content}")
            else:
                print(f"    Content: [No content]")
        
        print(f"\n✅ SUMMARY:")
        print(f"   Conversation '{conversation_id}' has {total} messages")
        print(f"   Should be loadable by the chatbot API")
        
        # Generate test payload
        print(f"\n🧪 TEST PAYLOAD:")
        print(f'{{')
        print(f'  "department": "TiaMD",')
        print(f'  "user": "TiaMD",')
        print(f'  "chatquery": "What are my previous questions",')
        print(f'  "historyenabled": true,')
        print(f'  "conversation_id": "{conversation_id}"')
        print(f'}}')
        
        cursor.close()
        conn.close()
        
    except psycopg.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_api_conversation_1():
    """Test the chatbot API specifically with conversation_id = '1'"""
    
    try:
        import requests
        
        url = "http://localhost:8000/chatbot/query"
        payload = {
            "department": "TiaMD",
            "user": "TiaMD",
            "chatquery": "What are my previous questions",
            "historyenabled": True,
            "conversation_id": "1"
        }
        
        print(f"\n🧪 Testing API with conversation_id: '1'")
        print(f"URL: {url}")
        print("Payload:", payload)
        
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"\n📡 API Response:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            chat_response = result.get('chatResponse', '')
            session_id = result.get('sessionId', '')
            
            print(f"Session ID returned: '{session_id}'")
            print(f"Response length: {len(chat_response)} characters")
            
            if "I don't have access" in chat_response:
                print("❌ API says no conversation history found")
                print("   This means conversation '1' exists in DB but isn't being loaded by the cache service")
                print("\n🔍 Possible issues:")
                print("   - Cache service not reading from PostgreSQL correctly")
                print("   - Conversation format not compatible with cache service")
                print("   - Redis/PostgreSQL cache backend issue")
            else:
                print("✅ API successfully loaded conversation history!")
                print(f"\n🤖 AI Response:")
                print(chat_response)
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except ImportError:
        print("⚠️  'requests' module not available. Install with: pip install requests")
    except Exception as e:
        print(f"❌ API Test Error: {e}")

if __name__ == "__main__":
    print("🔍 PostgreSQL Conversation '1' Checker")
    print("=" * 50)
    
    check_conversation_1()
    
    # Ask if user wants to test API
    try:
        test_input = input("\n🧪 Test API with conversation_id '1'? (y/n): ").lower().strip()
        if test_input == 'y':
            test_api_conversation_1()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except:
        pass