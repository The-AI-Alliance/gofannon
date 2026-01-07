"""Shared pytest fixtures and configuration."""
import os
import pytest
from typing import AsyncGenerator
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment variables before importing app
os.environ["APP_ENV"] = "test"
os.environ["COUCHDB_URL"] = "http://test-couch:5984"
os.environ["COUCHDB_USER"] = "test_user"
os.environ["COUCHDB_PASSWORD"] = "test_pass"
os.environ["AWS_ACCESS_KEY_ID"] = "test_key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test_secret"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["S3_ENDPOINT_URL"] = "http://test-minio:9000"

from app_factory import create_app


@pytest.fixture
def app():
    """Create a FastAPI test application instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a synchronous test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an asynchronous test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_database_service():
    """Mock DatabaseService for unit tests."""
    mock_db = Mock()
    mock_db.get_item = AsyncMock(return_value=None)
    mock_db.put_item = AsyncMock(return_value=True)
    mock_db.delete_item = AsyncMock(return_value=True)
    mock_db.query_items = AsyncMock(return_value=[])
    return mock_db


@pytest.fixture
def mock_observability_service():
    """Mock ObservabilityService for unit tests."""
    mock_logger = Mock()
    mock_logger.log = Mock()
    mock_logger.log_request = Mock()
    mock_logger.log_response = Mock()
    return mock_logger


@pytest.fixture
def mock_storage_service():
    """Mock StorageService for unit tests."""
    mock_storage = Mock()
    mock_storage.upload_file = AsyncMock(return_value="s3://test-bucket/test-key")
    mock_storage.download_file = AsyncMock(return_value=b"test content")
    mock_storage.delete_file = AsyncMock(return_value=True)
    mock_storage.generate_presigned_url = AsyncMock(return_value="https://test-url")
    return mock_storage


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for unit tests."""
    mock_llm = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value={
        "choices": [{
            "message": {
                "content": "Test response",
                "role": "assistant"
            }
        }]
    })
    return mock_llm


@pytest.fixture
def mock_user_service():
    """Mock UserService for unit tests."""
    mock_user = Mock()
    mock_user.get_user = AsyncMock(return_value={
        "uid": "test-user-id",
        "email": "test@example.com",
        "display_name": "Test User"
    })
    mock_user.create_user = AsyncMock(return_value=True)
    return mock_user


@pytest.fixture
def sample_agent_data():
    """Sample agent data for testing."""
    return {
        "id": "test-agent-123",
        "user_id": "test-user-id",
        "name": "Test Agent",
        "description": "A test agent for unit testing",
        "api_specs": ["https://api.example.com/openapi.json"],
        "code": "# Test agent code\nprint('Hello, World!')",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_chat_request():
    """Sample chat request data for testing."""
    return {
        "message": "Hello, how are you?",
        "provider": "openai",
        "model": "gpt-4",
        "agent_id": "test-agent-123",
        "session_id": "test-session-123"
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "uid": "test-user-id",
        "email": "test@example.com",
        "email_verified": True,
        "display_name": "Test User",
        "photo_url": "https://example.com/photo.jpg",
        "created_at": "2024-01-01T00:00:00Z"
    }
