#!/usr/bin/env python3
"""
Test PostgreSQL connection for PGVector
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test PostgreSQL connection using the exact configuration."""
    
    connection_string = os.getenv('POSTGRES_CONNECTION')
    collection_name = os.getenv('COLLECTION_NAME', 'medical_notes_embeddings')
    
    print(f"Testing connection: {connection_string}")
    print(f"Collection name: {collection_name}")
    
    try:
        # Test basic psycopg connection
        print("\n1. Testing basic psycopg connection...")
        import psycopg
        
        # Convert LangChain format to psycopg format
        psycopg_connection = connection_string.replace("postgresql+psycopg://", "postgresql://")
        print(f"Using psycopg format: {psycopg_connection}")
        
        # Parse connection string
        conn = psycopg.connect(psycopg_connection)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL version: {version[0]}")
        
        # Check if pgvector extension exists
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        vector_ext = cursor.fetchone()
        if vector_ext:
            print("✅ pgvector extension is installed")
        else:
            print("⚠️ pgvector extension not found")
        
        # Check if collection table exists
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE %s;
        """, (f'langchain_pg_collection%',))
        tables = cursor.fetchall()
        print(f"📋 LangChain tables found: {[t[0] for t in tables]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Basic connection failed: {e}")
        return False
    
    try:
        # Test LangChain PGVector
        print("\n2. Testing LangChain PGVector...")
        from langchain_postgres import PGVector
        from langchain_aws import BedrockEmbeddings
        
        # Initialize embeddings (dummy for testing)
        embeddings = BedrockEmbeddings(
            model_id="amazon.titan-embed-text-v2:0",
            region_name="us-east-1"
        )
        
        # Initialize PGVector
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=connection_string,
            use_jsonb=True
        )
        
        print("✅ PGVector initialized successfully")
        
        # Test a simple operation
        # Note: This might fail if no documents exist, but connection should work
        try:
            results = vector_store.similarity_search("test query", k=1)
            print(f"✅ Similarity search works: {len(results)} results")
        except Exception as e:
            print(f"⚠️ Similarity search failed (expected if no data): {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ PGVector initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)