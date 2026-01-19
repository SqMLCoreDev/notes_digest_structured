import requests

print("Testing simple query without history...")

try:
    response = requests.post("http://localhost:8000/chatbot/query", json={
        "department": "TiaMD",
        "user": "TiaMD",
        "chatquery": "Hello",
        "historyenabled": False
    }, timeout=10)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Works without history!")
        result = response.json()
        print(f"Response: {result['chatResponse'][:100]}...")
    else:
        print(f"❌ Failed: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ Timeout - server is hanging")
except requests.exceptions.ConnectionError:
    print("❌ Connection error - server not running")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nTesting with conversation history...")

try:
    response = requests.post("http://localhost:8000/chatbot/query", json={
        "department": "TiaMD",
        "user": "TiaMD", 
        "chatquery": "What are my previous questions",
        "historyenabled": True,
        "conversation_id": "1"
    }, timeout=15)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Works with history!")
        result = response.json()
        print(f"Response: {result['chatResponse'][:100]}...")
    else:
        print(f"❌ Failed: {response.text}")
        
except requests.exceptions.Timeout:
    print("❌ Timeout - conversation history loading is hanging")
except Exception as e:
    print(f"❌ Error: {e}")