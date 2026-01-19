#!/usr/bin/env python3
"""
Debug PostgreSQL-only conversation loading
"""

import requests
import json

def test_conversation_loading():
    """Test if conversation history is being loaded from PostgreSQL"""
    
    print("🧪 Testing conversation history loading...")
    
    # Make API call and watch for specific logs
    payload = {
        "department": "TiaMD",
        "user": "TiaMD",
        "chatquery": "What are my previous questions",
        "historyenabled": True,
        "conversation_id": "1"
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\n📋 WATCH SERVER LOGS FOR:")
    print("   - 'Processing query: user=TiaMD, department=TiaMD, history=True, session_id=None, conversation_id=1'")
    print("   - '🔄 PostgreSQL hit: Loading X responses for 1'")
    print("   - '🔄 No data in PostgreSQL for 1'")
    print("   - 'Connected to existing PostgreSQL table: chatbot_messages'")
    print("   - Any PostgreSQL errors")
    
    try:
        response = requests.post("http://localhost:8000/chatbot/query", json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ API Response:")
            print(f"Status: {response.status_code}")
            print(f"Session ID: '{result.get('sessionId')}'")
            print(f"User: '{result.get('user')}'")
            
            chat_response = result.get('chatResponse', '')
            print(f"\n🤖 AI Response ({len(chat_response)} chars):")
            
            if "I don't have access" in chat_response:
                print("❌ PROBLEM: LLM says no conversation history")
                print("\n🔍 POSSIBLE CAUSES:")
                print("   1. Cache service not loading from PostgreSQL")
                print("   2. PostgreSQL backend not finding conversation_id '1'")
                print("   3. Conversation history not being passed to LLM")
                print("   4. LLM receiving empty conversation history")
                
                print(f"\n📋 CHECK SERVER LOGS FOR:")
                print(f"   - Did you see '🔄 PostgreSQL hit: Loading 2 responses for 1'?")
                print(f"   - Or did you see '🔄 No data in PostgreSQL for 1'?")
                print(f"   - Any 'PostgreSQL get error' messages?")
                
            else:
                print("✅ SUCCESS: LLM loaded conversation history!")
                print(f"Response preview: {chat_response[:200]}...")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_without_history():
    """Test API without history to confirm basic functionality"""
    
    print("\n" + "="*50)
    print("🧪 Testing WITHOUT conversation history...")
    
    payload = {
        "department": "TiaMD",
        "user": "TiaMD",
        "chatquery": "Hello, how are you?",
        "historyenabled": False
    }
    
    try:
        response = requests.post("http://localhost:8000/chatbot/query", json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Basic API works: {response.status_code}")
            print(f"Response length: {len(result.get('chatResponse', ''))}")
        else:
            print(f"❌ Basic API failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Basic API error: {e}")

if __name__ == "__main__":
    print("🔍 PostgreSQL-Only Conversation History Debug")
    print("=" * 60)
    
    # Test basic functionality first
    test_without_history()
    
    # Test conversation history
    test_conversation_loading()
    
    print(f"\n📋 SUMMARY:")
    print(f"1. Make sure your server is running: python main.py")
    print(f"2. Watch server console logs when API call is made")
    print(f"3. Look for PostgreSQL-related log messages")
    print(f"4. Check if conversation_id '1' is being found in database")