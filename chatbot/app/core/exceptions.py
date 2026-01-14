"""
app/core/exceptions.py - Custom Exception Classes

Defines application-specific exceptions with proper error codes and HTTP status mappings.
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class MCPException(Exception):
    """Base exception for all MCP-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "MCP_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class AuthenticationError(MCPException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            details=details
        )


class AuthorizationError(MCPException):
    """Raised when user lacks permission."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="AUTHZ_ERROR",
            details=details
        )


class ValidationError(MCPException):
    """Raised when request validation fails."""
    
    def __init__(self, message: str = "Validation error", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details
        )


class OpenSearchError(MCPException):
    """Raised when OpenSearch operations fail."""
    
    def __init__(self, message: str = "OpenSearch error", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="OPENSEARCH_ERROR",
            details=details
        )


class ClaudeError(MCPException):
    """Raised when Claude/Bedrock operations fail."""
    
    def __init__(self, message: str = "Claude AI error", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="CLAUDE_ERROR",
            details=details
        )


class ConfigurationError(MCPException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str = "Configuration error", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            details=details
        )


# HTTP Status Code Mapping
EXCEPTION_STATUS_CODES = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    ValidationError: 400,
    OpenSearchError: 502,
    ClaudeError: 503,
    ConfigurationError: 500,
    MCPException: 500,
}


async def mcp_exception_handler(request: Request, exc: MCPException) -> JSONResponse:
    """
    Global exception handler for MCP exceptions.
    Converts exceptions to proper JSON responses.
    """
    status_code = EXCEPTION_STATUS_CODES.get(type(exc), 500)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Fallback handler for unhandled exceptions.
    Logs the error and returns a generic response.
    """
    import logging
    import traceback
    
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": {}
            }
        }
    )
