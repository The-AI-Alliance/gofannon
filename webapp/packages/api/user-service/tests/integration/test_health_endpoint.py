"""Integration tests for health check and basic endpoints."""
import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.integration


class TestHealthEndpoint:
    """Integration tests for health check endpoint."""

    def test_health_endpoint_returns_200(self, client: TestClient):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_root_endpoint_returns_200(self, client: TestClient):
        """Test that root endpoint returns 200 OK."""
        response = client.get("/")

        assert response.status_code == 200
