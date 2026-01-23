"""
app/schema.py - Pydantic Models for Request/Response Validation

Defines all API request and response models with validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# =============================================================================
# REQUEST MODELS
# =============================================================================

class QueryRequest(BaseModel):
    """Request model for querying data."""
    
    department: str = Field(
        ...,
        min_length=1,
        description="Department name (determines OpenSearch cluster routing)",
        examples=["Dept"]
    )
    user: str = Field(
        ...,
        min_length=1,
        description="User identifier",
        examples=["user123"]
    )
    chatquery: str = Field(
        ...,
        min_length=1,
        description="The question to ask about the data",
        examples=["What is the average claim amount?"]
    )
    historyenabled: bool = Field(
        ...,
        description="Whether to load conversation history: true to load history, false for new conversation",
        examples=[False]
    )
    chatsession_id: Optional[str] = Field(
        None,
        description="Session ID for retrieving conversation history (required when historyenabled=true). This maps to conversation_id in PostgreSQL.",
        examples=["1", "2", "session-uuid"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "department": "Dept",
                "user": "user123",
                "chatquery": "What about the top 10 records?",
                "historyenabled": False,
                "chatsession_id": "1"
            }
        }


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class QueryResponse(BaseModel):
    """Response model for query results."""
    
    user: str = Field(..., description="User who made the query")
    sessionId: str = Field(..., description="Session ID for this conversation")
    query: str = Field(..., description="Original query string")
    chatResponse: str = Field(..., description="AI-generated response")
    chartbase64Image: Optional[str] = Field(None, description="Base64 encoded chart image")
    responseTime: str = Field(..., description="ISO timestamp of response")


class DatasetInfo(BaseModel):
    """Information about the dataset queried."""
    
    department: str = Field(..., description="Department name")
    user: str = Field(..., description="User identifier")
    allowed_indices: List[str] = Field(..., description="Indices user can access")
    indices_used: List[str] = Field(..., description="Indices actually queried")
    history_enabled: bool = Field(..., description="Whether history was loaded")
    conversation_length: int = Field(..., description="Number of messages in conversation")


class HealthResponse(BaseModel):
    """Response model for health checks."""
    
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="ISO timestamp of health check")
    checks: Optional[dict] = Field(None, description="Individual component health checks")


class HealthDetailResponse(BaseModel):
    """Detailed health check response."""
    
    status: str = Field(..., description="Overall status")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="ISO timestamp")
    components: dict = Field(..., description="Individual component statuses")
    

class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    success: bool = Field(default=False, description="Always false for errors")
    error: dict = Field(..., description="Error details with code and message")


# =============================================================================
# INTERNAL MODELS
# =============================================================================

class ConversationEntry(BaseModel):
    """Single conversation entry for history."""
    
    question: str = Field(..., description="User's question")
    answer: str = Field(..., description="AI's response")
    timestamp: str = Field(..., description="ISO timestamp")
    used_indices: Optional[List[str]] = Field(None, description="Indices used")


class CacheEntry(BaseModel):
    """Cache entry for response storage."""
    
    query: str = Field(..., description="User query")
    response: str = Field(..., description="AI response")
    used_indices: List[str] = Field(default_factory=list, description="Indices used")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
