"""
app/api/v1/endpoints/health.py - Health Check Endpoints

Provides health check endpoints for monitoring and orchestration.
"""

from datetime import datetime
from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.logging import get_logger
from app.schema import HealthResponse, HealthDetailResponse
from app.services.clients.es_client import OpenSearchClient
from app.api.deps import get_mcp_server_dep
from app.services.mcp.mcp_server import MCPServer

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic Health Check",
    description="Quick health check for load balancers and monitoring."
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    Returns healthy if the application is running.
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat()
    )


@router.get(
    "/health/ready",
    response_model=HealthDetailResponse,
    summary="Readiness Check",
    description="Checks if the application is ready to accept traffic by verifying dependencies."
)
async def readiness_check(
    mcp_server: MCPServer = Depends(get_mcp_server_dep)
) -> HealthDetailResponse:
    """
    Readiness check that verifies all dependencies.
    Returns status of each component.
    """
    components = {}
    overall_status = "healthy"
    
    # Check OpenSearch connectivity
    try:
        es_status = await mcp_server.es_client.test_connection()
        components["opensearch"] = {
            "status": es_status.get("status", "unknown"),
            "cluster": es_status.get("cluster_name", "unknown")
        }
        if es_status.get("status") != "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["opensearch"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # Check Claude/Bedrock (basic check)
    try:
        if mcp_server.claude_client:
            components["claude"] = {"status": "configured"}
        else:
            components["claude"] = {"status": "not_configured"}
            overall_status = "degraded"
    except Exception as e:
        components["claude"] = {
            "status": "error",
            "error": str(e)
        }
        overall_status = "degraded"
    
    # Check Vector Store (PGVector) connection
    try:
        if mcp_server.vector_store:
            # Test a simple query to verify connection
            test_result = await mcp_server.vector_store.retrieve_context(
                query="test connection",
                metadata=None
            )
            if test_result.get('success'):
                components["vector_store"] = {
                    "status": "connected",
                    "collection": settings.COLLECTION_NAME,
                    "connection": settings.POSTGRES_CONNECTION.split('@')[-1] if '@' in settings.POSTGRES_CONNECTION else 'localhost'
                }
            else:
                components["vector_store"] = {
                    "status": "connection_failed",
                    "error": test_result.get('error', 'Unknown error')
                }
                overall_status = "degraded"
        else:
            components["vector_store"] = {
                "status": "not_configured",
                "note": "Vector store not initialized - check POSTGRES_CONNECTION and AWS credentials"
            }
            overall_status = "degraded"
    except Exception as e:
        components["vector_store"] = {
            "status": "error",
            "error": str(e)
        }
        overall_status = "degraded"
    
    return HealthDetailResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        components=components
    )


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Liveness Check",
    description="Kubernetes liveness probe endpoint."
)
async def liveness_check() -> HealthResponse:
    """
    Liveness check for Kubernetes.
    Returns healthy if the process is alive.
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat()
    )
