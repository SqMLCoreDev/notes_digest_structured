"""
app/services/chat_service.py - Chat Query Orchestration Service

Main service for handling chat queries and coordinating between components.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import (
    MCPException, ValidationError, AuthorizationError, OpenSearchError
)
from app.services.cache_service_redis_postgres_simple_summary import SimplifiedCacheService as CacheService, get_cache_service
from app.services.mcp.mcp_server import MCPServer, get_mcp_server
from app.services.clients.es_client import OpenSearchClient
from app.schema import QueryRequest, QueryResponse

logger = get_logger(__name__)


class ChatService:
    """
    Main service for handling chat queries.
    Orchestrates between MCP server, caching, and user access control.
    """
    
    def __init__(
        self,
        mcp_server: Optional[MCPServer] = None,
        cache_service: Optional[CacheService] = None
    ):
        """
        Initialize chat service.
        
        Args:
            mcp_server: MCP server instance
            cache_service: Cache service instance
        """
        self.mcp_server = mcp_server or get_mcp_server()
        self.cache_service = cache_service or get_cache_service()
        self._es_client = self.mcp_server.es_client
    
    async def process_query(self, request: QueryRequest) -> QueryResponse:
        """
        Process a chat query request.
        
        Args:
            request: Query request with department, user, query, etc.
            
        Returns:
            QueryResponse with AI-generated answer
        """
        department = request.department.strip()
        user = request.user.strip()
        query = request.chatquery.strip()
        history_enabled = request.historyenabled
        session_id = request.chatsession_id
        conversation_id = request.conversation_id  # New optional field
        
        logger.info(f"Processing query: user={user}, department={department}, "
                    f"history={history_enabled}, session_id={session_id}, conversation_id={conversation_id}")
        
        # Log cache stats
        cache_stats = await self.cache_service.get_stats()
        logger.debug(f"Cache stats: {cache_stats}")
        
        # Get allowed indices for user
        allowed_indices = await self._get_user_allowed_indices(department, user)
        
        # Handle conversation history - use conversation_id if provided, otherwise use session_id
        effective_session_id = conversation_id if conversation_id else session_id
        conversation_history = await self._get_conversation_history(
            session_id=effective_session_id,
            history_enabled=history_enabled
        )
        
        # NOTE: Schemas are NOT pre-fetched anymore
        # Claude will use get_index_schema tool on-demand when it needs to query ES
        # This saves time for general queries that don't need ES data
        logger.debug(f"On-demand schema mode: {len(allowed_indices)} indices available")
        
        # Query with Claude via MCP (schemas=None for on-demand fetching)
        logger.info("Calling Claude with MCP tools (on-demand schema mode)")
        response_text, used_indices, base64_image = await self.mcp_server.query_with_claude(
            question=query,
            indices=allowed_indices,
            schemas=None,  # Let Claude fetch schemas when needed
            conversation_history=conversation_history
        )
        
        logger.info(f"Response generated ({len(response_text)} chars)")
        
        # Cache the response using the effective session ID
        if effective_session_id:
            await self.cache_service.save_response(
                session_id=effective_session_id,
                query=query,
                response_text=response_text,
                used_indices=used_indices
            )
        
        return QueryResponse(
            user=user,
            sessionId=effective_session_id or "",  # Return the effective session ID used
            query=query,
            chatResponse=response_text,
            chartbase64Image=base64_image,
            responseTime=datetime.utcnow().isoformat()
        )
    
    async def _get_user_allowed_indices(
        self,
        department: str,
        user: str
    ) -> List[str]:
        """
        Get allowed indices for a user from configuration index.
        
        Args:
            department: Department name
            user: User identifier
            
        Returns:
            List of allowed index names
        """
        try:
            query = {
                "bool": {
                    "must": [
                        {"match": {"departmentName": department}},
                        {"match": {"users": user}}
                    ]
                }
            }
            
            logger.debug(f"Looking up access for {user}@{department}")
            
            result = await self._es_client.search(
                index=settings.MAPPING_INDEX,
                query=query,
                size=10
            )
            
            if not result.get('success'):
                raise OpenSearchError(
                    message="Failed to query mapping index",
                    details={"error": result.get('error')}
                )
            
            documents = result.get('documents', [])
            
            if not documents:
                # Try broader search for better error message
                dept_result = await self._es_client.search(
                    index=settings.MAPPING_INDEX,
                    query={"match": {"departmentName": department}},
                    size=10
                )
                
                if dept_result.get('documents'):
                    found_users = []
                    for doc in dept_result.get('documents', []):
                        found_users.extend(doc.get('users', []))
                    
                    raise AuthorizationError(
                        message=f"User '{user}' not found in department '{department}'",
                        details={"available_users": list(set(found_users))}
                    )
                else:
                    raise AuthorizationError(
                        message=f"Department '{department}' not found",
                        details={}
                    )
            
            # Get allowed indices from first matching document
            allowed_indices = documents[0].get('datasets', [])
            
            if not allowed_indices:
                raise AuthorizationError(
                    message=f"No indices configured for {user}@{department}",
                    details={}
                )
            
            logger.info(f"Access granted: {user}@{department} -> {allowed_indices}")
            return allowed_indices
            
        except (AuthorizationError, OpenSearchError):
            raise
        except Exception as e:
            logger.error(f"Error fetching user access: {e}")
            raise MCPException(
                message=f"Failed to fetch user access: {str(e)}",
                error_code="ACCESS_ERROR"
            )
    
    async def _get_conversation_history(
        self,
        session_id: Optional[str],
        history_enabled: bool
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session ID
            history_enabled: Whether to load history
            
        Returns:
            List of conversation entries
        """
        if not history_enabled:
            # Clear cache for new conversation
            if session_id:
                await self.cache_service.clear_session(session_id)
            logger.debug("New conversation - cache cleared")
            return []
        
        if not session_id:
            return []
        
        # Try to get from cache first
        logger.info(f"🔍 Loading conversation history for session_id: {session_id}")
        cached_responses = await self.cache_service.get_responses(session_id)
        
        if cached_responses:
            logger.info(f"✅ Using {len(cached_responses)} cached responses")
            return self.cache_service.responses_to_conversation_history(cached_responses)
        
        # Fallback to OpenSearch history (if implemented)
        # This is where you'd query chatbox_history index
        logger.info(f"❌ No cached responses found for session_id: {session_id}")
        return []


# Singleton instance
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Get the chat service singleton."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
