#!/usr/bin/env python3
"""
List all available conversation IDs
"""

import psycopg

def list_conversations():
    """List all conversation IDs in the database"""
    
    connection_string = "postgresql://teleqcuser:LqXlObT4t4Y0g8H@3.21.212.7:5432/tiatelemdqc"
    
    try:
        print("🔍 Finding all conversation IDs...")
        conn = psycopg.connect(connection_string)
        cursor = conn.cursor()
        
        # Get all conversation IDs with message counts
        cursor.execute("""
            SELECT conversation_id, 
                   COUNT(*) as total_messages,
                   COUNT(*) FILTER (WHERE role = 'user') as user_messages,
                   COUNT(*) FILTER (WHERE role = 'assistant') as assistant_messages,
                   MAX(created_at) as last_message
            FROM chatbot_messages 
            WHERE deleted_at IS NULL
            GROUP BY conversation_id 
            ORDER BY conversation_id
        """)
        
        conversations = cursor.fetchall()
        print(f"Found {len(conversations)} conversations:")
        
        for conv in conversations:
            conv_id, total, user_count, assistant_count, last = conv
            print(f"\n📋 Conversation ID: '{conv_id}'")
            print(f"   Total messages: {total}")
            print(f"   User messages: {user_count}")
            print(f"   Assistant messages: {assistant_count}")
            print(f"   Last message: {last}")
        
        # Check which ones have valid assistant rows for our backend
        print(f"\n=== Conversations with Valid Assistant Rows ===")
        
        for conv in conversations:
            conv_id = conv[0]
            
            cursor.execute("""
                SELECT COUNT(*)
                FROM chatbot_messages 
                WHERE conversation_id = %s
                AND deleted_at IS NULL
                AND role = 'assistant'
                AND query IS NOT NULL
                AND response IS NOT NULL
            """, (conv_id,))
            
            valid_assistant_count = cursor.fetchone()[0]
            
            if valid_assistant_count > 0:
                print(f"✅ Conversation '{conv_id}': {valid_assistant_count} valid Q&A pairs")
            else:
                print(f"❌ Conversation '{conv_id}': No valid Q&A pairs")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_conversations()