#!/usr/bin/env python3
"""
Check conversation_id 2 specifically
"""

import psycopg

def check_conversation_2():
    """Check what's in conversation_id 2"""
    
    connection_string = "postgresql://teleqcuser:LqXlObT4t4Y0g8H@3.21.212.7:5432/tiatelemdqc"
    
    try:
        print("🔍 Checking conversation_id '2'...")
        conn = psycopg.connect(connection_string)
        cursor = conn.cursor()
        
        # Check all messages in conversation_id 2
        cursor.execute("""
            SELECT id, role, query, response, created_at
            FROM chatbot_messages 
            WHERE conversation_id = '2' 
            AND deleted_at IS NULL
            ORDER BY id ASC
        """)
        
        all_rows = cursor.fetchall()
        print(f"Total messages in conversation '2': {len(all_rows)}")
        
        for row in all_rows:
            msg_id, role, query, response, created = row
            print(f"\nID: {msg_id}, Role: {role}")
            print(f"Query: {query}")
            print(f"Response: {response}")
        
        # Check specifically assistant rows (what our backend looks for)
        cursor.execute("""
            SELECT id, query, response, created_at
            FROM chatbot_messages 
            WHERE conversation_id = 2  -- Using integer
            AND deleted_at IS NULL
            AND role = 'assistant'
            AND query IS NOT NULL
            AND response IS NOT NULL
            ORDER BY id ASC
        """)
        
        assistant_rows = cursor.fetchall()
        print(f"\n=== Assistant rows that backend would find ===")
        print(f"Found {len(assistant_rows)} assistant rows with both query and response:")
        
        for row in assistant_rows:
            msg_id, query, response, created = row
            print(f"\nID: {msg_id}")
            print(f"Q: {query}")
            print(f"A: {response}")
        
        cursor.close()
        conn.close()
        
        if len(assistant_rows) == 0:
            print(f"\n❌ ISSUE: No assistant rows found with both query AND response")
            print(f"   This is why the backend returns 'No cached responses found'")
        else:
            print(f"\n✅ Backend should find {len(assistant_rows)} Q&A pairs")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_conversation_2()