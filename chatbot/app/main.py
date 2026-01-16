"""
app/main.py - FastAPI Application Factory

Main application entry point for local development and container deployment.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import MCPException, mcp_exception_handler, generic_exception_handler
from app.api.v1.router import router as api_v1_router

# Setup logging
setup_logging(
    level="DEBUG" if settings.DEBUG else "INFO",
    json_format=settings.ENVIRONMENT == "production"
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


def custom_openapi():
    """Custom OpenAPI schema to remove tag groupings."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Model Context Protocol (MCP) API for Elasticsearch data querying with Claude AI",
        routes=app.routes,
    )
    
    # Remove tags from operations to avoid grouping
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict):
                operation.pop("tags", None)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Model Context Protocol (MCP) API for Elasticsearch data querying with Claude AI",
    version=settings.APP_VERSION,
    docs_url="/mcp",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Custom OpenAPI schema
app.openapi = custom_openapi

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(MCPException, mcp_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API routers
app.include_router(api_v1_router)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/mcp",
        "health": "/health"
    }


# For running locally with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
