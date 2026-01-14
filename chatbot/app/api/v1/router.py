"""
app/api/v1/router.py - API v1 Router

Aggregates all v1 endpoints into a single router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, query

router = APIRouter()

# Include health endpoints (no prefix for easy access)
router.include_router(
    health.router,
    tags=["Health"]
)

# Include query endpoint
router.include_router(
    query.router,
    tags=["Query"]
)
