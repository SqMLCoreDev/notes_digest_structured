"""
Notes Engine - Unified FastAPI Application

Mounts both chatbot and notesdigest services as sub-applications
with unified Swagger documentation.

Endpoints:
- /chatbot/*         → Chatbot API endpoints
- /notesdigest/*     → Notes Digest API endpoints
- /docs              → Combined Swagger UI
- /health            → Unified health check
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

# Add service directories to Python path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "chatbot"))
sys.path.insert(0, str(BASE_DIR / "notesdigest"))

# Import sub-applications
from app.main import app as chatbot_app
from medical_notes.service.app import app as notesdigest_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Unified application lifespan events."""
    print("🚀 Notes Engine starting...")
    print("   - Chatbot service mounted at /chatbot")
    print("   - NotesDigest service mounted at /notesdigest")
    print("   - Combined Swagger UI at /docs")
    
    yield
    
    print("👋 Notes Engine shutting down...")


# Create unified FastAPI application
app = FastAPI(
    title="Notes Engine API",
    description="Unified API combining Chatbot and Notes Digest services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount sub-applications
app.mount("/chatbot", chatbot_app)
app.mount("/notesdigest", notesdigest_app)


def custom_openapi():
    """
    Generate combined OpenAPI schema from both sub-applications.
    Preserves original schema names to maintain $ref compatibility.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    # Get base schema
    openapi_schema = get_openapi(
        title="Notes Engine API",
        version="1.0.0",
        description="Unified API combining Chatbot and Notes Digest services",
        routes=app.routes,
    )
    
    # Initialize components
    openapi_schema.setdefault('components', {}).setdefault('schemas', {})
    
    # Add paths and schemas from chatbot app
    if hasattr(chatbot_app, 'openapi'):
        chatbot_schema = chatbot_app.openapi()
        if chatbot_schema:
            # Merge schemas first (keep original names for $ref compatibility)
            if 'components' in chatbot_schema and 'schemas' in chatbot_schema['components']:
                for name, schema in chatbot_schema['components']['schemas'].items():
                    openapi_schema['components']['schemas'][name] = schema
            
            # Add paths with prefix
            if 'paths' in chatbot_schema:
                for path, methods in chatbot_schema['paths'].items():
                    prefixed_path = f"/chatbot{path}"
                    openapi_schema.setdefault('paths', {})[prefixed_path] = methods
                    # Add tag prefix
                    for method_data in methods.values():
                        if isinstance(method_data, dict) and 'tags' in method_data:
                            method_data['tags'] = [f"Chatbot - {tag}" for tag in method_data['tags']]
                        elif isinstance(method_data, dict):
                            method_data['tags'] = ["Chatbot"]
    
    # Add paths and schemas from notesdigest app
    if hasattr(notesdigest_app, 'openapi'):
        notesdigest_schema = notesdigest_app.openapi()
        if notesdigest_schema:
            # Merge schemas (keep original names for $ref compatibility)
            if 'components' in notesdigest_schema and 'schemas' in notesdigest_schema['components']:
                for name, schema in notesdigest_schema['components']['schemas'].items():
                    # Avoid overwriting - use NotesDigest prefix only for conflicts
                    if name in openapi_schema['components']['schemas']:
                        openapi_schema['components']['schemas'][f"NotesDigest_{name}"] = schema
                    else:
                        openapi_schema['components']['schemas'][name] = schema
            
            # Add paths with prefix
            if 'paths' in notesdigest_schema:
                for path, methods in notesdigest_schema['paths'].items():
                    prefixed_path = f"/notesdigest{path}"
                    openapi_schema.setdefault('paths', {})[prefixed_path] = methods
                    # Add tag prefix
                    for method_data in methods.values():
                        if isinstance(method_data, dict) and 'tags' in method_data:
                            method_data['tags'] = [f"NotesDigest - {tag}" for tag in method_data['tags']]
                        elif isinstance(method_data, dict):
                            method_data['tags'] = ["NotesDigest"]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Notes Engine API",
        "version": "1.0.0",
        "services": {
            "chatbot": "/chatbot",
            "notesdigest": "/notesdigest"
        },
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def unified_health():
    """Unified health check for all services."""
    return {
        "status": "healthy",
        "services": {
            "chatbot": "mounted at /chatbot",
            "notesdigest": "mounted at /notesdigest"
        }
    }


# For running locally with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
