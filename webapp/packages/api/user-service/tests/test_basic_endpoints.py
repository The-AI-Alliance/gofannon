webapp/packages/api/user-service/tests/test_basic_endpoints.py
import pytest
import httpx

# All tests in this suite will be treated as async
pytestmark = pytest.mark.asyncio

BASE_URL = "http://localhost:8000"

async def test_health_check():
    """Tests if the /health endpoint is working."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "user-service"

async def test_get_providers():
    """
    Tests if the /providers endpoint returns available providers.
    This test assumes that OPENAI_API_KEY or another key is set in the environment
    where the API server is running (e.g., via infra/docker/.env).
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/providers")
        assert response.status_code == 200
        providers = response.json()
        assert isinstance(providers, dict)
        # Check if at least one provider is available (depends on env vars)
        assert len(providers) > 0
        assert "openai" in providers or "gemini" in providers
        if "openai" in providers:
            assert "models" in providers["openai"]
            assert "gpt-4" in providers["openai"]["models"]

async def test_mcp_tools_endpoint_invalid_url():
    """Tests the /mcp/tools endpoint with an invalid URL."""
    async with httpx.AsyncClient() as client:
        payload = {"mcp_url": "not-a-valid-url"}
        response = await client.post(f"{BASE_URL}/mcp/tools", json=payload)
        assert response.status_code == 400 # Bad Request
        assert "Invalid MCP server URL scheme" in response.json()["detail"]

async def test_mcp_tools_endpoint_unreachable_url():
    """Tests the /mcp/tools endpoint with a valid but unreachable URL."""
    async with httpx.AsyncClient(timeout=10) as client:
        # This URL is syntactically valid but should not be reachable in the test environment
        payload = {"mcp_url": "http://localhost:9999/nonexistent"}
        response = await client.post(f"{BASE_URL}/mcp/tools", json=payload)
        # Expecting a 500 because the server fails to connect
        assert response.status_code == 500
        assert "Failed to connect to MCP server" in response.json()["detail"]