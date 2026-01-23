-- PostgreSQL initialization script for Notes Engine
-- Creates the chatbot_messages table and enables pgvector extension

-- Enable pgvector extension for embeddings (if available)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create chatbot_messages table (matches your existing structure)
CREATE TABLE IF NOT EXISTS chatbot_messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    parent_id INTEGER DEFAULT 0,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant')),
    query TEXT,
    response TEXT,
    "chatResponse" TEXT,
    meta JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_conversation_id ON chatbot_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_role ON chatbot_messages(role);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_created_at ON chatbot_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_deleted_at ON chatbot_messages(deleted_at);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_conv_role_created ON chatbot_messages(conversation_id, role, created_at);

-- Create embeddings table for vector search (if needed)
CREATE TABLE IF NOT EXISTS medical_notes_embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536), -- Adjust dimension based on your embedding model
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_medical_notes_embeddings_vector ON medical_notes_embeddings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Insert sample data for testing (optional)
INSERT INTO chatbot_messages (conversation_id, parent_id, role, query, response, meta) VALUES
('test-session-1', 0, 'user', 'Hello, can you help me?', NULL, '{"source": "web"}'),
('test-session-1', 0, 'assistant', 'Hello, can you help me?', 'Hello! I''m here to help you with medical data analysis. What would you like to know?', '{"source": "openai"}')
ON CONFLICT DO NOTHING;

COMMIT;