"""
app/api/deps.py - FastAPI Dependency Injection

Provides dependency functions for injecting services into endpoints.
"""

from typing import Generator
from fastapi import Depends

from app.services.chat_service import ChatService, get_chat_service
from app.services.cache_service_three_tier import ThreeTierCacheService as CacheService, get_cache_service
from app.services.mcp.mcp_server import MCPServer, get_mcp_server
from app.core.logging import set_correlation_id, get_logger

logger = get_logger(__name__)


def get_chat_service_dep() -> ChatService:
    """Dependency for getting the chat service."""
    return get_chat_service()


def get_cache_service_dep() -> CacheService:
    """Dependency for getting the cache service."""
    return get_cache_service()


def get_mcp_server_dep() -> MCPServer:
    """Dependency for getting the MCP server."""
    return get_mcp_server()
