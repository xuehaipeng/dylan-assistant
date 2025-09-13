"""
Unit tests for API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

from src.api.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        """Test health check returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "model" in data


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["docs"] == "/docs"


class TestChatEndpoint:
    """Test chat endpoint"""
    
    @patch('src.api.main.workflow')
    def test_chat_non_streaming(self, mock_workflow, client):
        """Test non-streaming chat response"""
        mock_workflow.get_response = AsyncMock(return_value="Test response")
        
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Hello",
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Test response"
        assert "session_id" in data
    
    def test_chat_empty_message(self, client):
        """Test chat with empty message"""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "",
                "stream": False
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_message_too_long(self, client):
        """Test chat with message exceeding max length"""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "x" * 8001,  # Exceeds 8000 character limit
                "stream": False
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_whitespace_only_message(self, client):
        """Test chat with whitespace-only message"""
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "   \n\t   ",
                "stream": False
            }
        )
        
        assert response.status_code == 422  # Validation error