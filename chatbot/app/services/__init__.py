# Services Package

# MCP Tool Orchestration
from app.services.mcp import MCPServer, get_mcp_server

# External Service Clients
from app.services.clients import (
    ClaudeClient, get_claude_client, 
    OpenSearchClient,
    VectorStoreClient, get_vector_store_client
)

# RAG Components (Embeddings)
from app.services.rag import EmbeddingsClient, get_embeddings_client

__all__ = [
    # MCP
    'MCPServer',
    'get_mcp_server',
    # Clients
    'ClaudeClient',
    'get_claude_client',
    'OpenSearchClient',
    'VectorStoreClient',
    'get_vector_store_client',
    # RAG
    'EmbeddingsClient',
    'get_embeddings_client',
]
