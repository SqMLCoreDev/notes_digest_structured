#!/usr/bin/env python3
"""
Debug the cache service flow to see why conversation history isn't loading
"""

import requests
import json
import time

def test_api_with_debug():
    """Test API and check server logs"""
    
    url = "http://localhost:8000/chatbot/query"
    payload = {
        "department": "TiaMD",
        "user": "TiaMD",
        "chatquery": "What are my previous questions",
        "historyenabled": True,
        "conversation_id": "1"
    }
    
    print("🧪 Testing API with conversation_id '1'...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"\n📡 Response:")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"Session ID: {result.get('sessionId')}")
            print(f"User: {result.get('user')}")
            print(f"Query: {result.get('query')}")
            
            chat_response = result.get('chatResponse', '')
            print(f"\n🤖 AI Response ({len(chat_response)} chars):")
            print(chat_response[:300] + "..." if len(chat_response) > 300 else chat_response)
            
            # Check if history was loaded
            if "I don't have access" in chat_response:
                print(f"\n❌ ISSUE: LLM says no conversation history")
                print(f"📋 CHECK SERVER LOGS FOR:")
                print(f"   - '🔄 PostgreSQL hit: Loading X responses for 1'")
                print(f"   - '🔄 No data in PostgreSQL for 1'")
                print(f"   - 'Redis get error' or 'PostgreSQL get error'")
                print(f"   - Any error messages during cache loading")
            else:
                print(f"\n✅ SUCCESS: LLM loaded conversation history!")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server not running on localhost:8000")
        print("Start server with: python main.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_health_endpoint():
    """Test health endpoint to see cache service status"""
    
    try:
        print("🏥 Testing health endpoint...")
        response = requests.get("http://localhost:8000/health", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Health Status: {result.get('status')}")
            print(f"Services: {result.get('services', {})}")
            
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check error: {e}")

if __name__ == "__main__":
    print("🔍 Cache Service Debug Tool")
    print("=" * 50)
    
    # Test health first
    test_health_endpoint()
    
    print("\n" + "=" * 50)
    
    # Test API
    test_api_with_debug()
    
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Check your server console logs for cache-related messages")
    print(f"2. Look for Redis connection errors")
    print(f"3. Look for PostgreSQL connection errors") 
    print(f"4. Check if conversation history is being loaded from PostgreSQL")
    print(f"5. Restart server if needed: python main.py")