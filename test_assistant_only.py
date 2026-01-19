#!/usr/bin/env python3
"""
Test the new assistant-only PostgreSQL backend
"""

import psycopg
import asyncio
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'chatbot'))
sys.path.insert(0, os.path.dirname(__file__))

async def test_assistant_only():
    """Test loading conversation using assistant rows only"""
    
    # First, check what's in the assistant rows for conversation '1'
    print("=== Raw Assistant Data for Conversation '1' ===")
    conn = psycopg.connect("postgresql://teleqcuser:LqXlObT4t4Y0g8H@3.21.212.7:5432/tiatelemdqc")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, role, query, response, created_at
        FROM chatbot_messages 
        WHERE conversation_id = '1' 
        AND deleted_at IS NULL
        AND role = 'assistant'
        ORDER BY id ASC
    """)
    
    assistant_rows = cursor.fetchall()
    print(f"Found {len(assistant_rows)} assistant rows:")
    
    for row in assistant_rows:
        msg_id, role, query, response, created = row
        print(f"\nID: {msg_id}")
        print(f"Query: '{query}'")
        print(f"Response: '{response}'")
        print(f"Time: {created}")
    
    cursor.close()
    conn.close()
    
    # Test the SQL query directly (simulating the backend)
    print(f"\n=== Testing SQL Query (Backend Simulation) ===")
    
    conn = psycopg.connect("postgresql://teleqcuser:LqXlObT4t4Y0g8H@3.21.212.7:5432/tiatelemdqc")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT query, response, created_at, id
        FROM chatbot_messages
        WHERE conversation_id = %s 
          AND deleted_at IS NULL
          AND role = 'assistant'
          AND query IS NOT NULL
          AND response IS NOT NULL
        ORDER BY id ASC
        LIMIT 100
    """, ("1",))
    
    rows = cursor.fetchall()
    print(f"Backend would load {len(rows)} Q&A pairs:")
    
    qa_pairs = []
    for row in rows:
        query, response, created_at, msg_id = row
        qa_pair = {
            'query': query or '',
            'response': response or '',
            'timestamp': created_at.isoformat() if created_at else '',
            'message_id': msg_id
        }
        qa_pairs.append(qa_pair)
        
        print(f"\nQ: {qa_pair['query']}")
        print(f"A: {qa_pair['response']}")
        print(f"Time: {qa_pair['timestamp']}")
    
    cursor.close()
    conn.close()
    
    return qa_pairs

if __name__ == "__main__":
    asyncio.run(test_assistant_only())