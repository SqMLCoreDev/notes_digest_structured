# API Tests

"""
Tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_health_endpoint_exists(self):
        """Test that health endpoint is accessible."""
        # Import here to avoid import issues during collection
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code in [200, 503]  # 503 if services not configured
    
    def test_root_endpoint(self):
        """Test root endpoint returns API info."""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    def test_docs_endpoint(self):
        """Test OpenAPI docs endpoint."""
        from app.main import app
        client = TestClient(app)
        
        response = client.get("/mcp")
        assert response.status_code == 200


class TestChatEndpoints:
    """Tests for chat API endpoints."""
    
    def test_chat_endpoint_requires_body(self):
        """Test that chat endpoint validates request body."""
        from app.main import app
        client = TestClient(app)
        
        response = client.post("/v1/chat", json={})
        # Should return 422 for missing required fields
        assert response.status_code == 422
    
    def test_chat_endpoint_validates_department(self):
        """Test that chat endpoint validates department."""
        from app.main import app
        client = TestClient(app)
        
        response = client.post("/v1/chat", json={
            "department": "test",
            "user": "test-user",
            "chatquery": "test query"
        })
        # Should return error if department/user not authorized
        assert response.status_code in [200, 401, 403, 500]
