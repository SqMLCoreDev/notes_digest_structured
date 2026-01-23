"""
app/api/v1/endpoints/query.py - Query Endpoint

Main endpoint for processing chat queries via MCP.
"""

from fastapi import APIRouter, Depends, HTTPException
import traceback

from app.core.logging import get_logger, set_correlation_id
from app.core.exceptions import MCPException, AuthorizationError, ValidationError
from app.schema import QueryRequest, QueryResponse
from app.services.chat_service import ChatService
from app.api.deps import get_chat_service_dep

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="MCP Query",
    description="Query Elasticsearch data using natural language via Model Context Protocol (MCP). Claude AI uses MCP tools to interact with Elasticsearch directly.",
    response_description="Returns the AI-generated answer with metadata",
    operation_id="query"
)
async def query_endpoint(
    request: QueryRequest,
    chat_service: ChatService = Depends(get_chat_service_dep)
) -> QueryResponse:
    """
    ## MCP Query Endpoint

    Query Elasticsearch data using natural language via Model Context Protocol (MCP).
    Claude AI uses MCP tools to interact with Elasticsearch directly.

    **Request:**
    - `department`: User's department
    - `user`: User identifier
    - `chatquery`: Natural language question
    - `historyenabled`: Boolean flag (true to load history, false for new conversation)
    - `chatsession_id`: Session ID (required when historyenabled=true)

    **How MCP Works:**
    1. Validates user access to Elasticsearch indices
    2. Fetches conversation history if enabled
    3. Fetches index schemas (metadata only)
    4. Claude AI receives question and schemas via MCP
    5. Claude uses MCP tools to query Elasticsearch
    6. Returns natural language answer
    """
    # Set correlation ID for request tracing
    correlation_id = set_correlation_id()
    
    # Validate request
    if not request.department.strip():
        raise HTTPException(status_code=400, detail="Department is required")
    if not request.user.strip():
        raise HTTPException(status_code=400, detail="User is required")
    if not request.chatquery.strip():
        raise HTTPException(status_code=400, detail="Query is required")
    if request.historyenabled and not request.chatsession_id:
        raise HTTPException(
            status_code=400,
            detail="chatsession_id is required when historyenabled=true"
        )
    
    logger.info(f"[{correlation_id}] Query request: "
                f"department={request.department}, user={request.user}")
    
    try:
        response = await chat_service.process_query(request)
        logger.info(f"[{correlation_id}] Query completed successfully")
        return response
        
    except AuthorizationError as e:
        logger.warning(f"[{correlation_id}] Authorization error: {e.message}")
        raise HTTPException(status_code=403, detail=e.message)
        
    except ValidationError as e:
        logger.warning(f"[{correlation_id}] Validation error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
        
    except MCPException as e:
        logger.error(f"[{correlation_id}] MCP error: {e.message}")
        raise HTTPException(status_code=500, detail=f"Query failed: {e.message}")
        
    except Exception as e:
        logger.error(f"[{correlation_id}] Unexpected error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
